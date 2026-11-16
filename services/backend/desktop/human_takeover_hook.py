"""Low-Level Human Takeover Detection Hook (Milestone 49 Phase 3, GUI-03).

Detects manual operator mouse intervention (>15px delta) and immediately
relinquishes automation control within < 10.0ms SLA.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Callable, List, Optional, Tuple

from services.backend.schemas.semantic_focus import TakeoverEvent
from services.backend.safety.guardian import guardian


class HumanTakeoverHook:
    """Monitors cursor coordinates and aborts automation upon manual operator displacement."""

    DISPLACEMENT_THRESHOLD_PX = 15.0

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._is_active: bool = False
        self._last_automation_pos: Optional[Tuple[int, int]] = None
        self._callbacks: List[Callable[[TakeoverEvent], None]] = []

    def register_callback(self, cb: Callable[[TakeoverEvent], None]) -> None:
        with self._lock:
            if cb not in self._callbacks:
                self._callbacks.append(cb)

    def start_monitoring(self, current_pos: Tuple[int, int]) -> None:
        """Starts monitoring from the known automation cursor position."""
        with self._lock:
            self._is_active = True
            self._last_automation_pos = current_pos

    def update_automation_pos(self, new_pos: Tuple[int, int]) -> None:
        """Updates expected automation coordinates during synthetic cursor moves."""
        with self._lock:
            self._last_automation_pos = new_pos

    def check_takeover(self, physical_cursor_pos: Tuple[int, int]) -> Optional[TakeoverEvent]:
        """Checks if physical cursor diverged from automation position (>15px)."""
        t0 = time.perf_counter()

        with self._lock:
            if not self._is_active or self._last_automation_pos is None:
                return None

            ax, ay = self._last_automation_pos
            px, py = physical_cursor_pos
            displacement = math.hypot(px - ax, py - ay)

            if displacement > self.DISPLACEMENT_THRESHOLD_PX:
                # Human takeover triggered!
                self._is_active = False
                latency_ms = (time.perf_counter() - t0) * 1000.0
                event = TakeoverEvent(
                    event_id=f"takeover_{int(time.time() * 1000)}",
                    initial_position=(ax, ay),
                    detected_position=(px, py),
                    displacement_px=round(displacement, 2),
                    detection_latency_ms=round(latency_ms, 3),
                    timestamp=time.time(),
                )

                # Fire callbacks
                for cb in self._callbacks:
                    try:
                        cb(event)
                    except Exception:
                        pass

                return event

        return None

    def stop_monitoring(self) -> None:
        with self._lock:
            self._is_active = False
            self._last_automation_pos = None
