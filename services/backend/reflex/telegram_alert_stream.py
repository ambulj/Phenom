"""Telegram Companion Alert Stream for Remote Reflex Notifications (Milestone 51 Phase 5).

Formats and broadcasts structured push alerts to the operator's Telegram channel
when long-running commands complete or critical build failures occur, enforcing
strict Rule 11 secret scrubbing.
"""

from __future__ import annotations

import collections
import time
from typing import Any, Deque, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.schemas.reflex_events import ReflexEvent, ReflexEventType, ReflexSeverity
from services.backend.reflex.contextual_anchor import ActiveContextAnchor
from services.backend.safety.clipboard_privacy_filter import ClipboardPrivacyFilter


class TelegramAlertPayload(BaseModel):
    """Formatted Telegram companion message payload."""
    alert_id: str
    chat_title: str = "Phenom Reflex Sentinel"
    text: str
    severity: ReflexSeverity
    event_type: ReflexEventType
    timestamp: float = Field(default_factory=time.time)
    inline_buttons: List[Dict[str, str]] = Field(default_factory=list)
    is_dispatched: bool = False


class TelegramReflexAlertStream:
    """Manages remote push notification streams for desktop reflex events."""

    def __init__(self, debounce_seconds: float = 5.0) -> None:
        self.debounce_seconds = debounce_seconds
        self._last_alert_time: Dict[str, float] = {}
        self._recent_alerts: Deque[TelegramAlertPayload] = collections.deque(maxlen=50)

    def format_alert(
        self,
        event: ReflexEvent,
        anchor: Optional[ActiveContextAnchor] = None
    ) -> Optional[TelegramAlertPayload]:
        """Formats a structured Telegram push notification with Rule 11 redaction.
        
        Returns None if debounced.
        """
        now = time.time()
        dedup_key = f"{event.event_type.value}:{event.severity.value}"
        last_time = self._last_alert_time.get(dedup_key, 0.0)

        if (now - last_time) < self.debounce_seconds:
            return None

        self._last_alert_time[dedup_key] = now

        # Determine Emoji and Header
        if event.is_failure or event.severity == ReflexSeverity.CRITICAL:
            header_emoji = "🚨"
            header_title = "CRITICAL REFLEX ALERT"
        elif event.is_success or event.severity == ReflexSeverity.SUCCESS:
            header_emoji = "✅"
            header_title = "EXECUTION COMPLETE"
        elif event.severity == ReflexSeverity.WARNING:
            header_emoji = "⚠️"
            header_title = "SYSTEM ALERT"
        else:
            header_emoji = "ℹ️"
            header_title = "REFLEX NOTICE"

        # Context details
        app_name = anchor.process_name if anchor else "System"
        workspace = anchor.project_name or "Phenom Workspace" if anchor else "Workspace"
        raw_detail = ""

        if event.visual_details:
            raw_detail = event.visual_details.raw_text
            app_name = event.visual_details.process_name or app_name
        elif event.toast_details:
            raw_detail = f"{event.toast_details.title}: {event.toast_details.message}"
            app_name = event.toast_details.app_name or app_name

        # Scrub secrets and credentials (Rule 11)
        sanitized_detail = ClipboardPrivacyFilter.sanitize(raw_detail).sanitized_text[:250]

        # Markdown body
        lines = [
            f"{header_emoji} *{header_title}*",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"• *Event:* `{event.event_type.value}`",
            f"• *App:* `{app_name}` | *Project:* `{workspace}`",
            f"• *Severity:* `{event.severity.value}`",
        ]

        if sanitized_detail:
            lines.append(f"\n```text\n{sanitized_detail}\n```")

        lines.append("\n_Suggested actions:_ `/status` • `/guardian_halt`")

        msg_text = "\n".join(lines)

        alert = TelegramAlertPayload(
            alert_id=f"tg_{event.event_id}",
            text=msg_text,
            severity=event.severity,
            event_type=event.event_type,
            timestamp=now,
            inline_buttons=[
                {"text": "Acknowledge", "callback_data": f"/ack_{event.event_id}"},
                {"text": "Guardian Halt", "callback_data": "/guardian_halt"},
            ],
            is_dispatched=True,
        )

        self._recent_alerts.append(alert)
        return alert

    def get_recent_alerts(self, limit: int = 10) -> List[TelegramAlertPayload]:
        """Returns recently formatted Telegram alerts."""
        return list(self._recent_alerts)[-limit:]
