"""Swarm Telemetry Tools Registration (Phase 48-05, TELE-02, TELE-03).

Registers swarm telemetry broadcast and dynamic Telegram status card generation
into Phenom's Safety ToolRegistry.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.remote.telegram_swarm_card import TelegramSwarmCard
from services.backend.swarm.telemetry_hub import swarm_telemetry_hub


# ============================================================================
# 1. broadcast_swarm_telemetry (Tier 0 - Read Only)
# ============================================================================

class BroadcastSwarmTelemetryArgs(BaseModel):
    event_type: str = Field(..., description="Type of event: auction_update, consensus_update, vram_telemetry, etc.")
    payload: Dict[str, Any] = Field(..., description="Event payload dictionary")


def broadcast_swarm_telemetry_preview(args: Dict[str, Any]) -> str:
    etype = args.get("event_type", "event")
    return f"Broadcast swarm telemetry event '{etype}' to WebSocket hub."


@registry.register(
    name="broadcast_swarm_telemetry",
    tier=0,
    description="Broadcasts structured multi-agent swarm telemetry events to all active WebSocket listeners.",
    args_schema=BroadcastSwarmTelemetryArgs,
    preview_fn=broadcast_swarm_telemetry_preview,
)
def handle_broadcast_swarm_telemetry(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    event = swarm_telemetry_hub.broadcast_event(event_type=event_type, payload=payload)
    return event


# ============================================================================
# 2. generate_telegram_swarm_card (Tier 0 - Read Only)
# ============================================================================

class GenerateTelegramSwarmCardArgs(BaseModel):
    mission_id: str = Field(..., description="Active mission identifier")
    active_role: str = Field(..., description="Currently active agent role (architect, coder, security_auditor, web_scout)")
    current_task_title: str = Field(..., description="Summary of active task being executed")
    quorum_state: Optional[str] = Field(default="quorum_reached", description="Current quorum status")
    coder_signed: Optional[bool] = Field(default=True, description="Whether Coder has signed off")
    security_signed: Optional[bool] = Field(default=True, description="Whether Security Auditor has signed off")
    vram_mb: Optional[float] = Field(default=4850.0, description="Current VRAM utilization in MB")
    elapsed_seconds: Optional[float] = Field(default=0.0, description="Elapsed mission execution time")


def generate_telegram_swarm_card_preview(args: Dict[str, Any]) -> str:
    mid = args.get("mission_id", "")
    return f"Generate dynamic Telegram markdown status card for mission '{mid}'."


@registry.register(
    name="generate_telegram_swarm_card",
    tier=0,
    description="Generates dynamic ASCII status card with quorum meters and VRAM gauges for Telegram companion.",
    args_schema=GenerateTelegramSwarmCardArgs,
    preview_fn=generate_telegram_swarm_card_preview,
)
def handle_generate_telegram_swarm_card(
    mission_id: str,
    active_role: str,
    current_task_title: str,
    quorum_state: Optional[str] = "quorum_reached",
    coder_signed: Optional[bool] = True,
    security_signed: Optional[bool] = True,
    vram_mb: Optional[float] = 4850.0,
    elapsed_seconds: Optional[float] = 0.0,
) -> Dict[str, Any]:
    card_md = TelegramSwarmCard.format_swarm_card(
        mission_id=mission_id,
        active_role=active_role,
        current_task_title=current_task_title,
        quorum_state=quorum_state or "quorum_reached",
        coder_signed=bool(coder_signed),
        security_signed=bool(security_signed),
        vram_mb=vram_mb or 4850.0,
        elapsed_seconds=elapsed_seconds or 0.0,
    )
    return {
        "mission_id": mission_id,
        "markdown_card": card_md,
    }
