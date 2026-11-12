"""
Phenom Virtual Desktop RAM Capture and Non-Disruptive Event Injection Driver
Captures window surfaces strictly in RAM via PrintWindow / memory DIB.
Dispatches mouse and keyboard events directly via Win32 PostMessageW with client coordinates.
Guarantees zero physical cursor movement, zero focus stealing, and zero disk writes.
"""

import io
import base64
from typing import Optional, Union, Dict
from PIL import Image

from services.backend.schemas.virtual_desktop import MouseButton
from services.backend.automation.virtual_desktop_backend import (
    IVirtualDesktopBackend,
)
from services.backend.automation.virtual_desktop_manager import (
    virtual_desktop_manager,
)


# Win32 Windows Messages
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_RBUTTONDBLCLK = 0x0206
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102

# Mouse wParam flags
MK_LBUTTON = 0x0001
MK_RBUTTON = 0x0002
MK_MBUTTON = 0x0010

# Common Virtual Key Codes
VK_MAP: Dict[str, int] = {
    "backspace": 0x08,
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "shift": 0x10,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "pause": 0x13,
    "capslock": 0x14,
    "esc": 0x1B,
    "escape": 0x1B,
    "space": 0x20,
    "pageup": 0x21,
    "pagedown": 0x22,
    "end": 0x23,
    "home": 0x24,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "printscreen": 0x2C,
    "insert": 0x2D,
    "delete": 0x2E,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
}


def pack_client_coordinates(x: int, y: int) -> int:
    """
    Packs (x, y) client coordinates into a 32-bit Win32 LPARAM.
    lParam = ((y & 0xFFFF) << 16) | (x & 0xFFFF)
    """
    return ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)


