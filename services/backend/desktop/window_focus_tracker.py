"""Real-Time Window Focus & UIA Context Tracker for Windows 11 (Milestone 49 Phase 3, GUI-01).

Extracts foreground HWND, process ID, executable name, window title, and bounding coordinates
with safe Win32 ctypes integration and injectable test simulator.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import psutil

from services.backend.schemas.semantic_focus import (
    BoundingRect,
    UIAElementDescriptor,
    WindowContext,
)
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.desktop.window_focus_tracker")


class WindowFocusTracker:
    """Observes active foreground desktop windows and extracts semantic context."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._simulated_window: Optional[WindowContext] = None

    def _assert_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Window tracking aborted.")

    def set_simulated_window(self, context: Optional[WindowContext]) -> None:
        """Injects simulated active window context for deterministic unit testing."""
        with self._lock:
            self._simulated_window = context

    def get_active_window(self) -> WindowContext:
        """Queries the current active foreground window on Windows 11."""
        self._assert_guardian()

        with self._lock:
            if self._simulated_window is not None:
                return self._simulated_window

        # Check OS platform
        if os.name != "nt":
            # POSIX / Headless fallback
            return WindowContext(
                hwnd=1001,
                title="Simulated Terminal",
                process_name="bash",
                pid=os.getpid(),
                bounding_rect=BoundingRect(left=0, top=0, right=1920, bottom=1080),
            )

        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return WindowContext(
                    hwnd=0,
                    title="Desktop / No Active Window",
                    process_name="explorer.exe",
                    pid=0,
                    bounding_rect=BoundingRect(left=0, top=0, right=1920, bottom=1080),
                )

            # Extract Title
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value or "Untitled Window"

            # Extract PID and Process Name
            pid_c = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_c))
            pid = pid_c.value
            process_name = "unknown"
            try:
                proc = psutil.Process(pid)
                process_name = proc.name()
            except Exception:
                pass

            # Extract Bounding Coordinates
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            bounds = BoundingRect(
                left=int(rect.left),
                top=int(rect.top),
                right=int(rect.right),
                bottom=int(rect.bottom),
            )

            # Check if minimized
            is_minimized = bool(user32.IsIconic(hwnd))

            return WindowContext(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
                pid=pid,
                bounding_rect=bounds,
                is_minimized=is_minimized,
                uia_root=UIAElementDescriptor(
                    name=title,
                    class_name="Window",
                    bounding_rect=bounds,
                ),
                timestamp=time.time(),
            )
        except Exception as e:
            logger.warning(f"Error querying active foreground window: {e}")
            return WindowContext(
                hwnd=0,
                title="Unknown Window",
                process_name="unknown",
                pid=0,
                bounding_rect=BoundingRect(left=0, top=0, right=1920, bottom=1080),
            )
