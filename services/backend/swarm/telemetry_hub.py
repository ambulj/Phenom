"""Swarm Telemetry WebSocket Hub for Phenom.

Phase 48-05: TELE-02.
Broadcasts granular multi-agent swarm state transitions, auction updates,
consensus quorum decisions, and GPU VRAM telemetry to frontend and companion clients.
"""

from __future__ import annotations

from collections import deque
import logging
import time
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger("phenom.swarm.telemetry_hub")


class SwarmTelemetryHub:
    """Central event broadcaster and history buffer for multi-agent swarm telemetry."""

    def __init__(self, max_history: int = 100) -> None:
        self.max_history = max_history
        self._history: Deque[Dict[str, Any]] = deque(maxlen=max_history)
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a subscriber callback for real-time telemetry events."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """Remove a subscriber callback."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            return True
        return False

    def broadcast_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source: str = "swarm",
    ) -> Dict[str, Any]:
        """Record and broadcast a structured telemetry event to all subscribers."""
        event = {
            "event_type": event_type,
            "source": source,
            "payload": payload,
            "timestamp": time.time(),
        }
        self._history.append(event)

        for sub in list(self._subscribers):
            try:
                sub(event)
            except Exception as exc:
                logger.warning("Error invoking subscriber callback: %s", exc)

        logger.debug("Broadcasted swarm event: %s", event_type)
        return event

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return a slice of the most recent telemetry events."""
        events = list(self._history)
        return events[-limit:] if limit > 0 else events

    def clear(self) -> None:
        """Reset telemetry history."""
        self._history.clear()


# Global singleton hub
swarm_telemetry_hub = SwarmTelemetryHub()
