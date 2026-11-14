"""
Phenom NEURAL-NEOCORTEX Privacy Masker & Sensitive Window Shield
Milestone 44.0: Project NEURAL-NEOCORTEX (Phase 2)

Key Architecture:
1. Sensitive Window Blinding:
   Detects password managers (KeePass, Bitwarden, 1Password), incognito browser windows,
   and banking portals, triggering immediate visual blackout (Rule 4 privacy).
2. Automated PII & Credential Masking (Rule 11):
   Regex sanitization for API keys, AWS credentials, GitHub tokens, JWTs, credit card numbers,
   and sensitive key-value pairs (password=xyz).
3. Red-Team Terminal Allowlist:
   Ensures developer security tools (Kali Linux WSL, PowerShell, Ghidra, Wireshark) are
   always captured without accidental blinding.
"""

from __future__ import annotations

import re
from typing import Tuple, List, Set, Dict, Any, Optional
from PIL import Image, ImageDraw

try:
    import win32gui
except ImportError:
    win32gui = None


# Sensitive process binaries that must trigger immediate visual blinding
SENSITIVE_PROCESSES: Set[str] = {
    "keepass.exe",
    "keepassxc.exe",
    "bitwarden.exe",
    "1password.exe",
    "dashlane.exe",
    "lastpass.exe",
}

# Sensitive title substrings (case-insensitive)
SENSITIVE_TITLE_KEYWORDS: List[str] = [
    "1password",
    "bitwarden",
    "keepass",
    "keepassxc",
    "lastpass",
    "dashlane",
    "enpass",
    "nordpass",
    "incognito",
    "inprivate",
    "private browsing",
    "private window",
    "chase bank",
    "wells fargo",
    "bank of america",
    "citibank",
    "paypal",
    "metamask",
    "coinbase",
    "binance",
    "online banking",
    "whatsapp",
    "signal",
    "telegram",
    "master password",
    "enter password",
    "unlock database",
    "credential manager",
    "windows security",
    "user account control",
]

# Dedicated cyber tools that must NEVER be blinded
CYBER_TERMINAL_PROCESSES: Set[str] = {
    "wsl.exe",
    "wslhost.exe",
    "powershell.exe",
    "pwsh.exe",
    "cmd.exe",
    "ghidra.exe",
    "ida64.exe",
    "cutter.exe",
    "wireshark.exe",
}

