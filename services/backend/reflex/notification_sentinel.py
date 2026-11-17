"""Notification Reflex Sentinel for Windows Desktop Alerts (Milestone 51 Phase 1).

Monitors and normalizes incoming Windows system toasts, app alarms, and background
service notifications into standard ReflexEvent payloads.
"""

from __future__ import annotations

import collections
import time
from typing import Any, Deque, Dict, List, Optional
from services.backend.schemas.reflex_events import (
    ReflexEvent,
    ReflexEventType,
    ReflexSeverity,
    ToastNotificationDetails,
)


class NotificationReflexSentinel:
    """Captures, filters, and normalizes Windows desktop notifications."""

    def __init__(self, debounce_seconds: float = 3.0) -> None:
        self.debounce_seconds = debounce_seconds
        self._recent_events: Deque[ReflexEvent] = collections.deque(maxlen=100)
        self._seen_toasts: Dict[str, float] = {}

    def process_toast(
        self,
        app_name: str,
        title: str,
        message: str,
        urgency: str = "normal",
    ) -> Optional[ReflexEvent]:
        """Ingests and normalizes an incoming notification toast.
        
        Applies deduplication and severity classification.
        """
        now = time.time()
        dedup_key = f"{app_name}:{title}:{message}"

        # Check deduplication window
        last_seen = self._seen_toasts.get(dedup_key, 0.0)
        if (now - last_seen) < self.debounce_seconds:
            return None

        self._seen_toasts[dedup_key] = now

        # Determine severity and event type
        lower_msg = (title + " " + message).lower()
        if any(w in lower_msg for w in ("failed", "error", "exception", "crashed", "fatal")):
            severity = ReflexSeverity.CRITICAL
            event_type = ReflexEventType.ERROR_DIALOG
        elif any(w in lower_msg for w in ("warn", "warning", "caution", "alert", "low battery")):
            severity = ReflexSeverity.WARNING
            event_type = ReflexEventType.TOAST_NOTIFICATION
        elif any(w in lower_msg for w in ("succeeded", "complete", "finished", "ready")):
            severity = ReflexSeverity.SUCCESS
            event_type = ReflexEventType.TOAST_NOTIFICATION
        else:
            severity = ReflexSeverity.INFO
            event_type = ReflexEventType.TOAST_NOTIFICATION

        toast_details = ToastNotificationDetails(
            app_name=app_name,
            title=title,
            message=message,
            timestamp=now,
            urgency=urgency,
        )

        event = ReflexEvent(
            event_type=event_type,
            severity=severity,
            source="notification_sentinel",
            confidence=0.99,
            toast_details=toast_details,
            metadata={"urgency": urgency, "app": app_name},
        )

        self._recent_events.append(event)
        return event

    def get_recent_events(self, limit: int = 10) -> List[ReflexEvent]:
        """Returns the most recent notification reflex events."""
        return list(self._recent_events)[-limit:]
