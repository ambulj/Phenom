"""
Phenom Privacy Masker
Automatically detects sensitive desktop windows (password managers, banking, incognito tabs)
and blacks them out in RAM prior to any model ingestion or live streaming.
Strictly zero disk writes - all redactions happen directly on in-memory buffers.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image, ImageDraw

try:
    import win32gui
except ImportError:
    win32gui = None


DEFAULT_SENSITIVE_PATTERNS = [
    # Password Managers
    r"1password",
    r"bitwarden",
    r"keepass",
    r"lastpass",
    r"dashlane",
    r"enpass",
    r"roboform",
    r"nordpass",
    # Private Browsing
    r"incognito",
    r"inprivate",
    r"private browsing",
    # Financial & Crypto
    r"wallet",
    r"paypal",
    r"metamask",
    r"coinbase",
    r"binance",
    r"online banking",
    # System Credentials & Security
    r"credential manager",
    r"windows security",
    r"user account control",
]


class PrivacyMasker:
    def __init__(self, patterns: Optional[List[str]] = None):
        raw_patterns = patterns or DEFAULT_SENSITIVE_PATTERNS
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in raw_patterns]
        self.last_masked_count: int = 0

    def add_pattern(self, pattern: str):
        self.compiled_patterns.append(re.compile(pattern, re.IGNORECASE))

    def is_sensitive_title(self, title: str) -> bool:
        if not title:
            return False
        return any(p.search(title) for p in self.compiled_patterns)

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
                        # Filter zero-sized or minimized windows
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
            # Clamp to image dimensions
            clamped_left = max(0, min(img_w, left))
            clamped_top = max(0, min(img_h, top))
            clamped_right = max(0, min(img_w, right))
            clamped_bottom = max(0, min(img_h, bottom))

            if clamped_right > clamped_left and clamped_bottom > clamped_top:
                # Solid black out
                draw.rectangle(
                    [(clamped_left, clamped_top), (clamped_right, clamped_bottom)],
                    fill=(0, 0, 0)
                )

                # Cyber privacy badge tag
                badge_text = "[PHENOM PRIVACY MASK]"
                draw.text(
                    (clamped_left + 12, clamped_top + 12),
                    badge_text,
                    fill=(204, 255, 0)  # Acid Lime
                )

                applied_masks.append({
                    "title": item.get("title", "Sensitive Window"),
                    "rect": (clamped_left, clamped_top, clamped_right, clamped_bottom)
                })

        return masked_img, applied_masks


privacy_masker = PrivacyMasker()
