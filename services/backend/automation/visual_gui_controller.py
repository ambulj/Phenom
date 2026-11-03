"""
Phenom Closed-Loop Visual GUI Controller
Executes visual interaction plans with pre-action frame capture,
coordinate validation, message injection, settle delay, post-action frame capture,
and visual delta verification. Integrates sub-500ms Human Takeover interrupt.
"""

import time
import uuid
import asyncio
from typing import Optional, List, Dict, Any, Callable
from PIL import Image

from services.backend.schemas.virtual_desktop import (
    GuiActionRequest,
    VisualFeedbackReport,
    ActionType,
    MouseButton,
)
from services.backend.schemas.protocol import (
    AutomationTakeoverPromptMsg,
    AutomationTakeoverPromptPayload,
)
from services.backend.automation.virtual_desktop_driver import (
    VirtualDesktopDriver,
    virtual_desktop_driver,
)
from services.backend.automation.virtual_desktop_manager import (
    VirtualDesktopManager,
    virtual_desktop_manager,
)
from services.backend.automation.human_takeover import (
    HumanTakeoverAbort,
    takeover_manager,
)
from services.backend.vision.delta_detector import DeltaDetector
from services.backend.voice.sound_fx import sound_fx
from services.backend.safety.guardian import guardian


class VisualGuiController:
    """
    Coordinates closed-loop visual desktop automation, verifying state delta
    between pre- and post-action frames and reacting to human takeover interruptions.
    """

    def __init__(
        self,
        driver: Optional[VirtualDesktopDriver] = None,
        manager: Optional[VirtualDesktopManager] = None,
    ):
        self._driver = driver
        self._manager = manager
        self._broadcaster: Optional[Callable[[Dict[str, Any]], Any]] = None
        self._history: List[VisualFeedbackReport] = []

    @property
    def driver(self) -> VirtualDesktopDriver:
        return self._driver or virtual_desktop_driver

    @property
    def manager(self) -> VirtualDesktopManager:
        return self._manager or virtual_desktop_manager

    def register_broadcaster(self, broadcaster: Callable[[Dict[str, Any]], Any]) -> None:
        """Registers a callback or async function to broadcast WebSocket protocol messages."""
        self._broadcaster = broadcaster

    def _broadcast_takeover(self, session_id: str, reason: str, app_name: Optional[str] = None):
        """Emits automation.takeover_prompt protocol message to connected desktop clients."""
        msg = AutomationTakeoverPromptMsg(
            payload=AutomationTakeoverPromptPayload(
                reason=reason,
                session_id=session_id,
                app_name=app_name or "Virtual Desktop Application",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        )
        msg_dict = msg.model_dump()
        if self._broadcaster:
            try:
                res = self._broadcaster(msg_dict)
                if asyncio.iscoroutine(res):
                    try:
                        loop = asyncio.get_running_loop()
                        if loop.is_running():
                            loop.create_task(res)
                    except RuntimeError:
                        pass
            except Exception:
                pass

    def check_takeover_and_guardian(self, session_id: str) -> None:
        """
        Enforces Guardian halt and Human Takeover invariants.
        Aborts sequence in < 500ms when human input is detected.
        """
        if guardian.is_halted:
            raise PermissionError("Action aborted: Guardian kill switch is active.")

        if takeover_manager.is_paused:
            sound_fx.play_automation_halt()
            self._broadcast_takeover(
                session_id=session_id,
                reason="Physical user input detected during virtual automation task.",
            )
            raise HumanTakeoverAbort(
                "Automation paused: Physical user takeover detected (< 500ms abort sequence)."
            )

    def execute_action(
        self,
        request: GuiActionRequest,
        settle_delay_s: float = 0.1,
        delta_threshold: float = 0.0005,
    ) -> VisualFeedbackReport:
        """
        Synchronously executes a closed-loop GUI action:
        1. Pre-action check (Guardian + Takeover)
        2. Window validation
        3. Pre-action RAM capture
        4. Coordinate & action injection
        5. Settle delay
        6. Post-action check (Guardian + Takeover)
        7. Post-action RAM capture
        8. Delta computation & report generation
        """
        start_time = time.perf_counter()

        # 1. Enforce safety checks first (Guardian kill switch & Takeover)
        self.check_takeover_and_guardian(request.session_id)

        session = self.manager.get_session(request.session_id)
        if not session or not session.is_active:
            raise ValueError(f"Session '{request.session_id}' not found or inactive.")

        # 2. Window validation
        rect = self.manager.backend.get_window_rect(request.hwnd)
        width = max(1, rect[2] - rect[0])
        height = max(1, rect[3] - rect[1])

        if request.x is not None and (request.x < 0 or request.x > width + 50):
            raise ValueError(f"Coordinate X={request.x} outside window bounds (width={width})")
        if request.y is not None and (request.y < 0 or request.y > height + 50):
            raise ValueError(f"Coordinate Y={request.y} outside window bounds (height={height})")

        # 3. Capture pre-action frame in RAM
        pre_img = self.driver.capture_window_ram(request.hwnd)
        pre_b64 = self.driver.capture_window_base64(request.hwnd, max_dimension=640, quality=70)

        # 4. Dispatch action via driver
        action_type = request.action_type
        success = False
        error_msg: Optional[str] = None

        try:
            if action_type == ActionType.CLICK:
                x = request.x or 10
                y = request.y or 10
                success = self.driver.post_mouse_click(request.hwnd, x, y, request.button)

            elif action_type == ActionType.DOUBLE_CLICK:
                x = request.x or 10
                y = request.y or 10
                success = self.driver.post_mouse_double_click(request.hwnd, x, y, request.button)

            elif action_type == ActionType.RIGHT_CLICK:
                x = request.x or 10
                y = request.y or 10
                success = self.driver.post_mouse_click(request.hwnd, x, y, MouseButton.RIGHT)

            elif action_type == ActionType.DRAG:
                x1 = request.x or 10
                y1 = request.y or 10
                x2 = request.x2 or x1 + 50
                y2 = request.y2 or y1 + 50
                success = self.driver.post_mouse_drag(request.hwnd, x1, y1, x2, y2)

            elif action_type == ActionType.TYPE_TEXT:
                text = request.text or ""
                success = self.driver.post_text(request.hwnd, text)

            elif action_type == ActionType.KEY_PRESS:
                key = request.key_name or request.key_code or "enter"
                success = self.driver.post_key(request.hwnd, key)

            elif action_type == ActionType.HOTKEY:
                combo = request.text or request.key_name or "ctrl+s"
                success = self.driver.post_hotkey(request.hwnd, combo)

            else:
                raise ValueError(f"Unsupported action type: {action_type}")

        except Exception as e:
            error_msg = str(e)
            success = False

        # 5. Settle delay
        if settle_delay_s > 0:
            time.sleep(settle_delay_s)

        # 6. Post-action safety check
        self.check_takeover_and_guardian(request.session_id)

        # 7. Post-action RAM capture
        post_img = self.driver.capture_window_ram(request.hwnd)
        post_b64 = self.driver.capture_window_base64(request.hwnd, max_dimension=640, quality=70)

        # 8. Compute visual delta
        detector = DeltaDetector(threshold=delta_threshold)
        detector.compute_delta(pre_img)
        delta_detected, delta_score = detector.compute_delta(post_img)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        report = VisualFeedbackReport(
            action_id=str(uuid.uuid4()),
            success=success,
            delta_detected=delta_detected,
            delta_score=round(delta_score, 4),
            duration_ms=round(duration_ms, 2),
            error=error_msg,
            pre_action_image_b64=pre_b64,
            post_action_image_b64=post_b64,
        )

        self._history.append(report)
        return report

    async def execute_action_async(
        self,
        request: GuiActionRequest,
        settle_delay_s: float = 0.1,
    ) -> VisualFeedbackReport:
        """
        Asynchronously executes closed-loop GUI action without blocking async event loops.
        """
        # Run blocking Win32 message loop / capture operations in default thread pool executor
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self.execute_action,
            request,
            settle_delay_s,
        )


# Global controller instance
visual_gui_controller = VisualGuiController()
