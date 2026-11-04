"""
Proactive Sensory Event Bus (PRX-01, SAF-01, SAF-02).
Ingests Win32 desktop context hooks, passes payloads through real-time PrivacyScrubber,
and routes sanitized events to autonomous subscribers and HUD telemetry.
"""

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from services.backend.proactive.privacy_scrubber import PrivacyScrubber, privacy_scrubber
from services.backend.schemas.proactive_bus import (
    ProactiveBusStatus,
    Win32EventPayload,
    Win32EventType,
)

logger = logging.getLogger(__name__)


class ProactiveEventBus:
    """Central event fabric coordinating proactive system context hooks and scrubbed event dispatch."""

    def __init__(self, scrubber: Optional[PrivacyScrubber] = None) -> None:
        self._scrubber = scrubber or privacy_scrubber
        self._type_subscribers: Dict[Win32EventType, List[Callable[[Win32EventPayload], None]]] = {
            t: [] for t in Win32EventType
        }
        self._global_subscribers: List[Callable[[Win32EventPayload], None]] = []
        self._recent_events: List[Win32EventPayload] = []
        self._max_buffer: int = 200
        self._total_ingested: int = 0
        self._total_scrubbed: int = 0
        self._halted: bool = False
        self._broadcaster: Optional[Callable[[dict], None]] = None

    def register_broadcaster(self, broadcaster: Callable[[dict], None]) -> None:
        """Register WebSocket notification callback."""
        self._broadcaster = broadcaster

    def halt(self) -> None:
        """Immediate synchronous halt for Guardian kill switch (< 10ms SLA)."""
        self._halted = True
        logger.info("[EventBus] ProactiveEventBus halted synchronously by Guardian.")

    def reset(self) -> None:
        """Reset after Guardian disengagement."""
        self._halted = False

    def is_halted(self) -> bool:
        return self._halted

    def subscribe(
        self,
        callback: Callable[[Win32EventPayload], None],
        event_type: Optional[Win32EventType] = None,
    ) -> None:
        """Subscribe a handler callback to a specific event type or all events."""
        if event_type is not None:
            if callback not in self._type_subscribers[event_type]:
                self._type_subscribers[event_type].append(callback)
        else:
            if callback not in self._global_subscribers:
                self._global_subscribers.append(callback)

    def unsubscribe(
        self,
        callback: Callable[[Win32EventPayload], None],
        event_type: Optional[Win32EventType] = None,
    ) -> None:
        """Remove a previously subscribed callback."""
        if event_type is not None:
            if callback in self._type_subscribers[event_type]:
                self._type_subscribers[event_type].remove(callback)
        else:
            if callback in self._global_subscribers:
                self._global_subscribers.remove(callback)

    def ingest_event(
        self,
        event_type: Win32EventType | str,
        process_name: str = "system",
        pid: int = 0,
        window_title: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> Win32EventPayload:
        """
        Ingest, sanitize via PrivacyScrubber, buffer, and dispatch a Win32 system event.
        Raises PermissionError if Guardian is halted.
        """
        if self._halted:
            raise PermissionError("Guardian kill switch active: Event bus ingestion halted.")

        # Coerce event_type enum
        if isinstance(event_type, str):
            try:
                ev_type = Win32EventType(event_type)
            except ValueError:
                ev_type = Win32EventType.SYSTEM_ALERT
        else:
            ev_type = event_type

        # 1. Real-time Privacy Scrubbing (Permanent Rule 11)
        scrubbed_fields: List[str] = []
        clean_title, title_cats = self._scrubber.scrub_text(window_title)
        if title_cats:
            scrubbed_fields.append("window_title")

        raw_details = details or {}
        clean_details, detail_cats = self._scrubber.scrub_dict(raw_details)
        if detail_cats:
            scrubbed_fields.append("details")

        is_scrubbed = len(scrubbed_fields) > 0
        if is_scrubbed:
            self._total_scrubbed += 1

        event_id = f"ev_{uuid.uuid4().hex[:10]}"
        payload = Win32EventPayload(
            event_id=event_id,
            event_type=ev_type,
            process_name=process_name.strip(),
            pid=pid,
            window_title=clean_title,
            details=clean_details,
            timestamp=time.time(),
            is_scrubbed=is_scrubbed,
            scrubbed_fields=scrubbed_fields,
        )

        # 2. Buffer management
        self._recent_events.append(payload)
        if len(self._recent_events) > self._max_buffer:
            self._recent_events.pop(0)

        self._total_ingested += 1

        # 3. Subscriber dispatch (safe exception handling)
        for cb in self._type_subscribers[ev_type]:
            try:
                cb(payload)
            except Exception as e:
                logger.debug(f"[EventBus] Subscriber error for {ev_type}: {e}")

        for gcb in self._global_subscribers:
            try:
                gcb(payload)
            except Exception as e:
                logger.debug(f"[EventBus] Global subscriber error: {e}")

        # 4. WebSocket notification
        if self._broadcaster:
            try:
                self._broadcaster({
                    "type": "proactive_bus_event",
                    "payload": payload.model_dump(),
                })
            except Exception as e:
                logger.debug(f"[EventBus] Broadcast error: {e}")

        return payload

    def get_status(self) -> ProactiveBusStatus:
        """Retrieve current telemetry, subscriber count, and recent events."""
        active_subs = len(self._global_subscribers) + sum(len(cbs) for cbs in self._type_subscribers.values())
        return ProactiveBusStatus(
            is_running=not self._halted,
            is_halted=self._halted,
            total_events_ingested=self._total_ingested,
            total_events_scrubbed=self._total_scrubbed,
            active_subscriptions=active_subs,
            recent_events=list(self._recent_events[-15:]),  # Return last 15
            active_webrtc_sessions=0,
        )


# Global singleton instance
proactive_event_bus = ProactiveEventBus()
