"""Window Focus Synchronizer for Phenom (Milestone 25 Phase 3).

Tracks desktop window hierarchies, coordinates foreground window switching,
and restores pre-workflow focus stacks safely (WIN-02.1).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.orchestrator.window_focus")


class Rule8ViolationError(Exception):
    """Raised when window focus targets payment or checkout dialogs."""
    pass


class WindowFocusState(BaseModel):
    window_id: str
    process_name: str
    title: str
    is_foreground: bool
    bounds: Tuple[int, int, int, int]  # (x, y, width, height)


class WorkspaceLayout(BaseModel):
    active_window: Optional[WindowFocusState] = None
    open_windows: List[WindowFocusState] = Field(default_factory=list)
    timestamp: float = 0.0


class WindowFocusSynchronizer:
    """Synchronizes window foreground state and maintains a restoration stack."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing|stripe|paypal)\b",
        re.IGNORECASE,
    )

    DEFAULT_WINDOWS: List[Dict[str, Any]] = [
        {
            "window_id": "win_ide_01",
            "process_name": "Code.exe",
            "title": "Phenom - Visual Studio Code",
            "bounds": (0, 0, 1280, 1080),
        },
        {
            "window_id": "win_browser_02",
            "process_name": "msedge.exe",
            "title": "Microsoft Edge - Documentation & APIs",
            "bounds": (1280, 0, 640, 540),
        },
        {
            "window_id": "win_term_03",
            "process_name": "WindowsTerminal.exe",
            "title": "PowerShell - Backend Services",
            "bounds": (1280, 540, 640, 540),
        },
    ]

    def __init__(self) -> None:
        self._focus_stack: List[str] = []
        self._current_foreground_id: str = "win_ide_01"

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Window focus synchronization halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: window title targeting payments or checkout is strictly prohibited. Found: {text}"
            )

    def get_layout(self) -> WorkspaceLayout:
        """Query active desktop windows and identify foreground window."""
        self._check_guardian()

        windows: List[WindowFocusState] = []
        active: Optional[WindowFocusState] = None

        for w in self.DEFAULT_WINDOWS:
            self._validate_rule_8(w["title"])
            is_fg = w["window_id"] == self._current_foreground_id
            state = WindowFocusState(
                window_id=w["window_id"],
                process_name=w["process_name"],
                title=w["title"],
                is_foreground=is_fg,
                bounds=w["bounds"],
            )
            windows.append(state)
            if is_fg:
                active = state

        return WorkspaceLayout(
            active_window=active,
            open_windows=windows,
        )

    def switch_focus(self, target: str) -> WindowFocusState:
        """Switch foreground window to target by ID or title keyword."""
        self._check_guardian()
        self._validate_rule_8(target)

        target_lower = target.lower()
        found: Optional[Dict[str, Any]] = None

        for w in self.DEFAULT_WINDOWS:
            if w["window_id"] == target or target_lower in w["process_name"].lower() or target_lower in w["title"].lower():
                found = w
                break

        if not found:
            raise ValueError(f"Window target '{target}' not found among active desktop windows.")

        # Push old to stack
        if self._current_foreground_id != found["window_id"]:
            self._focus_stack.append(self._current_foreground_id)
            self._current_foreground_id = found["window_id"]

        return WindowFocusState(
            window_id=found["window_id"],
            process_name=found["process_name"],
            title=found["title"],
            is_foreground=True,
            bounds=found["bounds"],
        )

    def restore_previous_focus(self) -> Optional[WindowFocusState]:
        """Restore previous foreground window from focus stack."""
        self._check_guardian()
        if not self._focus_stack:
            return None

        prev_id = self._focus_stack.pop()
        self._current_foreground_id = prev_id

        found = next((w for w in self.DEFAULT_WINDOWS if w["window_id"] == prev_id), self.DEFAULT_WINDOWS[0])
        return WindowFocusState(
            window_id=found["window_id"],
            process_name=found["process_name"],
            title=found["title"],
            is_foreground=True,
            bounds=found["bounds"],
        )


# Singleton instance
window_focus_synchronizer = WindowFocusSynchronizer()
