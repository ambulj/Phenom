"""Execution Telemetry Bus for Phenom (Milestone 29 Phase 4).

Captures, buffers, and distributes background tool execution events, latencies,
and status telemetry with strict Rule 11 credential scrubbing and Rule 8 defense (HUD-01.1, MON-04.1).
"""

from __future__ import annotations

from collections import deque
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.telemetry.bus")


class Rule8ViolationError(Exception):
    """Raised when telemetry payloads involve payment or checkout operations."""
    pass


class TelemetryEvent(BaseModel):
    event_id: str
    tool_name: str
    status: str = "COMPLETED"  # "STARTED", "COMPLETED", "FAILED", "CANCELLED"
    duration_ms: float = 0.0
    tier: int = 0
    timestamp: float = Field(default_factory=time.time)
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result_summary: Optional[str] = None


class TelemetryBusStats(BaseModel):
    total_events: int
    completed_events: int
    failed_events: int
    average_duration_ms: float
    tool_counts: Dict[str, int] = Field(default_factory=dict)


class ExecutionTelemetryBus:
    """In-memory circular event buffer for background tool execution telemetry."""

    _RULE_8_PATTERN = re.compile(
        r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
        re.IGNORECASE,
    )

    _SENSITIVE_KEY_PATTERN = re.compile(
        r"(password|token|secret|api.?key|auth|credential|private.?key)",
        re.IGNORECASE,
    )

    def __init__(self, max_events: int = 200) -> None:
        self._max_events = max_events
        self._events: deque[TelemetryEvent] = deque(maxlen=max_events)

    def check_safety(self, text: str) -> None:
        """Enforces Guardian kill switch and Rule 8 payment defenses."""
        if guardian.is_halted:
            raise RuntimeError("Execution halted by Guardian kill switch (TELEMETRY_BUS_HALTED)")

        if self._RULE_8_PATTERN.search(text):
            raise Rule8ViolationError(
                "Rule 8 Violation: Payment, checkout, or billing directives detected in telemetry event"
            )

    def scrub_credentials(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Scrubs sensitive credential tokens per Rule 11."""
        scrubbed: Dict[str, Any] = {}
        for k, v in data.items():
            if self._SENSITIVE_KEY_PATTERN.search(k):
                scrubbed[k] = "[REDACTED]"
            elif isinstance(v, dict):
                scrubbed[k] = self.scrub_credentials(v)
            elif isinstance(v, str) and ("bearer " in v.lower() or "ghp_" in v.lower()):
                scrubbed[k] = "[REDACTED]"
            else:
                scrubbed[k] = v
        return scrubbed

    def record_event(
        self,
        tool_name: str,
        status: str = "COMPLETED",
        duration_ms: float = 0.0,
        tier: int = 0,
        args: Optional[Dict[str, Any]] = None,
        result_summary: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> TelemetryEvent:
        """Records a new execution telemetry event into the circular ring buffer."""
        check_str = f"{tool_name} {status} {args or ''} {result_summary or ''}"
        self.check_safety(check_str)

        scrubbed_args = self.scrub_credentials(args or {})
        eid = event_id or f"evt-{int(time.time() * 1000) % 100000}-{os.urandom(2).hex()}"

        event = TelemetryEvent(
            event_id=eid,
            tool_name=tool_name,
            status=status.upper(),
            duration_ms=max(0.0, round(duration_ms, 3)),
            tier=tier,
            timestamp=time.time(),
            arguments=scrubbed_args,
            result_summary=result_summary,
        )

        self._events.append(event)
        logger.debug("Recorded telemetry event [%s] for %s (%s, %.2fms)", eid, tool_name, status, duration_ms)
        return event

    def query_history(
        self,
        tool_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[TelemetryEvent]:
        """Queries recorded telemetry events with optional tool filtering."""
        self.check_safety(f"query {tool_name or ''}")

        # Reverse deque to get latest first
        events_list = list(reversed(self._events))
        if tool_name:
            t_lower = tool_name.lower()
            events_list = [e for e in events_list if e.tool_name.lower() == t_lower]

        return events_list[:limit]

    def get_stats(self) -> TelemetryBusStats:
        """Calculates cumulative telemetry statistics across buffered events."""
        self.check_safety("stats")

        total = len(self._events)
        if total == 0:
            return TelemetryBusStats(
                total_events=0,
                completed_events=0,
                failed_events=0,
                average_duration_ms=0.0,
                tool_counts={},
            )

        completed = sum(1 for e in self._events if e.status == "COMPLETED")
        failed = sum(1 for e in self._events if e.status == "FAILED")
        avg_dur = sum(e.duration_ms for e in self._events) / total

        tool_counts: Dict[str, int] = {}
        for e in self._events:
            tool_counts[e.tool_name] = tool_counts.get(e.tool_name, 0) + 1

        return TelemetryBusStats(
            total_events=total,
            completed_events=completed,
            failed_events=failed,
            average_duration_ms=round(avg_dur, 2),
            tool_counts=tool_counts,
        )

    def clear(self) -> None:
        """Clears all buffered telemetry events."""
        self._events.clear()


# Global singleton instance
execution_telemetry_bus = ExecutionTelemetryBus()
