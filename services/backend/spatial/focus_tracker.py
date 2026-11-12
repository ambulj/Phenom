"""
Spatial Focus Tracking Engine (OVR-01, SAF-01, SAF-02).
Tracks active foreground windows on Windows 11 using Win32 API calls (GetForegroundWindow, GetWindowRect)
and process inspection with safe cross-platform/mock fallbacks for headless testing.
"""

import logging
import platform
import time
from typing import Optional

from services.backend.schemas.spatial import ActiveWindowTarget, WindowRect

logger = logging.getLogger(__name__)

# Check if native Win32 libraries are available
IS_WINDOWS = platform.system() == "Windows"
try:
    if IS_WINDOWS:
        import win32gui
        import win32process
        import psutil
        WIN32_AVAILABLE = True
    else:
        WIN32_AVAILABLE = False
except ImportError:
    WIN32_AVAILABLE = False


class FocusTrackingEngine:
    """Tracks active foreground window positions and bounds for holographic spatial anchoring."""

    def __init__(self) -> None:
        self._mock_target: Optional[ActiveWindowTarget] = None
        self._last_target: Optional[ActiveWindowTarget] = None
        self._halted: bool = False

    def halt(self) -> None:
        """Immediate synchronous halt for Guardian kill switch (< 10ms SLA)."""
        self._halted = True
        self._mock_target = None
        self._last_target = None
        logger.info("[FocusTracker] FocusTrackingEngine halted.")

    def reset(self) -> None:
        """Reset halt state after Guardian disengagement."""
        self._halted = False

    def is_halted(self) -> bool:
        return self._halted

    def set_mock_window(self, target: Optional[ActiveWindowTarget]) -> None:
        """Inject a simulated foreground window for headless CI, unit tests, or overrides."""
        self._mock_target = target

    def get_active_window(self) -> ActiveWindowTarget:
        """
        Query current foreground window metadata and bounds.
        Returns mock window if configured or running in non-desktop / headless mode.
        """
        if self._halted:
            return ActiveWindowTarget(
                hwnd=0,
                title="System Halted",
                process_name="guardian",
                pid=0,
                bounds=WindowRect(left=0, top=0, right=0, bottom=0, width=0, height=0),
                is_minimized=False,
                is_focused=False,
            )

        if self._mock_target is not None:
            self._mock_target.captured_at = time.time()
            self._last_target = self._mock_target
            return self._mock_target

        if not WIN32_AVAILABLE:
            # Fallback for non-Windows or headless test environment
            fallback = ActiveWindowTarget(
                hwnd=1001,
                title="Phenom Desktop Spatial Canvas",
                process_name="phenom.exe",
                pid=4242,
                bounds=WindowRect(left=100, top=100, right=1380, bottom=900, width=1280, height=800),
                is_minimized=False,
                is_focused=True,
                captured_at=time.time(),
            )
            self._last_target = fallback
            return fallback

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return self._last_target or ActiveWindowTarget(
                    hwnd=0,
                    title="Desktop Surface",
                    process_name="explorer.exe",
                    pid=0,
                    bounds=WindowRect(left=0, top=0, right=1920, bottom=1080, width=1920, height=1080),
                    is_minimized=False,
                    is_focused=True,
                    captured_at=time.time(),
                )

            title = win32gui.GetWindowText(hwnd).strip()
            # Clean and sanitize title
            if not title:
                title = "Unnamed Window"

            # Window Rect: (left, top, right, bottom)
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            width = max(0, right - left)
            height = max(0, bottom - top)

            # Process info
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc_name = "unknown"
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                proc_name = "system"

            is_minimized = bool(win32gui.IsIconic(hwnd))

            target = ActiveWindowTarget(
                hwnd=hwnd,
                title=title,
                process_name=proc_name,
                pid=pid,
                bounds=WindowRect(
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                    width=width,
                    height=height,
                ),
                is_minimized=is_minimized,
                is_focused=True,
                captured_at=time.time(),
            )
            self._last_target = target
            return target

        except Exception as e:
            logger.warning(f"[FocusTracker] Error reading foreground window: {e}")
            return self._last_target or ActiveWindowTarget(
                hwnd=0,
                title="Unknown",
                process_name="unknown",
                pid=0,
                bounds=WindowRect(left=0, top=0, right=1920, bottom=1080, width=1920, height=1080),
                is_minimized=False,
                is_focused=False,
                captured_at=time.time(),
            )
