"""
Phenom Observable Motion Driver (WKF-05.1, WKF-05.2, WKF-05.3)
Coordinates:
- Smooth cubic Bezier cursor trajectory calculation at 1.2x human speed
- Pre-click visual target bounding-box halo emission to CyberHUD
- Sub-10ms low-level human takeover displacement detection (>15px delta)
"""

from __future__ import annotations

import os
import sys
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.desktop.bezier_trajectory_generator import BezierTrajectoryGenerator
from services.backend.desktop.visual_target_halo import VisualTargetHaloEmitter
from services.backend.desktop.human_takeover_hook import HumanTakeoverHook
from services.backend.schemas.desktop_choreography import BezierTrajectory, TargetHaloSpec
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.desktop.observable_motion")


class MotionExecutionResult(BaseModel):
    """Result of an observable motion glide sequence."""
    trajectory_id: str
    waypoint_count: int
    duration_ms: float
    target_halo: TargetHaloSpec
    human_takeover_triggered: bool = False
    takeover_latency_ms: Optional[float] = None
    success: bool = True
    speed_factor: float = 1.2


class ObservableMotionDriver:
    """Drives humanized cursor movement with visual halos and takeover safeguards."""

    SPEED_FACTOR_HUMAN = 1.2

    def __init__(
        self,
        trajectory_gen: Optional[BezierTrajectoryGenerator] = None,
        halo_emitter: Optional[VisualTargetHaloEmitter] = None,
        takeover_hook: Optional[HumanTakeoverHook] = None
    ) -> None:
        self._trajectory_gen = trajectory_gen or BezierTrajectoryGenerator()
        self._halo_emitter = halo_emitter or VisualTargetHaloEmitter()
        self._takeover_hook = takeover_hook or HumanTakeoverHook()

    def plan_and_drive_motion(
        self,
        start_pos: Tuple[int, int],
        target_pos: Tuple[int, int],
        target_name: str,
        bounding_box: Tuple[int, int, int, int],
        physical_cursor_pos: Optional[Tuple[int, int]] = None
    ) -> MotionExecutionResult:
        """Executes full observable motion sequence with 1.2x speed scaling and takeover guard."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Motion aborted.")

        # 1. Emit target halo overlay prior to motion (WKF-05.2)
        halo = self._halo_emitter.create_halo(
            target_name=target_name,
            bounding_box=bounding_box,
            action_type="CLICK",
            duration_ms=400,
            color_hex="#00FFCC"  # Vibrant CyberHUD green/cyan halo
        )
        self._broadcast_event("WORKFLOW_TARGET_HALO", halo.model_dump())

        # 2. Compute smooth cubic Bezier trajectory scaled to 1.2x human speed (WKF-05.1)
        base_trajectory = self._trajectory_gen.generate(start_pos, target_pos)
        scaled_duration = base_trajectory.duration_ms / self.SPEED_FACTOR_HUMAN

        scaled_trajectory = self._trajectory_gen.generate(
            start_pos=start_pos,
            target_pos=target_pos,
            duration_ms=scaled_duration,
            add_jitter=True
        )

        trajectory_id = f"traj_{os.urandom(4).hex()}"

        self._broadcast_event("WORKFLOW_MOTION_TRAJECTORY", {
            "trajectory_id": trajectory_id,
            "waypoints": [p.model_dump() for p in scaled_trajectory.points],
            "duration_ms": scaled_duration,
            "speed_factor": self.SPEED_FACTOR_HUMAN
        })

        # 3. Check low-level human takeover displacement hook (WKF-05.3, < 10ms SLA)
        takeover_triggered = False
        takeover_latency = 0.0

        if physical_cursor_pos is not None:
            t0 = time.perf_counter()
            self._takeover_hook.start_monitoring(start_pos)
            event = self._takeover_hook.check_takeover(physical_cursor_pos)
            takeover_latency = (time.perf_counter() - t0) * 1000.0

            if event is not None:
                takeover_triggered = True
                self._broadcast_event("WORKFLOW_HUMAN_TAKEOVER_TRIGGERED", {
                    "displacement_px": event.displacement_px,
                    "latency_ms": takeover_latency
                })

        return MotionExecutionResult(
            trajectory_id=trajectory_id,
            waypoint_count=len(scaled_trajectory.points),
            duration_ms=scaled_duration,
            target_halo=halo,
            human_takeover_triggered=takeover_triggered,
            takeover_latency_ms=takeover_latency if physical_cursor_pos else None,
            success=not takeover_triggered,
            speed_factor=self.SPEED_FACTOR_HUMAN
        )

    def _broadcast_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        try:
            main_mod = sys.modules.get("services.backend.main")
            broadcaster = getattr(main_mod, "broadcast_message", None)
            if broadcaster:
                msg = {
                    "id": f"mot-{os.urandom(2).hex()}",
                    "type": event_type,
                    "ts": str(time.time()),
                    "payload": payload
                }
                main_loop = getattr(main_mod, "main_loop", None)
                if main_loop and main_loop.is_running():
                    asyncio.run_coroutine_threadsafe(broadcaster(msg), main_loop)
        except Exception:
            pass


observable_motion_driver = ObservableMotionDriver()
