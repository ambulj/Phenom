"""Phenom Proactive Intelligence & Ambient Sensing Tools.

Provides safety tool endpoints for inspecting idle and context sensors,
configuring anti-fatigue cooldowns, and managing active proactive cards.
Strictly respects SAFETY.md:
- get_proactive_status (Tier 0): Read-only status query.
- configure_proactive_cooldown (Tier 1): Requires interactive preview confirmation.
- dismiss_proactive_card (Tier 0): Safe dismissal of proactive notification card.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.sensors.idle_sensor import idle_detector
from services.backend.sensors.context_sensor import context_sensor
from services.backend.proactive.dispatcher import proactive_dispatcher, ProactivePriority


class GetProactiveStatusArgs(BaseModel):
    """Schema for get_proactive_status query (no arguments required)."""
    pass


class ConfigureProactiveCooldownArgs(BaseModel):
    idle_threshold_seconds: Optional[float] = Field(
        default=None,
        ge=10.0,
        le=86400.0,
        description="Duration of user inactivity before emitting USER_IDLE event (in seconds, min 10.0)",
    )
    default_cooldown_seconds: Optional[float] = Field(
        default=None,
        ge=60.0,
        le=86400.0,
        description="Default anti-fatigue cooldown period between proactive notifications (in seconds, min 60.0)",
    )
    event_type: Optional[str] = Field(
        default=None,
        description="Specific event category to configure cooldown for (e.g. 'MEETING_PREP', 'MORNING_BRIEF')",
    )
    event_cooldown_seconds: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=86400.0,
        description="Cooldown duration for the specified event_type (in seconds)",
    )


class DismissProactiveCardArgs(BaseModel):
    card_id: str = Field(..., description="ID of the proactive recommendation card to dismiss")


@registry.register(
    name="get_proactive_status",
    tier=0,
    description="Returns real-time status of Win32 idle detector, active window context sensor, and active proactive recommendation cards. Read-only.",
    args_schema=GetProactiveStatusArgs,
    preview_fn=lambda a: "Inspect ambient sensing and proactive dispatcher status (Read-only)",
)
def get_proactive_status(**kwargs) -> Dict[str, Any]:
    idle_dur = idle_detector.get_current_idle_seconds()
    ctx = context_sensor.query_context(redact_sensitive=True)
    active_cards = proactive_dispatcher.list_active_cards(limit=10)

    return {
        "status": "ok",
        "idle_sensor": {
            "is_idle": idle_detector.is_idle,
            "idle_duration_seconds": round(idle_dur, 2),
            "threshold_seconds": idle_detector.idle_threshold_seconds,
        },
        "context_sensor": {
            "title": ctx.title,
            "app_name": ctx.app_name,
            "is_sensitive": ctx.is_sensitive,
        },
        "dispatcher": {
            "current_mode": proactive_dispatcher.current_mode,
            "default_cooldown_seconds": proactive_dispatcher.default_cooldown_seconds,
            "active_card_count": len(active_cards),
            "active_cards": [c.model_dump() for c in active_cards],
        },
    }


@registry.register(
    name="configure_proactive_cooldown",
    tier=1,
    description="Configures user idle inactivity threshold and anti-fatigue cooldowns for proactive notifications. Requires confirmation.",
    args_schema=ConfigureProactiveCooldownArgs,
    preview_fn=lambda a: f"Configure proactive parameters: idle_threshold={a.get('idle_threshold_seconds')}, cooldown={a.get('default_cooldown_seconds')}, event={a.get('event_type')}:{a.get('event_cooldown_seconds')}",
)
def configure_proactive_cooldown(
    idle_threshold_seconds: Optional[float] = None,
    default_cooldown_seconds: Optional[float] = None,
    event_type: Optional[str] = None,
    event_cooldown_seconds: Optional[float] = None,
    **kwargs
) -> Dict[str, Any]:
    if idle_threshold_seconds is not None:
        idle_detector.set_threshold(idle_threshold_seconds)

    if default_cooldown_seconds is not None:
        proactive_dispatcher.default_cooldown_seconds = default_cooldown_seconds

    if event_type and event_cooldown_seconds is not None:
        proactive_dispatcher.set_cooldown_override(event_type.upper().strip(), event_cooldown_seconds)

    return {
        "status": "configured",
        "idle_threshold_seconds": idle_detector.idle_threshold_seconds,
        "default_cooldown_seconds": proactive_dispatcher.default_cooldown_seconds,
        "cooldown_for_event": proactive_dispatcher.get_cooldown_for_event(event_type) if event_type else None,
    }


@registry.register(
    name="dismiss_proactive_card",
    tier=0,
    description="Dismisses an active proactive recommendation card from the Cyber HUD tray. Read-only/Safe.",
    args_schema=DismissProactiveCardArgs,
    preview_fn=lambda a: f"Dismiss proactive card ID: {a.get('card_id')}",
)
def dismiss_proactive_card(card_id: str, **kwargs) -> Dict[str, Any]:
    success = proactive_dispatcher.dismiss_card(card_id)
    return {
        "status": "dismissed" if success else "not_found",
        "card_id": card_id,
        "success": success,
    }