class VirtualDesktopDriver:
    """
    High-level driver for capturing isolated windows in RAM and injecting
    mouse and keyboard actions without physical peripheral movement.
    """

    def __init__(self, backend: Optional[IVirtualDesktopBackend] = None):
        self._backend = backend

    @property
    def backend(self) -> IVirtualDesktopBackend:
        return self._backend or virtual_desktop_manager.backend

    def capture_window_ram(self, hwnd: int) -> Image.Image:
        """
        Captures window image directly in memory. Zero disk writes.
        """
        return self.backend.print_window_ram(hwnd)

    def capture_window_base64(
        self, hwnd: int, max_dimension: int = 1280, quality: int = 80
    ) -> str:
        """
        Captures window image, optionally downsamples, and returns base64 JPEG data.
        Entirely in RAM via io.BytesIO. Zero disk writes.
        """
        img = self.capture_window_ram(hwnd)
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.BILINEAR)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"

    def post_mouse_click(
        self,
        hwnd: int,
        x: int,
        y: int,
        button: MouseButton = MouseButton.LEFT,
    ) -> bool:
        """
        Dispatches client-relative mouse click to target HWND.
        Does not touch physical mouse cursor or foreground active window.
        """
        lparam = pack_client_coordinates(x, y)

        if button == MouseButton.LEFT:
            down_msg = WM_LBUTTONDOWN
            up_msg = WM_LBUTTONUP
            wparam = MK_LBUTTON
        elif button == MouseButton.RIGHT:
            down_msg = WM_RBUTTONDOWN
            up_msg = WM_RBUTTONUP
            wparam = MK_RBUTTON
        else:
            down_msg = WM_MBUTTONDOWN
            up_msg = WM_MBUTTONUP
            wparam = MK_MBUTTON

        # 1. Post mouse move to position
        self.backend.post_message(hwnd, WM_MOUSEMOVE, 0, lparam)
        # 2. Post button down
        d_res = self.backend.post_message(hwnd, down_msg, wparam, lparam)
        # 3. Post button up
        u_res = self.backend.post_message(hwnd, up_msg, 0, lparam)
        return bool(d_res and u_res)

    def post_mouse_double_click(
        self,
        hwnd: int,
        x: int,
        y: int,
        button: MouseButton = MouseButton.LEFT,
    ) -> bool:
        """
        Dispatches client-relative double click to target HWND.
        """
        lparam = pack_client_coordinates(x, y)
        if button == MouseButton.LEFT:
            dbl_msg = WM_LBUTTONDBLCLK
            up_msg = WM_LBUTTONUP
            wparam = MK_LBUTTON
        elif button == MouseButton.RIGHT:
            dbl_msg = WM_RBUTTONDBLCLK
            up_msg = WM_RBUTTONUP
            wparam = MK_RBUTTON
        else:
            dbl_msg = WM_MBUTTONDOWN
            up_msg = WM_MBUTTONUP
            wparam = MK_MBUTTON

        self.post_mouse_click(hwnd, x, y, button)
        d_res = self.backend.post_message(hwnd, dbl_msg, wparam, lparam)
        u_res = self.backend.post_message(hwnd, up_msg, 0, lparam)
        return bool(d_res and u_res)

    def post_mouse_drag(
        self,
        hwnd: int,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        steps: int = 5,
    ) -> bool:
        """
        Dispatches mouse drag from (x1, y1) to (x2, y2) with intermediate steps.
        """
        start_lparam = pack_client_coordinates(x1, y1)
        end_lparam = pack_client_coordinates(x2, y2)

        # Move to start and press left button
        self.backend.post_message(hwnd, WM_MOUSEMOVE, 0, start_lparam)
        self.backend.post_message(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, start_lparam)

        # Interpolate intermediate moves
        steps = max(1, steps)
        for i in range(1, steps):
            inter_x = int(x1 + (x2 - x1) * (i / steps))
            inter_y = int(y1 + (y2 - y1) * (i / steps))
            inter_lparam = pack_client_coordinates(inter_x, inter_y)
            self.backend.post_message(hwnd, WM_MOUSEMOVE, MK_LBUTTON, inter_lparam)

        # Move to end and release button
        self.backend.post_message(hwnd, WM_MOUSEMOVE, MK_LBUTTON, end_lparam)
        res = self.backend.post_message(hwnd, WM_LBUTTONUP, 0, end_lparam)
        return bool(res)

    def post_text(self, hwnd: int, text: str) -> bool:
        """
        Dispatches text string directly to HWND via WM_CHAR messages.
        Supports full Unicode text input.
        """
        success = True
        for char in text:
            code = ord(char)
            # lParam: repeat count 1, scan code 0, transition flags 0
            if not self.backend.post_message(hwnd, WM_CHAR, code, 1):
                success = False
        return success

    def post_key(self, hwnd: int, key_name_or_vk: Union[str, int]) -> bool:
        """
        Dispatches key down and key up for virtual key code or key name.
        """
        if isinstance(key_name_or_vk, int):
            vk = key_name_or_vk
        else:
            k_lower = key_name_or_vk.strip().lower()
            if k_lower in VK_MAP:
                vk = VK_MAP[k_lower]
            elif len(k_lower) == 1:
                vk = ord(k_lower.upper())
            else:
                raise ValueError(f"Unknown key name: '{key_name_or_vk}'")

        d_res = self.backend.post_message(hwnd, WM_KEYDOWN, vk, 0)
        u_res = self.backend.post_message(hwnd, WM_KEYUP, vk, 0xC0000001)
        return bool(d_res and u_res)

    def post_hotkey(self, hwnd: int, combo: str) -> bool:
        """
        Dispatches hotkey combination (e.g. 'ctrl+s', 'alt+f4', 'ctrl+shift+p').
        """
        tokens = [t.strip().lower() for t in combo.split("+")]
        vks = []
        for t in tokens:
            if t in VK_MAP:
                vks.append(VK_MAP[t])
            elif len(t) == 1:
                vks.append(ord(t.upper()))
            else:
                raise ValueError(f"Unknown hotkey component: '{t}'")

        # Press keys in forward order
        for vk in vks:
            self.backend.post_message(hwnd, WM_KEYDOWN, vk, 0)

        # Release keys in reverse order
        for vk in reversed(vks):
            self.backend.post_message(hwnd, WM_KEYUP, vk, 0xC0000001)

        return True


# Global default driver instance
virtual_desktop_driver = VirtualDesktopDriver()
