"""
Phenom Ambient Vision Co-Pilot Engine (VIS-01, GOV-01)
Continuous, non-invasive background screen comprehension loop.
- Operates at configurable 3-5s sampling intervals with zero cursor or focus disruption.
- Strictly zero disk writes: all frames and masking remain in RAM (PIL.Image / io.BytesIO).
- Strict privacy gate: automatically skips blacklisted windows (credentials, banking, incognito, private chats)
  and marks context with [BLACKLOCKED_WINDOW_SKIPPED].
- Perceptual delta comparison: skips VLM evaluation when screen change is < 2%.
- Adaptive governor integration: pauses during 3D gaming or high GPU load (> 85%), resuming at idle.
- Sub-1ms synchronous Guardian kill switch SLA (SAF-02).
"""

import asyncio
import inspect
import os
import time
from typing import Callable, List, Optional, Tuple

import psutil
from PIL import Image

from services.backend.schemas.ambient_vision import AmbientCopilotConfig, AmbientScreenContext
from services.backend.vision.delta_detector import delta_detector, DeltaDetector
from services.backend.vision.frame_grabber import frame_grabber, FrameGrabber
from services.backend.vision.moondream_client import moondream_client, MoondreamVisionClient
from services.backend.vision.privacy_masker import privacy_masker, PrivacyMasker

try:
    import win32gui
    import win32process
except ImportError:
    win32gui = None
    win32process = None


