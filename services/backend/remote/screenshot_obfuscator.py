"""
Phenom Sensitive Window Obfuscator & Screenshot Privacy Engine (Task 7g)
Strictly adheres to:
1. In-memory screenshot processing (strictly in RAM, never written to disk).
2. Scans open/visible windows matching sensitive keywords:
   - Password Managers (Bitwarden, KeePass, 1Password, LastPass, Dashlane)
   - Messaging & Email (WhatsApp, Telegram, Outlook, Thunderbird)
   - Banking & Financial Portals (HDFC, SBI, ICICI, Chase, Wells Fargo, Citi, etc.)
   - Login, credential, and wallet dialogues.
3. Applies 35px Gaussian blur (PIL.ImageFilter.GaussianBlur(35)) over bounding boxes.
4. Adds security watermark indicator over redacted regions.
5. Injected window provider support for deterministic testing and headless environments.
"""

from typing import List, Dict, Any, Tuple, Optional
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import os

DEFAULT_SENSITIVE_KEYWORDS = [
    "bitwarden", "keepass", "1password", "lastpass", "dashlane",
    "whatsapp", "telegram", "outlook", "thunderbird",
    "banking", "wallet", "login", "signin",
    "hdfc", "sbi", "icici", "chase", "wells fargo", "citi", "bank",
    "credit card", "passwords", "authenticator"
]

def find_sensitive_windows(
    keywords: Optional[List[str]] = None,
    custom_windows: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Locates top-level visible windows matching sensitive application keywords.
    Returns list of dicts: [{"title": str, "rect": (left, top, right, bottom)}]
    """
    search_keywords = [k.lower() for k in (keywords or DEFAULT_SENSITIVE_KEYWORDS)]
    matched_windows: List[Dict[str, Any]] = []

    # If custom windows are provided (for tests or simulated desktop environments)
    if custom_windows is not None:
        for win in custom_windows:
            title = win.get("title", "")
            lower_title = title.lower()
            if any(k in lower_title for k in search_keywords):
                matched_windows.append(win)
        return matched_windows

    # Live Windows inspection via win32gui
    try:
        import win32gui
        def enum_handler(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title:
                    lower_title = title.lower()
                    if any(k in lower_title for k in search_keywords):
                        rect = win32gui.GetWindowRect(hwnd) # (left, top, right, bottom)
                        w = rect[2] - rect[0]
                        h = rect[3] - rect[1]
                        if w > 10 and h > 10:
                            matched_windows.append({
                                "hwnd": hwnd,
                                "title": title,
                                "rect": rect
                            })
            return True
        win32gui.EnumWindows(enum_handler, None)
    except Exception:
        pass

    return matched_windows

def obfuscate_screenshot(
    image: Image.Image,
    sensitive_regions: Optional[List[Tuple[int, int, int, int]]] = None,
    sensitive_windows: Optional[List[Dict[str, Any]]] = None,
    blur_radius: int = 35
) -> Image.Image:
    """
    Applies 35px Gaussian blur to specified regions or detected sensitive windows.
    Returns a copy of the PIL Image with redacted regions.
    Never writes to disk.
    """
    obfuscated = image.copy()
    img_w, img_h = obfuscated.size

    # Collect target bounding boxes
    boxes: List[Tuple[Tuple[int, int, int, int], str]] = []

    if sensitive_regions:
        for box in sensitive_regions:
            boxes.append((box, "Sensitive Area"))

    if sensitive_windows:
        for win in sensitive_windows:
            rect = win.get("rect")
            if rect and len(rect) == 4:
                boxes.append((rect, win.get("title", "Sensitive Window")))

    # If no boxes provided, attempt auto-detection
    if sensitive_regions is None and sensitive_windows is None:
        detected = find_sensitive_windows()
        for win in detected:
            rect = win.get("rect")
            if rect and len(rect) == 4:
                boxes.append((rect, win.get("title", "Sensitive Window")))

    draw = ImageDraw.Draw(obfuscated, "RGBA")

    for rect, label in boxes:
        left, top, right, bottom = rect

        # Clamp coordinates to image boundaries
        c_left = max(0, min(left, img_w))
        c_top = max(0, min(top, img_h))
        c_right = max(0, min(right, img_w))
        c_bottom = max(0, min(bottom, img_h))

        if c_right <= c_left or c_bottom <= c_top:
            continue

        box = (c_left, c_top, c_right, c_bottom)
        
        # 1. Crop region and apply 35px Gaussian blur
        cropped = obfuscated.crop(box)
        blurred = cropped.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        obfuscated.paste(blurred, box)

        # 2. Draw privacy overlay pill and border
        border_box = [c_left, c_top, c_right - 1, c_bottom - 1]
        draw.rectangle(border_box, outline=(239, 68, 68, 200), width=3) # Ruby red border

        # Pill dimensions
        pill_w = min(420, max(260, (c_right - c_left) - 40))
        pill_h = 40
        pill_x0 = c_left + ((c_right - c_left) - pill_w) // 2
        pill_y0 = c_top + ((c_bottom - c_top) - pill_h) // 2

        if (c_right - c_left) >= 120 and (c_bottom - c_top) >= 60:
            draw.rectangle(
                [pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h],
                fill=(15, 23, 42, 225), # Dark slate translucent background
                outline=(239, 68, 68, 255),
                width=1
            )
            banner_text = f"[🔒 REDACTED: {label[:20]} (35px Blur)]"
            draw.text(
                (pill_x0 + 12, pill_y0 + 12),
                banner_text,
                fill=(248, 113, 113, 255) # Soft red text
            )

    return obfuscated

def capture_and_obfuscate_screen(
    blur_radius: int = 35,
    custom_windows: Optional[List[Dict[str, Any]]] = None
) -> Tuple[Image.Image, List[Dict[str, Any]]]:
    """
    Captures primary screen in-memory via DesktopController,
    detects sensitive windows, and applies 35px blur.
    Returns (obfuscated_image, detected_windows).
    """
    from services.backend.automation.desktop_controller import desktop_controller
    img = desktop_controller.capture_screen_ram()

    detected = find_sensitive_windows(custom_windows=custom_windows)
    obfuscated = obfuscate_screenshot(
        img,
        sensitive_windows=detected,
        blur_radius=blur_radius
    )
    return obfuscated, detected
