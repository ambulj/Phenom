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
from typing import Tuple, List, Set, Dict, Any


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
    "incognito",
    "inprivate",
    "private browsing",
    "chase bank",
    "wells fargo",
    "bank of america",
    "citibank",
    "paypal",
    "master password",
    "enter password",
    "unlock database",
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


class PrivacyMasker:
    """
    Automated visual PII redactor and sensitive window shield.
    """

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