class AmbientVisionCopilot:
    def __init__(
        self,
        config: Optional[AmbientCopilotConfig] = None,
        grabber: Optional[FrameGrabber] = None,
        masker: Optional[PrivacyMasker] = None,
        detector: Optional[DeltaDetector] = None,
        vlm: Optional[MoondreamVisionClient] = None,
    ):
        self.config = config or AmbientCopilotConfig()
        self.grabber = grabber or frame_grabber
        self.masker = masker or privacy_masker
        self.detector = detector or delta_detector
        self.vlm = vlm or moondream_client

        # Lifecycle flags
        self._is_running: bool = False
        self._is_halted: bool = False
        self._is_suspended: bool = False
        self._suspension_reason: Optional[str] = None
        self._loop_task: Optional[asyncio.Task] = None

        # State cache
        self._last_context: Optional[AmbientScreenContext] = None
        self._broadcasters: List[Callable] = []

        # Mock / Test hooks
        self._mock_foreground_window: Optional[Tuple[str, str]] = None
        self._mock_frame: Optional[Image.Image] = None
        self._mock_vlm_response: Optional[dict] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_halted(self) -> bool:
        return self._is_halted

    @property
    def is_suspended(self) -> bool:
        return self._is_suspended

    def register_broadcaster(self, cb: Callable):
        """Registers a callback to broadcast VISION_AMBIENT_UPDATE over WebSocket."""
        if cb not in self._broadcasters:
            self._broadcasters.append(cb)

    def set_mock_hooks(
        self,
        window_title: Optional[str] = None,
        process_name: Optional[str] = None,
        frame: Optional[Image.Image] = None,
        vlm_response: Optional[dict] = None,
    ):
        """Allows injecting mocked environment parameters for deterministic unit tests."""
        if window_title is not None or process_name is not None:
            self._mock_foreground_window = (window_title or "", process_name or "")
        if frame is not None:
            self._mock_frame = frame
        if vlm_response is not None:
            self._mock_vlm_response = vlm_response

    def clear_mock_hooks(self):
        """Clears test mocks."""
        self._mock_foreground_window = None
        self._mock_frame = None
        self._mock_vlm_response = None

    def get_foreground_info(self) -> Tuple[str, str]:
        """
        Retrieves active foreground window title and process name.
        Safe across Windows and CI environments.
        """
        if self._mock_foreground_window is not None:
            return self._mock_foreground_window

        if os.name != "nt" or win32gui is None or win32process is None:
            return "Desktop", "explorer.exe"

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return "", ""
            title = win32gui.GetWindowText(hwnd).strip()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            p_name = ""
            if pid > 0:
                try:
                    p_name = psutil.Process(pid).name()
                except Exception:
                    pass
            return title, p_name
        except Exception:
            return "", ""

    async def step(self) -> AmbientScreenContext:
        """
        Executes a single ambient vision evaluation step.
        """
        if self._is_halted:
            raise PermissionError("AmbientVisionCopilot is HALTED by Guardian kill switch.")

        now = time.time()

        # 1. Check if suspended by resource governor
        if self._is_suspended:
            ctx = AmbientScreenContext(
                timestamp=now,
                window_title=self._last_context.window_title if self._last_context else "",
                process_name=self._last_context.process_name if self._last_context else "",
                scene_summary="Ambient vision suspended by Resource Governor",
                is_suspended=True,
                suspension_reason=self._suspension_reason or "governor_suspend",
                has_changed=False,
            )
            self._last_context = ctx
            return ctx

        # 2. Inspect active foreground window
        title, process_name = self.get_foreground_info()

        # 3. Privacy Blacklist Gate
        if self.masker.is_window_blacklisted(title, process_name):
            ctx = AmbientScreenContext(
                timestamp=now,
                window_title="[REDACTED]",
                process_name=process_name,
                is_sensitive=True,
                is_blacklisted=True,
                scene_summary="[BLACKLOCKED_WINDOW_SKIPPED]",
                detected_errors=[],
                detected_text_snippets=[],
                delta_score=0.0,
                has_changed=False,
                is_suspended=False,
                suspension_reason=None,
            )
            self._last_context = ctx
            await self._broadcast_update(ctx)
            return ctx

        # 4. Grab frame into in-memory PIL.Image (Zero Disk Writes)
        if self._mock_frame is not None:
            raw_frame = self._mock_frame
        else:
            raw_frame = self.grabber.grab_frame()

        # 5. Mask any sensitive sub-windows/fields on in-memory buffer
        masked_frame, applied_masks = self.masker.mask_sensitive_windows(raw_frame)
        is_sensitive = len(applied_masks) > 0

        # 6. Perceptual Delta Hashing
        has_changed, delta_score = self.detector.compute_delta(masked_frame)

        # 7. VLM Evaluation Gate
        if not has_changed and self._last_context is not None and not self._last_context.is_blacklisted:
            # Screen content is stationary (< 2% change); reuse previous summary and update timestamp
            ctx = AmbientScreenContext(
                timestamp=now,
                window_title=title,
                process_name=process_name,
                is_sensitive=is_sensitive or self._last_context.is_sensitive,
                is_blacklisted=False,
                scene_summary=self._last_context.scene_summary,
                detected_errors=self._last_context.detected_errors,
                detected_text_snippets=self._last_context.detected_text_snippets,
                delta_score=delta_score,
                has_changed=False,
                vlm_model=self.vlm.model_name,
                inference_latency_ms=0.0,
                is_suspended=False,
                suspension_reason=None,
            )
            self._last_context = ctx
            return ctx

        # 8. Query Local VLM
        if self._mock_vlm_response is not None:
            vlm_res = self._mock_vlm_response
        else:
            vlm_res = await self.vlm.query_ambient_screen(masked_frame)

        scene_desc = vlm_res.get("description") or "Screen captured; no notable elements detected."
        errors = vlm_res.get("detected_errors") or []
        latency_ms = vlm_res.get("latency_ms", 0.0)

        ctx = AmbientScreenContext(
            timestamp=now,
            window_title=title,
            process_name=process_name,
            is_sensitive=is_sensitive,
            is_blacklisted=False,
            scene_summary=scene_desc,
            detected_errors=errors,
            detected_text_snippets=[],
            delta_score=delta_score,
            has_changed=True,
            vlm_model=self.vlm.model_name,
            inference_latency_ms=latency_ms,
            is_suspended=False,
            suspension_reason=None,
        )
        self._last_context = ctx
        await self._broadcast_update(ctx)
        return ctx

    async def _broadcast_update(self, ctx: AmbientScreenContext):
        payload = {
            "type": "VISION_AMBIENT_UPDATE",
            "context": ctx.model_dump(),
        }
        for cb in self._broadcasters:
            try:
                res = cb(payload)
                if inspect.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception:
                pass

    def get_context(self) -> AmbientScreenContext:
        """Returns the current cached ambient screen context."""
        if self._last_context is not None:
            return self._last_context
        return AmbientScreenContext(
            timestamp=time.time(),
            window_title="",
            process_name="",
            scene_summary="No ambient screen context captured yet.",
            is_suspended=self._is_suspended,
            suspension_reason=self._suspension_reason,
        )

    def configure(
        self,
        is_enabled: Optional[bool] = None,
        interval_seconds: Optional[float] = None,
        delta_threshold: Optional[float] = None,
        custom_blacklists: Optional[List[str]] = None,
    ):
        """Updates runtime configuration."""
        if is_enabled is not None:
            self.config.is_enabled = is_enabled
        if interval_seconds is not None:
            self.config.interval_seconds = max(1.0, interval_seconds)
        if delta_threshold is not None:
            self.config.delta_threshold = delta_threshold
            self.detector.threshold = delta_threshold
        if custom_blacklists:
            for pat in custom_blacklists:
                if pat not in self.config.custom_blacklists:
                    self.config.custom_blacklists.append(pat)
                    self.masker.add_pattern(pat)

    def pause(self, reason: str = "governor_suspend"):
        """Pauses the vision loop (e.g. called by Resource Governor during 3D gaming)."""
        self._is_suspended = True
        self._suspension_reason = reason
        if self._last_context:
            self._last_context.is_suspended = True
            self._last_context.suspension_reason = reason

    def resume(self):
        """Resumes the vision loop (e.g. called by Resource Governor after 3D gaming exits)."""
        self._is_suspended = False
        self._suspension_reason = None
        if self._last_context:
            self._last_context.is_suspended = False
            self._last_context.suspension_reason = None

    def halt(self):
        """
        Synchronous Guardian kill switch halt (< 1ms SLA).
        Cancels active asyncio task immediately, sets _is_halted = True,
        and wipes cached memory.
        """
        self._is_halted = True
        self._is_running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        self._last_context = None

    def reset(self):
        """Resets copilot after Guardian resume."""
        self._is_halted = False
        self._is_suspended = False
        self._suspension_reason = None
        self.detector.reset()
        self.clear_mock_hooks()

    async def start(self):
        """Starts the background continuous loop."""
        if self._is_running or self._is_halted:
            return
        self._is_running = True
        self._loop_task = asyncio.create_task(self._run_copilot_loop())

    async def stop(self):
        """Stops the background continuous loop."""
        self._is_running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    async def _run_copilot_loop(self):
        while self._is_running and not self._is_halted:
            try:
                if self.config.is_enabled and not self._is_suspended:
                    await self.step()
            except Exception:
                pass
            await asyncio.sleep(self.config.interval_seconds)


ambient_copilot = AmbientVisionCopilot()
