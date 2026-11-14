"""
Conversational Cyber Voice Synapse Tools
Milestone 43.0: Project FULL-DUPLEX JARVIS (Phase 3)

Registers:
1. dispatch_voice_cyber_synapse (Tier 1 confirmation required):
   Dispatches spoken natural language commands directly to autonomous cyber tools
   with sub-100ms routing, Safe-Mode validation, and prosodic acting envelopes.
2. get_voice_synapse_status (Tier 0 read-only):
   Queries dispatch counts, last routing latency, and safe subnet definitions.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.voice.voice_cyber_synapse import voice_cyber_synapse


# ==========================================
# 1. Dispatch Voice Cyber Synapse (Tier 1)
# ==========================================

class DispatchVoiceCyberSynapseArgs(BaseModel):
    voice_command: str = Field(..., description="Spoken natural language cyber directive (e.g. 'scan local network', 'run rootkit hunter', 'launch 5-stage lab mission')")
    dry_run: Optional[bool] = Field(default=False, description="Preview dispatch routing without executing underlying cyber tool")


def preview_dispatch_voice_cyber_synapse(args: Dict[str, Any]) -> str:
    cmd = args.get("voice_command", "")
    dr = " (dry-run preview)" if args.get("dry_run") else ""
    return f"Dispatch spoken cyber directive: '{cmd}'{dr}"


@registry.register(
    name="dispatch_voice_cyber_synapse",
    tier=1,
    description="Maps hands-free voice commands to autonomous cyber reconnaissance, rootkit audits, threat intel, and multi-stage DAGs with Safe-Mode boundary enforcement (Tier 1).",
    args_schema=DispatchVoiceCyberSynapseArgs,
    preview_fn=preview_dispatch_voice_cyber_synapse,
    can_remember_per_folder=False,
)
def handle_dispatch_voice_cyber_synapse(voice_command: str, dry_run: bool = False) -> Dict[str, Any]:
    return voice_cyber_synapse.dispatch_voice_command(voice_text=voice_command, dry_run=dry_run)


# ==========================================
# 2. Get Voice Synapse Status (Tier 0)
# ==========================================

class GetVoiceSynapseStatusArgs(BaseModel):
    pass


def preview_get_voice_synapse_status(args: Dict[str, Any]) -> str:
    return "Query hands-free cyber voice synapse telemetry and routing latencies (Tier 0)"


@registry.register(
    name="get_voice_synapse_status",
    tier=0,
    description="Returns real-time dispatch counters, sub-100ms intent routing metrics, and Safe-Mode subnet status (Tier 0 read-only).",
    args_schema=GetVoiceSynapseStatusArgs,
    preview_fn=preview_get_voice_synapse_status,
    can_remember_per_folder=False,
)
def handle_get_voice_synapse_status() -> Dict[str, Any]:
    return voice_cyber_synapse.get_status()
