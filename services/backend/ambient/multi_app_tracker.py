"""
Phenom Multi-App Semantic Tracker (CTX-01.1, Rule 4)
Enumerates desktop windows, resolves active document paths/titles, and categorizes
applications across IDEs, Browsers, Terminals, Notes, and Communication tools.
100% in-RAM; zero disk I/O. Supports mock mode for unit tests.
"""

import sys
import os
import re
import time
import logging
from typing import Dict, Any, List, Optional, Tuple, Literal
from pydantic import BaseModel, Field

import psutil

try:
    import win32gui
    import win32process
except ImportError:
    win32gui = None
    win32process = None

from services.backend.ambient.context_sanitizer import context_sanitizer

logger = logging.getLogger("phenom.multi_app_tracker")

AppCategory = Literal["ide", "browser", "terminal", "notes", "communication", "other"]

PROCESS_CATEGORIES: Dict[str, AppCategory] = {
    # IDEs & Code Editors
    "code.exe": "ide",
    "cursor.exe": "ide",
    "pycharm64.exe": "ide",
    "idea64.exe": "ide",
    "devenv.exe": "ide",
    "sublime_text.exe": "ide",
    "notepad++.exe": "ide",

    # Browsers
    "chrome.exe": "browser",
    "msedge.exe": "browser",
    "brave.exe": "browser",
    "firefox.exe": "browser",
    "opera.exe": "browser",

    # Terminals
    "windowsterminal.exe": "terminal",
    "powershell.exe": "terminal",
    "cmd.exe": "terminal",
    "bash.exe": "terminal",
    "wsl.exe": "terminal",
    "conhost.exe": "terminal",

    # Notes & Knowledge
    "obsidian.exe": "notes",
    "notion.exe": "notes",
    "onenote.exe": "notes",
    "zotero.exe": "notes",

    # Communication
    "slack.exe": "communication",
    "teams.exe": "communication",
    "discord.exe": "communication",
    "telegram.exe": "communication",
    "whatsapp.exe": "communication",
}


class AppWindowInfo(BaseModel):
    hwnd: int = Field(..., description="Window handle")
    title: str = Field(..., description="Sanitized window title")
    process_name: str = Field(..., description="Executable name (e.g. code.exe)")
    pid: int = Field(..., description="Process ID")
    category: AppCategory = Field(default="other", description="Classified application domain")
    active_document: Optional[str] = Field(default=None, description="Inferred active file or tab name")
    is_foreground: bool = Field(default=False, description="Whether this window is currently in active focus")


# Testing mock state
_mock_mode: bool = False
_mock_windows: List[Dict[str, Any]] = []


def set_mock_tracker_mode(enabled: bool, mock_windows: Optional[List[Dict[str, Any]]] = None):
    """Enables mock window tracking for headless unit tests."""
    global _mock_mode, _mock_windows
    _mock_mode = enabled
    _mock_windows = mock_windows or []


class MultiAppTracker:
    """
    Enables zero-latency multi-window desktop inspection and app categorization.
    """

    def __init__(self):
        pass

    def get_foreground_window(self) -> Optional[AppWindowInfo]:
        """Returns metadata for the current foreground active window."""
        windows = self.enumerate_active_windows()
        for w in windows:
            if w.is_foreground:
                return w
        return windows[0] if windows else None

    def enumerate_active_windows(self) -> List[AppWindowInfo]:
        """
        Enumerates all visible, titled top-level desktop windows in < 5ms.
        """
        if _mock_mode:
            results = []
            for w in _mock_windows:
                clean_title, _ = context_sanitizer.sanitize(w.get("title", ""))
                cat = PROCESS_CATEGORIES.get(w.get("process_name", "").lower(), "other")
                doc = self._infer_active_document(clean_title, cat)
                results.append(AppWindowInfo(
                    hwnd=w.get("hwnd", 100),
                    title=clean_title,
                    process_name=w.get("process_name", "unknown.exe"),
                    pid=w.get("pid", 1234),
                    category=cat,
                    active_document=doc,
                    is_foreground=w.get("is_foreground", False)
                ))
            return results

        if sys.platform != "win32" or not win32gui or not win32process:
            return []

        fg_hwnd = win32gui.GetForegroundWindow()
        windows: List[AppWindowInfo] = []

        def enum_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            raw_title = win32gui.GetWindowText(hwnd).strip()
            if not raw_title or len(raw_title) < 2:
                return True

            # Ignore tooltips or system helper overlays
            if raw_title in ("Program Manager", "Settings", "Cortana", "Phenom Mini Overlay"):
                return True

            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc_name = psutil.Process(pid).name().lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                proc_name = "unknown.exe"
                pid = 0

            # Redact credentials from title per Rule 11
            clean_title, _ = context_sanitizer.sanitize(raw_title)
            category = PROCESS_CATEGORIES.get(proc_name, "other")
            doc = self._infer_active_document(clean_title, category)

            windows.append(AppWindowInfo(
                hwnd=hwnd,
                title=clean_title,
                process_name=proc_name,
                pid=pid,
                category=category,
                active_document=doc,
                is_foreground=(hwnd == fg_hwnd)
            ))
            return True

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            logger.warning(f"Error enumerating desktop windows: {e}")

        return windows

    def _infer_active_document(self, title: str, category: AppCategory) -> Optional[str]:
        """Infers the active file name, project, or tab title from window text."""
        if not title:
            return None

        # VS Code / Cursor / JetBrains style: 'filename.ext - Project - Visual Studio Code'
        if category == "ide":
            parts = title.split(" - ")
            if len(parts) >= 2:
                return parts[0].strip()
            return title

        # Browser style: 'Article Title - Browser Name'
        if category == "browser":
            parts = title.split(" - ")
            if len(parts) >= 2:
                return parts[0].strip()
            return title

        # Terminal style: 'Terminal - powershell' or current path
        if category == "terminal":
            return title

        # Notes style: 'Daily Note - Obsidian v1.5'
        if category == "notes":
            return title.split(" - ")[0].strip()

        return None


multi_app_tracker = MultiAppTracker()
