"""Choreography & Memory Telemetry Tools Registration for Phenom (Milestone 49 Phase 5, TELE-02, TELE-03).

Exposes:
1. `broadcast_choreography_telemetry` (Tier 0) - Broadcasts real-time events to CyberHUD and UI channels.
2. `generate_telegram_episodic_card` (Tier 0) - Formats rich proactive Telegram episodic companion cards.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.memory.telemetry_hub import memory_telemetry_hub
from services.backend.remote.telegram_episodic_card import telegram_episodic_card


# ============================================================================
# 1. broadcast_choreography_telemetry (Tier 0)
# ============================================================================

class BroadcastChoreographyTelemetryArgs(BaseModel):
    event_type: str = Field(..., description="CHOREOGRAPHY_STEP, FOCUS_CHANGED, MEMORY_ACTIVATION, or TAKEOVER_TRIGGERED")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event telemetry payload")


def broadcast_choreography_telemetry_preview(args: Dict[str, Any]) -> str:
    evt = args.get("event_type", "EVENT")
    return f"Broadcast '{evt}' telemetry to CyberHUD and WebSocket subscribers."


@registry.register(
    name="broadcast_choreography_telemetry",
    tier=0,
    description="Streams real-time desktop choreography, window focus, and memory recall events to CyberHUD.",
    args_schema=BroadcastChoreographyTelemetryArgs,
    preview_fn=broadcast_choreography_telemetry_preview,
    can_remember_per_folder=False,
)
def handle_broadcast_choreography_telemetry(
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    event = memory_telemetry_hub.broadcast(event_type=event_type, payload=payload or {})
    return {
        "status": "success",
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "timestamp": event["timestamp"],
    }


# ============================================================================
# 2. generate_telegram_episodic_card (Tier 0)
# ============================================================================

class GenerateTelegramEpisodicCardArgs(BaseModel):
    episode_title: str = Field(..., description="Milestone episode title")
    summary: str = Field(default="", description="Narrative summary")
    active_entities: List[str] = Field(default_factory=list, description="Top connected entity labels")
    recent_heuristics: List[str] = Field(default_factory=list, description="Recently learned heuristics")
    active_window: Optional[str] = Field(default=None, description="Active target desktop window title")


def generate_telegram_episodic_card_preview(args: Dict[str, Any]) -> str:
    title = args.get("episode_title", "Milestone")
    return f"Generate proactive Telegram episodic status card for '{title}'."


@registry.register(
    name="generate_telegram_episodic_card",
    tier=0,
    description="Formats a rich Telegram status card featuring ASCII topology, active focus, and review buttons.",
    args_schema=GenerateTelegramEpisodicCardArgs,
    preview_fn=generate_telegram_episodic_card_preview,
    can_remember_per_folder=False,
)
def handle_generate_telegram_episodic_card(
    episode_title: str,
    summary: str = "",
    active_entities: Optional[List[str]] = None,
    recent_heuristics: Optional[List[str]] = None,
    active_window: Optional[str] = None,
) -> Dict[str, Any]:
    card = telegram_episodic_card.format_card(
        episode_title=episode_title,
        summary=summary,
        active_entities=active_entities or [],
        recent_heuristics=recent_heuristics or [],
        active_window=active_window,
    )
    return {
        "status": "success",
        "card": card,
    }
