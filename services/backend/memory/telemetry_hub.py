"""Real-Time Telemetry Hub for Knowledge Matrix & Desktop Choreography (Milestone 49 Phase 5, TELE-02).

Broadcasts real-time events across desktop choreography, active semantic window focus,
and episodic memory recall ripples to CyberHUD and UI clients.
"""

from __future__ import annotations

import collections
import logging
import threading
import time
from typing import Any, Callable, Deque, Dict, List, Optional

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.memory.telemetry_hub")


class MemoryTelemetryHub:
    """Manages live telemetry broadcasting and rolling event buffer for CyberHUD."""

    def __init__(self, buffer_size: int = 100) -> None:
        self._lock = threading.RLock()
        self._buffer: Deque[Dict[str, Any]] = collections.deque(maxlen=buffer_size)
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def _assert_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Telemetry broadcast aborted.")

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def broadcast(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source: str = "backend",
    ) -> Dict[str, Any]:
        """Broadcasts a telemetry event to all subscribers and records it in the ring buffer."""
        self._assert_guardian()

        event = {
            "event_id": f"evt_{int(time.time() * 1000)}_{len(self._buffer)}",
            "event_type": event_type,
            "source": source,
            "payload": payload,
            "timestamp": time.time(),
        }

        with self._lock:
            self._buffer.append(event)
            subs = list(self._subscribers)

        for sub in subs:
            try:
                sub(event)
            except Exception as e:
                logger.warning(f"Error notifying telemetry subscriber: {e}")

        return event

    def get_recent_events(self, limit: int = 50, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        self._assert_guardian()
        with self._lock:
            events = list(self._buffer)
            if event_type:
                events = [e for e in events if e["event_type"] == event_type]
            return events[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


# Global shared instance
memory_telemetry_hub = MemoryTelemetryHub()
