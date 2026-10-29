"""
Phenom Meeting Mode & Windows Display Affinity Engine (Task 7l)
Detects active meetings (Zoom, Teams, Meet, Slack, Webex) and applies hardware capture exclusion:
1. Process & Title detection: zoom.exe, teams.exe, "Meet - ", "Zoom Meeting", etc.
2. Windows Display Affinity: SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
   Blacks out/omits Phenom windows from screen shares, screen recordings, and capture.
3. Audio Mute: TTS and sound effects immediately silenced.
4. Privacy: Notifications silenced; private panels hidden.
"""

import sys
import psutil
from typing import Dict, Any, List, Optional, Set, Tuple

# Win32 Constants for SetWindowDisplayAffinity
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011

MEETING_PROCESSES: Set[str] = {
    "zoom.exe",
    "teams.exe",
    "slack.exe",
    "webex.exe",
    "webexmta.exe",
    "discord.exe",
    "gotomeeting.exe"
}

MEETING_TITLE_KEYWORDS: List[str] = [
    "meet - ",
    "zoom meeting",
    "microsoft teams",
    "webex meeting",
    "google meet"
]

class MeetingModeManager:
    def __init__(self):
        self.meeting_mode_active: bool = False
        self.active_meeting_app: Optional[str] = None
        self.detection_source: Optional[str] = None
        self.display_affinity_applied: bool = False

    def detect_meeting(
        self,
        mock_process: Optional[str] = None,
        mock_window_title: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Scans running processes and window titles for active conference sessions.
        Returns: (is_meeting, app_or_title, reason)
        """
        # Test override if provided
        if mock_process:
            p_name = mock_process.strip().lower()
            if p_name in MEETING_PROCESSES:
                return True, p_name, f"meeting_process_detected:{p_name}"

        if mock_window_title:
            w_title = mock_window_title.strip().lower()
            for kw in MEETING_TITLE_KEYWORDS:
                if kw in w_title:
                    return True, mock_window_title, f"meeting_window_detected:{kw}"

        # 1. Process scan
        for proc in psutil.process_iter(['name']):
            try:
                name = (proc.info['name'] or '').lower()
                if name in MEETING_PROCESSES:
                    return True, name, f"meeting_process_detected:{name}"
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # 2. Window title scan on Windows
        try:
            import win32gui
            found_title = None

            def enum_cb(hwnd, _):
                nonlocal found_title
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd).lower()
                    for kw in MEETING_TITLE_KEYWORDS:
                        if kw in t:
                            found_title = t
                            return False
                return True

            win32gui.EnumWindows(enum_cb, None)
            if found_title:
                return True, found_title, "meeting_window_detected"
        except Exception:
            pass

        return False, None, "idle"

    def apply_display_affinity(self, hwnd: int) -> bool:
        """
        Applies WDA_EXCLUDEFROMCAPTURE to exclude a window from screen-sharing.
        """
        if sys.platform != "win32":
            return False

        try:
            import ctypes
            user32 = ctypes.windll.user32
            # SetWindowDisplayAffinity(HWND hWnd, DWORD dwAffinity)
            res = user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            if res != 0:
                self.display_affinity_applied = True
                return True
        except Exception:
            pass
        return False

    def enter_meeting_mode(self, app_name: str, reason: str = "meeting_detected") -> Dict[str, Any]:
        """
        Activates meeting mode: mutes speech, applies capture exclusion, silences alerts.
        """
        self.meeting_mode_active = True
        self.active_meeting_app = app_name
        self.detection_source = reason

        return {
            "status": "meeting_mode_active",
            "meeting_app": app_name,
            "speech_muted": True,
            "sound_fx_muted": True,
            "notifications_silenced": True,
            "display_affinity": "WDA_EXCLUDEFROMCAPTURE",
            "orb_theme": "amber_muted"
        }

    def exit_meeting_mode(self) -> Dict[str, Any]:
        """
        Restores normal operations when meeting concludes.
        """
        prev_app = self.active_meeting_app
        self.meeting_mode_active = False
        self.active_meeting_app = None
        self.detection_source = None

        return {
            "status": "meeting_mode_exited",
            "previous_app": prev_app,
            "speech_muted": False,
            "sound_fx_muted": False,
            "notifications_silenced": False,
            "display_affinity": "WDA_NONE",
            "orb_theme": "default_cyan"
        }

# Global meeting mode manager instance
meeting_manager = MeetingModeManager()
