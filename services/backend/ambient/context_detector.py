"""
Phenom Context Detector
Inspects foreground application state on Windows and provides context-aware automatic
mode adaptation across Work, Study, Chill/Gaming, and Deep Focus with hysteresis filtering.
"""

import sys
import time
import logging
from typing import Optional, Dict, Any, List
import psutil

from services.backend.modes.mode_manager import mode_manager, AssistantMode

logger = logging.getLogger("phenom.context_detector")

# Known process name categorizations
PROCESS_CATEGORY_MAP: Dict[str, AssistantMode] = {
    # Work: IDEs, terminals, spreadsheets, productivity suites
    "code.exe": AssistantMode.WORK,
    "cursor.exe": AssistantMode.WORK,
    "pycharm64.exe": AssistantMode.WORK,
    "devenv.exe": AssistantMode.WORK,
    "windowsterminal.exe": AssistantMode.WORK,
    "powershell.exe": AssistantMode.WORK,
    "cmd.exe": AssistantMode.WORK,
    "slack.exe": AssistantMode.WORK,
    "teams.exe": AssistantMode.WORK,
    "excel.exe": AssistantMode.WORK,
    "winword.exe": AssistantMode.WORK,
    "powerpnt.exe": AssistantMode.WORK,

    # Study: Research tools, document viewers, notes
    "obsidian.exe": AssistantMode.STUDY,
    "notion.exe": AssistantMode.STUDY,
    "zotero.exe": AssistantMode.STUDY,
    "acrobat.exe": AssistantMode.STUDY,
    "acrord32.exe": AssistantMode.STUDY,
    "foxitpdfreader.exe": AssistantMode.STUDY,
    "drawio.exe": AssistantMode.STUDY,

    # Chill / Gaming: Game launchers, media players, chat
    "steam.exe": AssistantMode.CHILL,
    "epicgameslauncher.exe": AssistantMode.CHILL,
    "vlc.exe": AssistantMode.CHILL,
    "spotify.exe": AssistantMode.CHILL,
    "discord.exe": AssistantMode.CHILL,
    "gta5.exe": AssistantMode.CHILL,
    "cyberpunk2077.exe": AssistantMode.CHILL,
}


def classify_process(process_name: Optional[str]) -> Optional[AssistantMode]:
    """Maps a process executable name to its corresponding AssistantMode."""
    if not process_name:
        return None
    clean = process_name.strip().lower()
    return PROCESS_CATEGORY_MAP.get(clean)


def get_foreground_process_name() -> Optional[str]:
    """Samples the active foreground window process executable on Windows."""
    if sys.platform != "win32":
        return None
    try:
        import win32gui
        import win32process
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid <= 0:
            return None
        proc = psutil.Process(pid)
        return proc.name().lower()
    except Exception:
        return None


class ContextDetector:
    """
    Evaluates foreground application context and performs stable, hysteresis-governed
    mode transitions.
    """

    def __init__(self, hysteresis_seconds: float = 5.0):
        self.hysteresis_seconds = hysteresis_seconds
        self.is_auto_switch_enabled = True
        self._candidate_mode: Optional[AssistantMode] = None
        self._candidate_since: float = 0.0
        self._last_detected_proc: Optional[str] = None

    def sample_and_evaluate(
        self,
        override_process: Optional[str] = None,
        now_ts: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Samples foreground process, applies hysteresis filter, and switches mode if stable.
        """
        now = now_ts if now_ts is not None else time.time()
        proc_name = override_process or get_foreground_process_name()
        self._last_detected_proc = proc_name

        recommended_mode = classify_process(proc_name)
        current_mode = mode_manager.get_current_mode()
        switched = False

        # If process doesn't map to a specific mode, or user locked in Deep Focus manually, do not switch
        if current_mode == AssistantMode.DEEP_FOCUS and not override_process:
            return {
                "detected_process": proc_name,
                "recommended_mode": recommended_mode.value if recommended_mode else None,
                "switched": False,
                "active_mode": current_mode.value,
                "reason": "locked_in_deep_focus"
            }

        if recommended_mode and recommended_mode != current_mode:
            if self._candidate_mode != recommended_mode:
                # New candidate mode detected; start hysteresis clock
                self._candidate_mode = recommended_mode
                self._candidate_since = now
            else:
                # Same candidate maintained; check if hysteresis threshold exceeded
                elapsed = now - self._candidate_since
                if elapsed >= self.hysteresis_seconds:
                    if self.is_auto_switch_enabled:
                        mode_manager.set_mode(recommended_mode.value)
                        switched = True
                        logger.info(
                            f"[ContextDetector] Auto-switched to {recommended_mode.value} "
                            f"after {elapsed:.1f}s on {proc_name}"
                        )
                    self._candidate_mode = None
                    self._candidate_since = 0.0
        else:
            # Matches current mode or unknown process; reset candidate
            self._candidate_mode = None
            self._candidate_since = 0.0

        return {
            "detected_process": proc_name,
            "recommended_mode": recommended_mode.value if recommended_mode else None,
            "switched": switched,
            "active_mode": mode_manager.get_current_mode().value
        }


# Global context detector instance
context_detector = ContextDetector()
