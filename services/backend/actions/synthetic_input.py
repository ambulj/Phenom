"""Win32 Synthetic Input Controller with smooth Bezier mouse trajectories and Guardian E-Stop."""

from __future__ import annotations

import ctypes
import math
import random
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from services.backend.actions.bezier_trajectory import BezierTrajectoryGenerator
from services.backend.safety.guardian import guardian
from services.backend.schemas.computer_use import (
    ActionItem,
    ActionSequencePayload,
    BezierPath,
    ClickAction,
    ClickType,
    DragAction,
    ExecutionResult,
    HotKeyAction,
    MoveAction,
    Point2D,
    ScrollAction,
    TypeAction,
)

# Win32 Constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_BACK = 0x08

KEY_MAP: Dict[str, int] = {
    "ctrl": VK_CONTROL,
    "control": VK_CONTROL,
    "shift": VK_SHIFT,
    "alt": VK_MENU,
    "enter": VK_RETURN,
    "return": VK_RETURN,
    "tab": VK_TAB,
    "escape": VK_ESCAPE,
    "esc": VK_ESCAPE,
    "backspace": VK_BACK,
}


class SyntheticInputController:
    """Dispatches human-like synthetic desktop inputs with sub-10ms Guardian Kill Switch checks."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.trajectory_gen = BezierTrajectoryGenerator()
        self._lock = threading.RLock()
        self._current_pos = Point2D(x=100, y=100)
        self.recorded_events: List[Dict[str, Any]] = []
        self._is_windows = sys.platform == "win32" and not dry_run

    def get_cursor_position(self) -> Point2D:
        """Gets current screen cursor position."""
        if self._is_windows:
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = POINT()
            try:
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                self._current_pos = Point2D(x=pt.x, y=pt.y)
            except Exception:
                pass
        return self._current_pos

    def set_cursor_position(self, x: int, y: int) -> None:
        """Directly positions the cursor."""
        self._current_pos = Point2D(x=x, y=y)
        if self._is_windows:
            try:
                ctypes.windll.user32.SetCursorPos(x, y)
            except Exception:
                pass

    def _sleep_with_guardian(self, duration_s: float) -> bool:
        """Sleeps while checking Guardian kill switch; returns False if halted."""
        start = time.perf_counter()
        while time.perf_counter() - start < duration_s:
            if guardian.is_halted:
                return False
            time.sleep(min(0.005, max(0.0, duration_s - (time.perf_counter() - start))))
        return not guardian.is_halted

    def move_smooth(self, target: Point2D, duration_ms: float = 200.0) -> Tuple[bool, Optional[BezierPath]]:
        """Moves cursor to target along a smooth cubic Bezier trajectory."""
        if guardian.is_halted:
            return False, None

        current = self.get_cursor_position()
        path = self.trajectory_gen.generate_path(current, target, duration_ms=duration_ms)

        if self.dry_run or not self._is_windows:
            self._current_pos = target
            self.recorded_events.append({"action": "move_smooth", "target": (target.x, target.y), "path_points": len(path.points)})
            return True, path

        # Step through trajectory points
        prev_time = 0.0
        for pt in path.points:
            if guardian.is_halted:
                return False, path
            delta_ms = pt.timestamp_ms - prev_time
            if delta_ms > 0:
                if not self._sleep_with_guardian(delta_ms / 1000.0):
                    return False, path
            self.set_cursor_position(pt.x, pt.y)
            prev_time = pt.timestamp_ms

        self.set_cursor_position(target.x, target.y)
        return True, path

    def click(self, action: ClickAction) -> bool:
        """Dispatches mouse click at specified coordinate."""
        if guardian.is_halted:
            return False

        if action.smooth_move:
            ok, _ = self.move_smooth(action.target)
            if not ok or guardian.is_halted:
                return False
        else:
            self.set_cursor_position(action.target.x, action.target.y)

        if action.pre_delay_ms > 0:
            if not self._sleep_with_guardian(action.pre_delay_ms / 1000.0):
                return False

        if self.dry_run or not self._is_windows:
            self.recorded_events.append({
                "action": "click",
                "target": (action.target.x, action.target.y),
                "type": action.click_type.value,
            })
            return True

        clicks_count = 2 if action.click_type == ClickType.DOUBLE else 1
        for _ in range(clicks_count):
            if guardian.is_halted:
                return False
            down_flag = MOUSEEVENTF_LEFTDOWN if action.click_type in (ClickType.LEFT, ClickType.DOUBLE) else MOUSEEVENTF_RIGHTDOWN
            up_flag = MOUSEEVENTF_LEFTUP if action.click_type in (ClickType.LEFT, ClickType.DOUBLE) else MOUSEEVENTF_RIGHTUP

            ctypes.windll.user32.mouse_event(down_flag, 0, 0, 0, 0)
            if not self._sleep_with_guardian(action.button_down_duration_ms / 1000.0):
                ctypes.windll.user32.mouse_event(up_flag, 0, 0, 0, 0)
                return False
            ctypes.windll.user32.mouse_event(up_flag, 0, 0, 0, 0)

            if clicks_count > 1:
                time.sleep(0.05)

        return True

    def drag(self, action: DragAction) -> bool:
        """Performs smooth drag and drop from start to end coordinate."""
        if guardian.is_halted:
            return False

        # Move to start
        ok, _ = self.move_smooth(action.start, duration_ms=150.0)
        if not ok or guardian.is_halted:
            return False

        if self.dry_run or not self._is_windows:
            self._current_pos = action.end
            self.recorded_events.append({"action": "drag", "start": (action.start.x, action.start.y), "end": (action.end.x, action.end.y)})
            return True

        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        ok, _ = self.move_smooth(action.end, duration_ms=action.duration_ms)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        return ok

    def type_text(self, action: TypeAction) -> bool:
        """Types text with natural WPM cadence and micro-delays."""
        if guardian.is_halted:
            return False

        if action.focus_target:
            click_act = ClickAction(target=action.focus_target, click_type=ClickType.LEFT)
            if not self.click(click_act) or guardian.is_halted:
                return False

        base_char_delay_s = 60.0 / (max(10.0, action.typing_speed_wpm) * 5.0)

        if self.dry_run or not self._is_windows:
            self.recorded_events.append({
                "action": "type",
                "text": action.text,
                "press_enter": action.press_enter,
            })
            return True

        for char in action.text:
            if guardian.is_halted:
                return False

            # Unicode keystroke dispatch
            char_code = ord(char)
            ctypes.windll.user32.keybd_event(0, char_code, KEYEVENTF_UNICODE, 0)
            ctypes.windll.user32.keybd_event(0, char_code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)

            delay = base_char_delay_s
            if action.randomize_delay:
                delay *= random.uniform(0.75, 1.25)
            if not self._sleep_with_guardian(delay):
                return False

        if action.press_enter:
            ctypes.windll.user32.keybd_event(VK_RETURN, 0, 0, 0)
            time.sleep(0.01)
            ctypes.windll.user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)

        return True

    def hotkey(self, action: HotKeyAction) -> bool:
        """Dispatches key combination (e.g. Ctrl+Shift+P)."""
        if guardian.is_halted:
            return False

        if self.dry_run or not self._is_windows:
            self.recorded_events.append({"action": "hotkey", "keys": action.keys})
            return True

        vk_codes: List[int] = []
        for k in action.keys:
            k_lower = k.lower()
            if k_lower in KEY_MAP:
                vk_codes.append(KEY_MAP[k_lower])
            elif len(k) == 1:
                vk_codes.append(ord(k.upper()))

        # Key down in order
        for code in vk_codes:
            ctypes.windll.user32.keybd_event(code, 0, 0, 0)

        self._sleep_with_guardian(action.hold_duration_ms / 1000.0)

        # Key up in reverse order
        for code in reversed(vk_codes):
            ctypes.windll.user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)

        return True

    def scroll(self, action: ScrollAction) -> bool:
        """Dispatches mouse scroll event."""
        if guardian.is_halted:
            return False

        if action.target:
            self.move_smooth(action.target, duration_ms=100.0)

        if self.dry_run or not self._is_windows:
            self.recorded_events.append({"action": "scroll", "clicks": action.clicks})
            return True

        wheel_delta = int(action.clicks * 120)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, wheel_delta, 0)
        return True

    def execute_sequence(self, payload: ActionSequencePayload) -> ExecutionResult:
        """Executes a complete batch of desktop actions with Guardian protection."""
        with self._lock:
            start_time = time.perf_counter()
            executed_count = 0

            if payload.abort_on_guardian and guardian.is_halted:
                return ExecutionResult(
                    success=False,
                    executed_actions=0,
                    total_actions=len(payload.actions),
                    duration_ms=0.0,
                    error="Execution blocked: Guardian Kill Switch is active",
                    guardian_halted=True,
                    final_cursor_position=self.get_cursor_position()
                )

            for act in payload.actions:
                if payload.abort_on_guardian and guardian.is_halted:
                    return ExecutionResult(
                        success=False,
                        executed_actions=executed_count,
                        total_actions=len(payload.actions),
                        duration_ms=(time.perf_counter() - start_time) * 1000.0,
                        error="Execution halted mid-sequence: Guardian triggered",
                        guardian_halted=True,
                        final_cursor_position=self.get_cursor_position()
                    )

                success = False
                if isinstance(act, ClickAction):
                    success = self.click(act)
                elif isinstance(act, MoveAction):
                    success, _ = self.move_smooth(act.target, duration_ms=act.duration_ms)
                elif isinstance(act, DragAction):
                    success = self.drag(act)
                elif isinstance(act, TypeAction):
                    success = self.type_text(act)
                elif isinstance(act, HotKeyAction):
                    success = self.hotkey(act)
                elif isinstance(act, ScrollAction):
                    success = self.scroll(act)

                if not success:
                    halted = guardian.is_halted
                    return ExecutionResult(
                        success=False,
                        executed_actions=executed_count,
                        total_actions=len(payload.actions),
                        duration_ms=(time.perf_counter() - start_time) * 1000.0,
                        error="Guardian halted action" if halted else "Action execution failed",
                        guardian_halted=halted,
                        final_cursor_position=self.get_cursor_position()
                    )

                executed_count += 1

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                success=True,
                executed_actions=executed_count,
                total_actions=len(payload.actions),
                duration_ms=duration_ms,
                final_cursor_position=self.get_cursor_position()
            )


# Global controller instance
synthetic_input = SyntheticInputController(dry_run=False)
