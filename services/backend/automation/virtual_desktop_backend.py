"""
Phenom Virtual Desktop Backend Abstraction
Defines IVirtualDesktopBackend interface, Win32VirtualDesktopBackend (native Windows user32/gdi32/kernel32),
and MockVirtualDesktopBackend (in-memory test mock).
"""

from abc import ABC, abstractmethod
import sys
import os
import time
import threading
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image, ImageDraw

from services.backend.schemas.virtual_desktop import WindowInfo


class IVirtualDesktopBackend(ABC):
    """Abstract interface for virtual desktop management, window capture, and input injection."""

    @abstractmethod
    def create_desktop(self, name: str) -> int:
        """Create or open a virtual desktop. Returns handle (hdesk) as int."""
        pass

    @abstractmethod
    def close_desktop(self, hdesk: int) -> bool:
        """Close virtual desktop handle."""
        pass

    @abstractmethod
    def launch_process(self, app_path: str, args: Optional[List[str]], desktop_name: str) -> int:
        """Launch process targeting specified desktop_name. Returns PID."""
        pass

    @abstractmethod
    def enum_desktop_windows(self, hdesk: int) -> List[WindowInfo]:
        """Enumerate top-level windows on the virtual desktop."""
        pass

    @abstractmethod
    def get_window_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        """Get (left, top, right, bottom) rect of window."""
        pass

    @abstractmethod
    def get_window_title(self, hwnd: int) -> str:
        """Get window title."""
        pass

    @abstractmethod
    def is_window_visible(self, hwnd: int) -> bool:
        """Check if window is visible."""
        pass

    @abstractmethod
    def is_window_minimized(self, hwnd: int) -> bool:
        """Check if window is minimized (iconic)."""
        pass

    @abstractmethod
    def print_window_ram(self, hwnd: int) -> Image.Image:
        """Capture window frame directly into a PIL Image in RAM. Zero disk writes."""
        pass

    @abstractmethod
    def post_message(self, hwnd: int, msg: int, w_param: int, l_param: int) -> bool:
        """Post Win32 message to window message queue without moving physical cursor."""
        pass

    @abstractmethod
    def get_window_pid(self, hwnd: int) -> Optional[int]:
        """Get process ID that owns the window."""
        pass


