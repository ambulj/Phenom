"""
Smart Context Screen Capture Engine (VIS-01.1 & VIS-01.3).
Captures the active focused window or full primary display in-memory.
Applies Rule 4 and Rule 8 privacy masking (credit cards, password fields, sensitive windows)
directly on RAM buffers before any model ingestion. Strictly zero disk writes.
"""

import io
import re
import time
import base64
from typing import Tuple, Dict, Any, Optional, List
from PIL import Image, ImageDraw

try:
    import win32gui
    import win32process
except ImportError:
    win32gui = None
    win32process = None

from services.backend.vision.frame_grabber import FrameGrabber, frame_grabber
from services.backend.vision.privacy_masker import privacy_masker, DEFAULT_SENSITIVE_PATTERNS


# Regex patterns for sensitive credentials & financial data on screen
CARD_NUMBER_REGEX = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")
CVV_REGEX = re.compile(r"\b(?:CVV|CVC|CID)[\s:]*([0-9]{3,4})\b", re.IGNORECASE)
PASSWORD_LABEL_REGEX = re.compile(r"\b(?:password|passcode|secret|api[_-]?key)\b", re.IGNORECASE)


class SmartScreenCapture:
    """High-performance in-RAM screen capture with Smart Context window targeting and privacy shielding."""

    def __init__(self, grabber: Optional[FrameGrabber] = None):
        self._grabber = grabber or frame_grabber
        self.last_capture_metadata: Dict[str, Any] = {}

    def get_focused_window_info(self) -> Dict[str, Any]:
        """Returns details about the currently active focused Windows application."""
        if not win32gui:
            return {
                "hwnd": 0,
                "title": "Desktop Simulation",
                "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
                "is_sensitive": False
            }

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return {
                    "hwnd": 0,
                    "title": "Desktop",
                    "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
                    "is_sensitive": False
                }

            title = win32gui.GetWindowText(hwnd) or "Untitled Window"
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            width = max(0, right - left)
            height = max(0, bottom - top)

            # Check if title matches sensitive patterns
            is_sensitive = any(re.search(pat, title, re.IGNORECASE) for pat in DEFAULT_SENSITIVE_PATTERNS)

            return {
                "hwnd": hwnd,
                "title": title,
                "rect": {"x": left, "y": top, "width": width, "height": height},
                "is_sensitive": is_sensitive
            }
        except Exception:
            return {
                "hwnd": 0,
                "title": "Unknown",
                "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
                "is_sensitive": False
            }

    def capture(
        self,
        mode: str = "focused_window",
        mask_privacy: bool = True
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Captures the screen in RAM.
        mode: 'focused_window' (crops to active application) or 'full_desktop'.
        mask_privacy: black out sensitive windows, cards, and password fields (Rule 4, Rule 8).
        """
        start = time.perf_counter()
        raw_full = self._grabber.grab_frame()
        win_info = self.get_focused_window_info()

        result_img: Image.Image
        capture_rect = win_info["rect"]

        if mode == "focused_window" and win_info["hwnd"] != 0:
            rect = win_info["rect"]
            x, y, w, h = rect["x"], rect["y"], rect["width"], rect["height"]
            full_w, full_h = raw_full.size

            # Clamp coordinates within display boundaries
            crop_x1 = max(0, min(full_w - 1, x))
            crop_y1 = max(0, min(full_h - 1, y))
            crop_x2 = max(crop_x1 + 1, min(full_w, x + w))
            crop_y2 = max(crop_y1 + 1, min(full_h, y + h))

            if (crop_x2 - crop_x1) > 10 and (crop_y2 - crop_y1) > 10:
                result_img = raw_full.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                raw_full.close()  # Memory leak prevention
            else:
                result_img = raw_full
        else:
            result_img = raw_full
            mode = "full_desktop"

        masked_count = 0
        if mask_privacy:
            result_img, masked_count = self._apply_privacy_mask(result_img, win_info)

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        metadata = {
            "mode": mode,
            "window_title": win_info["title"],
            "window_rect": capture_rect,
            "resolution": {"width": result_img.width, "height": result_img.height},
            "capture_latency_ms": round(elapsed_ms, 2),
            "privacy_masked": mask_privacy,
            "masked_regions_count": masked_count
        }

        self.last_capture_metadata = metadata
        return result_img, metadata

    def _apply_privacy_mask(
        self,
        img: Image.Image,
        win_info: Dict[str, Any]
    ) -> Tuple[Image.Image, int]:
        """Applies Rule 4 and Rule 8 privacy mask in-memory."""
        masked_count = 0

        # 1. If entire window is flagged as sensitive (banking, password manager, private chat)
        if win_info.get("is_sensitive", False):
            # Obfuscate entire frame
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (img.width, img.height)], fill=(12, 12, 15))
            draw.text((20, 20), f"[REDACTED PRIVACY SHIELD: {win_info.get('title')}]", fill=(255, 60, 60))
            return img, 1

        # 2. Check through privacy_masker for active processes and title rules
        try:
            masked_img = privacy_masker.mask_image(img, window_title=win_info.get("title", ""))
            if masked_img is not img:
                img.close()
                img = masked_img
                masked_count += 1
        except Exception:
            pass

        return img, masked_count

    def to_jpeg_bytes(self, img: Image.Image, quality: int = 85) -> bytes:
        """Encodes PIL Image to JPEG bytes entirely in RAM with zero disk write."""
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    def to_base64_data_uri(self, img: Image.Image, quality: int = 85) -> str:
        """Returns data URI string for WebSocket/REST UI transmission."""
        raw_bytes = self.to_jpeg_bytes(img, quality=quality)
        encoded = base64.b64encode(raw_bytes).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"


# Global singleton instance
smart_screen_capture = SmartScreenCapture()
