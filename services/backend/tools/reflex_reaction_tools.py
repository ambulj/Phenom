"""
Phenom Reflex Reaction & Jarvis Commentary Tools (Milestone 51 Phase 2).

Registers:
- evaluate_reflex_reaction (Tier 0)
- dispatch_jarvis_commentary (Tier 0)
- configure_reflex_cooldowns (Tier 1)
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.reflex import reflex_engine, jarvis_commentator
from services.backend.schemas.reflex_events import (
    ReflexEvent,
    ReflexEventType,
    ReflexSeverity,
    VisualCueDetails,
    ToastNotificationDetails,
)


class EvaluateReflexReactionArgs(BaseModel):
    event_type: str = Field(description="ReflexEventType name")
    severity: Optional[str] = Field(default="INFO", description="Severity: INFO, SUCCESS, WARNING, CRITICAL")
    raw_text: Optional[str] = Field(default="", description="Snippet or diagnostic message")
    process_name: Optional[str] = Field(default="", description="Source process name")
    app_name: Optional[str] = Field(default="", description="Toast originating application")


class DispatchJarvisCommentaryArgs(BaseModel):
    event_type: str = Field(description="Event category to comment on")
    diagnostic: Optional[str] = Field(default="", description="Specific error diagnostic or message")
    severity: Optional[str] = Field(default="INFO", description="Event severity")


class ConfigureReflexCooldownsArgs(BaseModel):
    rule_id: str = Field(description="Target reflex rule ID (e.g. rule_build_failed)")
    cooldown_seconds: float = Field(default=10.0, ge=0.0, le=300.0, description="New cooldown in seconds")


@registry.register(
    name="evaluate_reflex_reaction",
    tier=0,
    description="Matches a reflex event against rules in <100ms and returns commentary and suggested action.",
    args_schema=EvaluateReflexReactionArgs,
    preview_fn=lambda a: f"Evaluate reflex reaction for '{a.get('event_type')}' ({a.get('severity')})"
)
def evaluate_reflex_reaction(
    event_type: str,
    severity: Optional[str] = "INFO",
    raw_text: Optional[str] = "",
    process_name: Optional[str] = "",
    app_name: Optional[str] = ""
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
        source="reaction_evaluator",
        visual_details=VisualCueDetails(
            process_name=process_name or "",
            raw_text=raw_text or "",
        ) if (raw_text or process_name) else None,
        toast_details=ToastNotificationDetails(
            app_name=app_name or "System",
            title=event_type,
            message=raw_text or "",
        ) if app_name else None,
    )

    reaction, elapsed_ms = reflex_engine.evaluate_event(event)

    return {
        "matched": reaction is not None,
        "evaluation_latency_ms": round(elapsed_ms, 3),
        "reaction": reaction.model_dump() if reaction else None,
    }


@registry.register(
    name="dispatch_jarvis_commentary",
    tier=0,
    description="Synthesizes witty, concise Jarvis spoken debrief strictly constrained to <= 20 words.",
    args_schema=DispatchJarvisCommentaryArgs,
    preview_fn=lambda a: f"Synthesize spoken Jarvis commentary for '{a.get('event_type')}'"
)
def dispatch_jarvis_commentary(
    event_type: str,
    diagnostic: Optional[str] = "",
    severity: Optional[str] = "INFO"
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
        visual_details=VisualCueDetails(raw_text=diagnostic or "") if diagnostic else None,
    )

    text, word_count = jarvis_commentator.format_commentary(event)

    return {
        "voice_commentary": text,
        "word_count": word_count,
        "valid_limit": word_count <= 20,
    }


@registry.register(
    name="configure_reflex_cooldowns",
    tier=1,
    description="Updates debounce and cooldown threshold for a specific reflex rule.",
    args_schema=ConfigureReflexCooldownsArgs,
    preview_fn=lambda a: f"Set cooldown for reflex rule '{a.get('rule_id')}' to {a.get('cooldown_seconds')}s"
)
def configure_reflex_cooldowns(rule_id: str, cooldown_seconds: float) -> Dict[str, Any]:
    success = reflex_engine.set_rule_cooldown(rule_id, cooldown_seconds)
    return {
        "success": success,
        "rule_id": rule_id,
        "new_cooldown_seconds": cooldown_seconds,
    }