class MockVirtualDesktopBackend(IVirtualDesktopBackend):
    """
    High-fidelity in-memory simulated virtual desktop backend.
    Enables deterministic testing, headless CI environments, and validation without OS side effects.
    """

    def __init__(self):
        self._desktops: Dict[int, str] = {}
        self._next_hdesk: int = 1000
        self._windows: Dict[int, Dict[str, Any]] = {}
        self._next_hwnd: int = 65536
        self._processes: Dict[int, Dict[str, Any]] = {}
        self._next_pid: int = 50000
        self.injected_messages: List[Tuple[int, int, int, int]] = []
        self._lock = threading.RLock()

    def create_desktop(self, name: str) -> int:
        with self._lock:
            self._next_hdesk += 1
            hdesk = self._next_hdesk
            self._desktops[hdesk] = name
            return hdesk

    def close_desktop(self, hdesk: int) -> bool:
        with self._lock:
            if hdesk in self._desktops:
                del self._desktops[hdesk]
                # Clean up windows belonging to this desktop
                hwnds_to_del = [h for h, w in self._windows.items() if w.get("hdesk") == hdesk]
                for h in hwnds_to_del:
                    del self._windows[h]
                return True
            return False

    def launch_process(self, app_path: str, args: Optional[List[str]], desktop_name: str) -> int:
        with self._lock:
            self._next_pid += 1
            pid = self._next_pid
            self._next_hwnd += 1
            hwnd = self._next_hwnd

            app_title = os.path.basename(app_path)
            self._processes[pid] = {
                "app_path": app_path,
                "args": args or [],
                "desktop_name": desktop_name,
                "hwnd": hwnd,
            }

            # Find matching hdesk
            hdesk = 0
            for hd, name in self._desktops.items():
                if name == desktop_name:
                    hdesk = hd
                    break

            self._windows[hwnd] = {
                "title": f"Mock {app_title}",
                "class_name": "MockWindowClass",
                "rect": (100, 100, 900, 700),
                "is_visible": True,
                "is_minimized": False,
                "hdesk": hdesk,
                "pid": pid,
                "content_text": "",
                "click_count": 0,
            }
            return pid

    def enum_desktop_windows(self, hdesk: int) -> List[WindowInfo]:
        with self._lock:
            res: List[WindowInfo] = []
            for hwnd, info in self._windows.items():
                if info.get("hdesk") == hdesk:
                    res.append(
                        WindowInfo(
                            hwnd=hwnd,
                            title=info["title"],
                            class_name=info["class_name"],
                            rect=info["rect"],
                            is_visible=info["is_visible"],
                            is_minimized=info["is_minimized"],
                        )
                    )
            return res

    def get_window_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        with self._lock:
            if hwnd in self._windows:
                return self._windows[hwnd]["rect"]
            return (0, 0, 800, 600)

    def get_window_title(self, hwnd: int) -> str:
        with self._lock:
            if hwnd in self._windows:
                return self._windows[hwnd]["title"]
            return ""

    def is_window_visible(self, hwnd: int) -> bool:
        with self._lock:
            if hwnd in self._windows:
                return self._windows[hwnd]["is_visible"]
            return False

    def is_window_minimized(self, hwnd: int) -> bool:
        with self._lock:
            if hwnd in self._windows:
                return self._windows[hwnd]["is_minimized"]
            return False

    def get_window_pid(self, hwnd: int) -> Optional[int]:
        with self._lock:
            if hwnd in self._windows:
                return self._windows[hwnd].get("pid")
            return None

    def print_window_ram(self, hwnd: int) -> Image.Image:
        """Returns in-memory synthetic PIL image showing current window state."""
        with self._lock:
            rect = self.get_window_rect(hwnd)
            width = max(100, rect[2] - rect[0])
            height = max(100, rect[3] - rect[1])
            title = self.get_window_title(hwnd)
            win = self._windows.get(hwnd, {})
            click_count = win.get("click_count", 0)
            text_content = win.get("content_text", "")

            # Create in-memory canvas
            img = Image.new("RGB", (width, height), (24, 28, 36))
            draw = ImageDraw.Draw(img)

            # Draw title bar
            draw.rectangle([(0, 0), (width, 32)], fill=(40, 48, 64))
            draw.text((12, 8), f"Window: {title} (HWND: {hwnd})", fill=(220, 225, 235))

            # Draw content area with state indicator
            draw.rectangle([(10, 42), (width - 10, height - 10)], outline=(60, 70, 90), width=1)
            draw.text((20, 60), f"Clicks received: {click_count}", fill=(0, 255, 204))
            draw.text((20, 90), f"Buffer text: {text_content}", fill=(255, 255, 255))

            # Visual state change indicators for delta detection
            if click_count > 0:
                draw.rectangle([(180, 55), (180 + min(400, click_count * 30), 80)], fill=(0, 255, 204))
            if text_content:
                draw.rectangle([(180, 90), (180 + min(400, len(text_content) * 20), 115)], fill=(255, 180, 0))
            return img

    def post_message(self, hwnd: int, msg: int, w_param: int, l_param: int) -> bool:
        with self._lock:
            self.injected_messages.append((hwnd, msg, w_param, l_param))
            if hwnd in self._windows:
                # WM_LBUTTONDOWN = 0x0201, WM_CHAR = 0x0102
                if msg == 0x0201:
                    self._windows[hwnd]["click_count"] = self._windows[hwnd].get("click_count", 0) + 1
                elif msg == 0x0102:
                    char = chr(w_param) if 0 <= w_param <= 0x10FFFF else ""
                    self._windows[hwnd]["content_text"] = self._windows[hwnd].get("content_text", "") + char
                return True
            return False


