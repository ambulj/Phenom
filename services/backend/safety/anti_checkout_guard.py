"""
Phenom Anti-Checkout Guard & Tamper-Evident Audit Logger (WKF-03.2, WKF-03.3)
Wraps macro execution steps in pre-action visual safety barriers,
enforces sub-25ms emergency halt, and logs tamper-evident audit events
to encrypted SQLite database.
"""

from __future__ import annotations

import os
import sys
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.visual_shield import (
    ActiveVisualSafetyShield,
    VisualScanResult,
    VisualSafetyBarrierError,
    visual_safety_shield,
)
from services.backend.safety.action_log import action_log
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.safety.anti_checkout_guard")


class BarrierTripRecord(BaseModel):
    """Tamper-evident audit record of a tripped visual safety barrier."""
    audit_id: str
    timestamp: float
    window_title: str
    category: str
    trigger_term: str
    snippet: Optional[str] = None
    guardian_halted: bool = True


class AntiCheckoutGuard:
    """Active runtime guard enforcing visual barriers and audit logging."""

    def __init__(self, shield: Optional[ActiveVisualSafetyShield] = None) -> None:
        self._shield = shield or visual_safety_shield
        self._barrier_trips: List[BarrierTripRecord] = []

    def inspect_and_guard(
        self,
        surface_text: str,
        window_title: str = "",
        step_id: Optional[str] = None
    ) -> VisualScanResult:
        """Inspects surface text; halts immediately and writes audit log on violation."""
        scan = self._shield.scan_frame(surface_text, window_title, halt_on_violation=True)

        if not scan.safe:
            self._record_and_broadcast_trip(scan, window_title, step_id)
            raise VisualSafetyBarrierError(
                scan.category,
                scan.trigger_term,
                f"Visual Safety Barrier Tripped on '{scan.trigger_term}' in window '{window_title}'"
            )

        return scan

    def _record_and_broadcast_trip(
        self,
        scan: VisualScanResult,
        window_title: str,
        step_id: Optional[str]
    ) -> BarrierTripRecord:
        """Persists audit event to encrypted SQLite log and broadcasts alert."""
        audit_id = f"trip_{os.urandom(4).hex()}"
        record = BarrierTripRecord(
            audit_id=audit_id,
            timestamp=time.time(),
            window_title=window_title,
            category=scan.category.value if scan.category else "UNKNOWN",
            trigger_term=scan.trigger_term or "unknown",
            snippet=scan.matched_text_snippet,
            guardian_halted=guardian.is_halted
        )
        self._barrier_trips.append(record)

        # 1. Log to encrypted Action Log with tamper-evident metadata
        try:
            action_log.log(
                tool_name="visual_safety_barrier_trip",
                arguments={
                    "audit_id": audit_id,
                    "category": record.category,
                    "trigger_term": record.trigger_term,
                    "window_title": window_title,
                    "step_id": step_id,
                    "snippet": record.snippet,
                },
                result="EMERGENCY_HALT_TRIGGERED",
                tier=3,
                duration_ms=scan.scan_latency_ms
            )
        except Exception as e:
            logger.error(f"Failed to log barrier trip to encrypted action log: {e}")

        # 2. Broadcast WebSocket event to CyberHUD and mobile clients
        self._broadcast_event("WORKFLOW_SAFETY_BARRIER_TRIPPED", record.model_dump())
        return record

    def get_trip_history(self) -> List[Dict[str, Any]]:
        """Returns the in-memory log of barrier trips."""
        return [r.model_dump() for r in self._barrier_trips]

    def _broadcast_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        try:
            main_mod = sys.modules.get("services.backend.main")
            broadcaster = getattr(main_mod, "broadcast_message", None)
            if broadcaster:
                msg = {
                    "id": f"bar-{os.urandom(2).hex()}",
                    "type": event_type,
                    "ts": str(time.time()),
                    "payload": payload
                }
                main_loop = getattr(main_mod, "main_loop", None)
                if main_loop and main_loop.is_running():
                    asyncio.run_coroutine_threadsafe(broadcaster(msg), main_loop)
        except Exception:
            pass


anti_checkout_guard = AntiCheckoutGuard()
