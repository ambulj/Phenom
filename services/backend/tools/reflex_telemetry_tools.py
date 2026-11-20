"""
Phenom Reflex Telemetry & Telegram Companion Alert Tools (Milestone 51 Phase 5).

Registers:
- broadcast_reflex_telemetry (Tier 0)
- dispatch_telegram_reflex_alert (Tier 0)
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.reflex import (
    visual_sentinel,
    contextual_anchor_manager,
    action_suggester,
    telegram_alert_stream,
    reflex_engine,
)
from services.backend.schemas.reflex_events import ReflexEvent, ReflexEventType, ReflexSeverity, VisualCueDetails


class BroadcastReflexTelemetryArgs(BaseModel):
    include_proposals: bool = Field(default=True, description="Whether to include suggested action proposals")


class DispatchTelegramReflexAlertArgs(BaseModel):
    event_type: str = Field(description="ReflexEventType to broadcast (e.g. TERMINAL_COMPLETED, BUILD_FAILED)")
    severity: Optional[str] = Field(default="INFO", description="Severity: INFO, SUCCESS, WARNING, CRITICAL")
    raw_text: Optional[str] = Field(default="", description="Snippet or diagnostic message")
    process_name: Optional[str] = Field(default="", description="Process executable name")


@registry.register(
    name="broadcast_reflex_telemetry",
    tier=0,
    description="Gathers active context anchor, recent reflex blips, and proposals for CyberHUD Reflex Radar.",
    args_schema=BroadcastReflexTelemetryArgs,
    preview_fn=lambda a: "Broadcast active reflex radar telemetry to CyberHUD"
)
def broadcast_reflex_telemetry(include_proposals: bool = True) -> Dict[str, Any]:
    anchor = contextual_anchor_manager.resolve_anchor()
    sentinel_status = visual_sentinel.get_status()

    recent_reactions = reflex_engine.get_recent_reactions(limit=5)
    latest_reaction = recent_reactions[-1] if recent_reactions else None

    proposals = []
    if include_proposals:
        latest_event = sentinel_status.recent_events[-1] if sentinel_status.recent_events else None
        props = action_suggester.generate_proposals(anchor=anchor, event=latest_event)
        proposals = [p.model_dump() for p in props]

    telemetry_payload = {
        "active_app": anchor.process_name or "Desktop",
        "active_file": anchor.active_file,
        "project_name": anchor.project_name or "Phenom",
        "app_category": anchor.app_category.value,
        "sample_rate_hz": sentinel_status.active_sample_rate_hz,
        "cpu_percent": sentinel_status.cpu_percent_estimate,
        "voice_commentary": latest_reaction.voice_commentary if latest_reaction else None,
        "word_count": latest_reaction.word_count if latest_reaction else 0,
        "recent_events": [e.model_dump() for e in sentinel_status.recent_events],
        "proposals": proposals,
    }

    return telemetry_payload


@registry.register(
    name="dispatch_telegram_reflex_alert",
    tier=0,
    description="Formats and queues a Telegram push alert for background completions or build failures.",
    args_schema=DispatchTelegramReflexAlertArgs,
    preview_fn=lambda a: f"Format and send Telegram reflex alert for '{a.get('event_type')}'"
)
def dispatch_telegram_reflex_alert(
    event_type: str,
    severity: Optional[str] = "INFO",
    raw_text: Optional[str] = "",
    process_name: Optional[str] = ""
) -> Dict[str, Any]:
    try:
        ev_type = ReflexEventType(event_type)
    except ValueError:
        ev_type = ReflexEventType.UNKNOWN

    try:
        ev_sev = ReflexSeverity(severity or "INFO")
    except ValueError:
        ev_sev = ReflexSeverity.INFO

    event = ReflexEvent(
        event_type=ev_type,
        severity=ev_sev,
        source="telegram_dispatcher",
        visual_details=VisualCueDetails(
            process_name=process_name or "",
            raw_text=raw_text or "",
        ),
    )

    anchor = contextual_anchor_manager.resolve_anchor()
    alert = telegram_alert_stream.format_alert(event, anchor=anchor)

    return {
        "success": alert is not None,
        "alert": alert.model_dump() if alert else None,
        "reason": "Debounced" if alert is None else None,
    }