# PII and Credential Regex Patterns
PII_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # OpenAI & generic sk- API keys
    (re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"), "[REDACTED_API_KEY]"),
    # AWS Access Key IDs
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    # GitHub personal tokens
    (re.compile(r"\bghp_[a-zA-Z0-9]{36}\b"), "[REDACTED_GH_TOKEN]"),
    # Bearer JWT tokens
    (re.compile(r"Bearer\s+[a-zA-Z0-9\-_.]+\.[a-zA-Z0-9\-_.]+\.[a-zA-Z0-9\-_.]+"), "Bearer [REDACTED_JWT]"),
    # Credit Card Numbers (13 to 16 digits formatted)
    (re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"), "[REDACTED_CREDIT_CARD]"),
    # Key-value password / secret assignments
    (re.compile(r"(?i)\b(password|passwd|secret|api_key|privkey)\s*[:=]\s*['\"]?([^\s;,\"']+)['\"]?"), r"\1=[REDACTED_SECRET]"),
]

# Backward compatibility alias for legacy tests
DEFAULT_SENSITIVE_PATTERNS = PII_PATTERNS


class PrivacyMasker:
    """
    Automated visual PII redactor and sensitive window shield.
    """

    def __init__(self, patterns: Optional[List[str]] = None):
        self.last_masked_count: int = 0
        self.blacklist_processes: Set[str] = {p.lower() for p in SENSITIVE_PROCESSES}
        self.custom_patterns: List[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in patterns] if patterns else []

    def add_pattern(self, pattern: str) -> None:
        """Adds a custom regex pattern to sensitive window detection."""
        try:
            self.custom_patterns.append(re.compile(pattern, re.IGNORECASE))
        except Exception:
            pass

    def is_window_blacklisted(self, window_title: str, process_name: str = "") -> bool:
        """Alias for is_sensitive_window for backward compatibility with ambient copilot."""
        if any(p.search(window_title) or p.search(process_name) for p in self.custom_patterns):
            return True
        return self.is_sensitive_window(window_title, process_name)

    def is_sensitive_title(self, title: str) -> bool:
        """Checks if a window title contains any sensitive keywords."""
        title_lower = title.strip().lower()
        return any(keyword in title_lower for keyword in SENSITIVE_TITLE_KEYWORDS)

    def scan_visible_sensitive_windows(self) -> List[Dict[str, Any]]:
        """
        Uses Win32 API to find visible window bounds matching sensitive patterns.
        Returns list of rects: [{"title": str, "rect": (left, top, right, bottom)}]
        """
        matches: List[Dict[str, Any]] = []
        if win32gui is None:
            return matches

        def enum_callback(hwnd, extra):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).strip()
                    if title and self.is_sensitive_title(title):
                        rect = win32gui.GetWindowRect(hwnd)
                        left, top, right, bottom = rect
                        if right > left and bottom > top:
                            matches.append({
                                "title": title,
                                "rect": (left, top, right, bottom)
                            })
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception:
            pass

        return matches

    def mask_sensitive_windows(
        self,
        img: Image.Image,
        custom_windows: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[Image.Image, List[Dict[str, Any]]]:
        """
        Blacks out sensitive regions on the given PIL Image.
        Returns (masked_img, masked_list).
        Guarantees zero disk writes - all operations occur on in-memory PIL / raw buffer.
        """
        windows_to_mask = custom_windows if custom_windows is not None else self.scan_visible_sensitive_windows()
        self.last_masked_count = len(windows_to_mask)

        if not windows_to_mask:
            return img, []

        masked_img = img.copy()
        draw = ImageDraw.Draw(masked_img)
        img_w, img_h = masked_img.size

        applied_masks: List[Dict[str, Any]] = []

        for item in windows_to_mask:
            rect = item.get("rect")
            if not rect or len(rect) != 4:
                continue

            left, top, right, bottom = rect
            clamped_left = max(0, min(img_w, left))
            clamped_top = max(0, min(img_h, top))
            clamped_right = max(0, min(img_w, right))
            clamped_bottom = max(0, min(img_h, bottom))

            if clamped_right > clamped_left and clamped_bottom > clamped_top:
                draw.rectangle(
                    [(clamped_left, clamped_top), (clamped_right, clamped_bottom)],
                    fill=(0, 0, 0)
                )
                badge_text = "[PHENOM PRIVACY MASK]"
                draw.text(
                    (clamped_left + 12, clamped_top + 12),
                    badge_text,
                    fill=(204, 255, 0)
                )

                applied_masks.append({
                    "title": item.get("title", "Sensitive Window"),
                    "rect": (clamped_left, clamped_top, clamped_right, clamped_bottom)
                })

        return masked_img, applied_masks

    def is_sensitive_window(self, window_title: str, process_name: str) -> bool:
        """
        Determines whether the active foreground window must be blinded.
        Guarantees developer red-team tools remain visible while vaults are shielded.
        """
        proc_clean = process_name.strip().lower()
        title_clean = window_title.strip().lower()

        # 1. Check if allowed developer/cyber tool (Never blind)
        for allowed in CYBER_TERMINAL_PROCESSES:
            if allowed in proc_clean:
                return False

        # 2. Check sensitive process binary
        for sens_proc in SENSITIVE_PROCESSES:
            if sens_proc in proc_clean:
                return True

        # 3. Check sensitive window title keywords
        for keyword in SENSITIVE_TITLE_KEYWORDS:
            if keyword in title_clean:
                return True

        return False

    def mask_pii_text(self, text: str) -> Tuple[str, int]:
        """
        Scans text and redacts API keys, credentials, and tokens.
        Returns (masked_text, total_redactions).
        """
        if not text:
            return "", 0

        masked = text
        redactions_count = 0

        for pattern, replacement in PII_PATTERNS:
            matches = pattern.findall(masked)
            if matches:
                redactions_count += len(matches)
                masked = pattern.sub(replacement, masked)

        return masked, redactions_count


# Singleton instance
privacy_masker = PrivacyMasker()