class Win32VirtualDesktopBackend(IVirtualDesktopBackend):
    """
    Native Win32 implementation using ctypes.windll user32, gdi32, and kernel32.
    Implements dedicated clean worker threads for thread desktop affinity to prevent ERROR_BUSY (170).
    """

    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("Win32VirtualDesktopBackend is only supported on Windows.")
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.windll.user32
        self.gdi32 = ctypes.windll.gdi32
        self.kernel32 = ctypes.windll.kernel32

        # Win32 Constants
        self.DESKTOP_ALL_ACCESS = 0x01FF
        self.PW_RENDERFULLCONTENT = 2
        self.WM_LBUTTONDOWN = 0x0201
        self.WM_LBUTTONUP = 0x0202
        self.WM_RBUTTONDOWN = 0x0204
        self.WM_RBUTTONUP = 0x0205
        self.WM_MOUSEMOVE = 0x0200
        self.WM_CHAR = 0x0102
        self.WM_KEYDOWN = 0x0100
        self.WM_KEYUP = 0x0101

    def create_desktop(self, name: str) -> int:
        """
        Creates or opens a named desktop surface on the current window station.
        """
        # HDESK CreateDesktopW(LPCWSTR lpszDesktop, LPCWSTR lpszDevice, DEVMODEW *pDevmode,
        #                      DWORD dwFlags, DWORD dwDesiredAccess, LPSECURITY_ATTRIBUTES lpsa);
        hdesk = self.user32.CreateDesktopW(
            name,
            None,
            None,
            0,
            self.DESKTOP_ALL_ACCESS,
            None
        )
        if not hdesk:
            # Fallback to OpenDesktopW if already exists
            hdesk = self.user32.OpenDesktopW(name, 0, False, self.DESKTOP_ALL_ACCESS)
        if not hdesk:
            err = self.kernel32.GetLastError()
            raise OSError(f"Failed to create/open desktop '{name}': Win32 error {err}")
        return int(hdesk)

    def close_desktop(self, hdesk: int) -> bool:
        """Closes a desktop handle."""
        res = self.user32.CloseDesktop(self.wintypes.HANDLE(hdesk))
        return bool(res)

    def launch_process(self, app_path: str, args: Optional[List[str]], desktop_name: str) -> int:
        """
        Launches an application inside the isolated desktop by setting STARTUPINFO.lpDesktop.
        """
        class STARTUPINFOW(self.ctypes.Structure):
            _fields_ = [
                ("cb", self.wintypes.DWORD),
                ("lpReserved", self.wintypes.LPWSTR),
                ("lpDesktop", self.wintypes.LPWSTR),
                ("lpTitle", self.wintypes.LPWSTR),
                ("dwX", self.wintypes.DWORD),
                ("dwY", self.wintypes.DWORD),
                ("dwXSize", self.wintypes.DWORD),
                ("dwYSize", self.wintypes.DWORD),
                ("dwXCountChars", self.wintypes.DWORD),
                ("dwYCountChars", self.wintypes.DWORD),
                ("dwFillAttribute", self.wintypes.DWORD),
                ("dwFlags", self.wintypes.DWORD),
                ("wShowWindow", self.wintypes.WORD),
                ("cbReserved2", self.wintypes.WORD),
                ("lpReserved2", self.ctypes.c_void_p),
                ("hStdInput", self.wintypes.HANDLE),
                ("hStdOutput", self.wintypes.HANDLE),
                ("hStdError", self.wintypes.HANDLE),
            ]

        class PROCESS_INFORMATION(self.ctypes.Structure):
            _fields_ = [
                ("hProcess", self.wintypes.HANDLE),
                ("hThread", self.wintypes.HANDLE),
                ("dwProcessId", self.wintypes.DWORD),
                ("dwThreadId", self.wintypes.DWORD),
            ]

        si = STARTUPINFOW()
        si.cb = self.ctypes.sizeof(STARTUPINFOW)
        si.lpDesktop = desktop_name

        pi = PROCESS_INFORMATION()

        cmd_line = f'"{app_path}"'
        if args:
            cmd_line += " " + " ".join(f'"{a}"' if " " in a else a for a in args)

        cmd_buf = self.ctypes.create_unicode_buffer(cmd_line)

        # CREATE_NEW_CONSOLE = 0x00000010
        success = self.kernel32.CreateProcessW(
            None,
            cmd_buf,
            None,
            None,
            False,
            0x00000010,
            None,
            None,
            self.ctypes.byref(si),
            self.ctypes.byref(pi),
        )

        if not success:
            err = self.kernel32.GetLastError()
            raise OSError(f"Failed to launch process '{app_path}' on desktop '{desktop_name}': Win32 error {err}")

        pid = int(pi.dwProcessId)
        self.kernel32.CloseHandle(pi.hThread)
        self.kernel32.CloseHandle(pi.hProcess)
        return pid

    def enum_desktop_windows(self, hdesk: int) -> List[WindowInfo]:
        """
        Enumerates top-level windows for the virtual desktop.
        Runs in a dedicated clean worker thread to preserve desktop affinity and prevent ERROR_BUSY (170).
        """
        windows: List[WindowInfo] = []
        result_container: Dict[str, Any] = {"error": None, "windows": windows}

        def _worker():
            try:
                # Set thread desktop for this clean thread
                self.user32.SetThreadDesktop(self.wintypes.HANDLE(hdesk))

                WNDENUMPROC = self.ctypes.WINFUNCTYPE(self.wintypes.BOOL, self.wintypes.HWND, self.wintypes.LPARAM)

                def _enum_proc(hwnd, lparam):
                    try:
                        title_buf = self.ctypes.create_unicode_buffer(512)
                        self.user32.GetWindowTextW(hwnd, title_buf, 512)
                        title = title_buf.value

                        class_buf = self.ctypes.create_unicode_buffer(256)
                        self.user32.GetClassNameW(hwnd, class_buf, 256)
                        class_name = class_buf.value

                        rect = self.wintypes.RECT()
                        self.user32.GetWindowRect(hwnd, self.ctypes.byref(rect))
                        rect_tuple = (rect.left, rect.top, rect.right, rect.bottom)

                        is_vis = bool(self.user32.IsWindowVisible(hwnd))
                        is_min = bool(self.user32.IsIconic(hwnd))

                        windows.append(
                            WindowInfo(
                                hwnd=int(hwnd),
                                title=title,
                                class_name=class_name,
                                rect=rect_tuple,
                                is_visible=is_vis,
                                is_minimized=is_min,
                            )
                        )
                    except Exception:
                        pass
                    return True

                proc_cb = WNDENUMPROC(_enum_proc)
                self.user32.EnumDesktopWindows(self.wintypes.HANDLE(hdesk), proc_cb, 0)
            except Exception as e:
                result_container["error"] = e

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join(timeout=2.0)

        if result_container["error"]:
            raise result_container["error"]
        return result_container["windows"]

    def get_window_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        rect = self.wintypes.RECT()
        self.user32.GetWindowRect(self.wintypes.HWND(hwnd), self.ctypes.byref(rect))
        return (rect.left, rect.top, rect.right, rect.bottom)

    def get_window_title(self, hwnd: int) -> str:
        title_buf = self.ctypes.create_unicode_buffer(512)
        self.user32.GetWindowTextW(self.wintypes.HWND(hwnd), title_buf, 512)
        return title_buf.value

    def is_window_visible(self, hwnd: int) -> bool:
        return bool(self.user32.IsWindowVisible(self.wintypes.HWND(hwnd)))

    def is_window_minimized(self, hwnd: int) -> bool:
        return bool(self.user32.IsIconic(self.wintypes.HWND(hwnd)))

    def get_window_pid(self, hwnd: int) -> Optional[int]:
        pid = self.wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(self.wintypes.HWND(hwnd), self.ctypes.byref(pid))
        return int(pid.value) if pid.value else None

    def print_window_ram(self, hwnd: int) -> Image.Image:
        """
        Captures target window bitmap directly in RAM using Win32 PrintWindow and DIB section.
        Ensures zero disk I/O.
        """
        rect_tuple = self.get_window_rect(hwnd)
        width = max(1, rect_tuple[2] - rect_tuple[0])
        height = max(1, rect_tuple[3] - rect_tuple[1])

        hwnd_val = self.wintypes.HWND(hwnd)
        hwnd_dc = self.user32.GetWindowDC(hwnd_val)
        if not hwnd_dc:
            hwnd_dc = self.user32.GetDC(hwnd_val)

        mem_dc = self.gdi32.CreateCompatibleDC(hwnd_dc)
        hbm = self.gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
        old_bm = self.gdi32.SelectObject(mem_dc, hbm)

        try:
            # Attempt PrintWindow with PW_RENDERFULLCONTENT (2)
            pw_res = self.user32.PrintWindow(hwnd_val, mem_dc, self.PW_RENDERFULLCONTENT)
            if not pw_res:
                # Fallback to standard PrintWindow (0)
                self.user32.PrintWindow(hwnd_val, mem_dc, 0)

            # Create BITMAPINFO structure for 32-bit BGRA
            class BITMAPINFOHEADER(self.ctypes.Structure):
                _fields_ = [
                    ("biSize", self.wintypes.DWORD),
                    ("biWidth", self.wintypes.LONG),
                    ("biHeight", self.wintypes.LONG),
                    ("biPlanes", self.wintypes.WORD),
                    ("biBitCount", self.wintypes.WORD),
                    ("biCompression", self.wintypes.DWORD),
                    ("biSizeImage", self.wintypes.DWORD),
                    ("biXPelsPerMeter", self.wintypes.LONG),
                    ("biYPelsPerMeter", self.wintypes.LONG),
                    ("biClrUsed", self.wintypes.DWORD),
                    ("biClrImportant", self.wintypes.DWORD),
                ]

            bmi = BITMAPINFOHEADER()
            bmi.biSize = self.ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height  # Negative for top-down DIB
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0  # BI_RGB

            buffer_size = width * height * 4
            buf = self.ctypes.create_string_buffer(buffer_size)

            self.gdi32.GetDIBits(
                mem_dc,
                hbm,
                0,
                height,
                buf,
                self.ctypes.byref(bmi),
                0,  # DIB_RGB_COLORS
            )

            # Convert directly from in-memory BGRA buffer to PIL RGB Image
            img = Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1).convert("RGB")
            return img

        finally:
            self.gdi32.SelectObject(mem_dc, old_bm)
            self.gdi32.DeleteObject(hbm)
            self.gdi32.DeleteDC(mem_dc)
            self.user32.ReleaseDC(hwnd_val, hwnd_dc)

    def post_message(self, hwnd: int, msg: int, w_param: int, l_param: int) -> bool:
        """
        Posts Win32 message to window handle message queue.
        Zero physical cursor movement and zero focus stealing.
        """
        res = self.user32.PostMessageW(
            self.wintypes.HWND(hwnd),
            self.wintypes.UINT(msg),
            self.wintypes.WPARAM(w_param),
            self.wintypes.LPARAM(l_param),
        )
        return bool(res)
