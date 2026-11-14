"""
Acoustic Barge-In & Audio Guardian E-Stop Tools for Phenom
Milestone 43.0: Project FULL-DUPLEX JARVIS (Phase 2)

Registers:
1. set_duplex_voice_state (Tier 1 confirmation required):
   Configures voice duplex activity, mute state, energy threshold, and required onset chunks.
2. query_voice_latency_metrics (Tier 0 read-only):
   Queries real-time acoustic barge-in latency, emergency spoken halt SLA, and onset latency.
3. trigger_voice_emergency_stop (Tier 0 emergency e-stop):
   Directly executes voice-commanded emergency stop via Guardian Kill Switch (< 25ms SLA).
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.voice.barge_in_controller import barge_in_controller
from services.backend.voice.tts import tts_engine


# ==========================================
# 1. Set Duplex Voice State (Tier 1)
# ==========================================

class SetDuplexVoiceStateArgs(BaseModel):
    active: Optional[bool] = Field(None, description="Enable or disable duplex listening pipeline.")
    muted: Optional[bool] = Field(None, description="Mute or unmute microphone audio ingestion.")
    energy_threshold: Optional[float] = Field(None, description="RMS energy threshold for acoustic detection (0.005 to 1.0).")
    required_chunks: Optional[int] = Field(None, description="Required consecutive speech chunks for onset confirmation.")


def preview_set_duplex_voice_state(args: Dict[str, Any]) -> str:
    acts = []
    if "active" in args:
        acts.append(f"active={args['active']}")
    if "muted" in args:
        acts.append(f"muted={args['muted']}")
    if "energy_threshold" in args:
        acts.append(f"energy_threshold={args['energy_threshold']}")
    if "required_chunks" in args:
        acts.append(f"required_chunks={args['required_chunks']}")
    return f"Configure duplex voice state: {', '.join(acts) if acts else 'no change'}"


@registry.register(
    name="set_duplex_voice_state",
    tier=1,
    description="Configures duplex voice parameters: active, muted, energy threshold, and required onset chunks (Tier 1).",
    args_schema=SetDuplexVoiceStateArgs,
    preview_fn=preview_set_duplex_voice_state,
    can_remember_per_folder=False,
)
def handle_set_duplex_voice_state(
    active: Optional[bool] = None,
    muted: Optional[bool] = None,
    energy_threshold: Optional[float] = None,
    required_chunks: Optional[int] = None,
) -> Dict[str, Any]:
    barge_in_controller.configure(
        energy_threshold=energy_threshold,
        required_chunks=required_chunks,
    )
    return {
        "status": "success",
        "active": active,
        "muted": muted,
        "energy_threshold": barge_in_controller.energy_threshold,
        "required_chunks": barge_in_controller.required_chunks,
    }


# ==========================================
# 2. Query Voice Latency Metrics (Tier 0)
# ==========================================

class QueryVoiceLatencyMetricsArgs(BaseModel):
    pass


def preview_query_voice_latency_metrics(args: Dict[str, Any]) -> str:
    return "Query real-time acoustic barge-in latency and Guardian audio emergency metrics (Tier 0)"


@registry.register(
    name="query_voice_latency_metrics",
    tier=0,
    description="Returns real-time acoustic barge-in latency metrics, speech onset stats, and audio Guardian E-Stop latencies (Tier 0 read-only).",
    args_schema=QueryVoiceLatencyMetricsArgs,
    preview_fn=preview_query_voice_latency_metrics,
    can_remember_per_folder=False,
)
def handle_query_voice_latency_metrics() -> Dict[str, Any]:
    metrics = barge_in_controller.get_metrics()
    metrics["guardian_halted"] = guardian.is_halted
    metrics["tts_speaking"] = getattr(tts_engine, "is_speaking", False)
    return metrics


# ==========================================
# 3. Trigger Voice Emergency Stop (Tier 0)
# ==========================================

class TriggerVoiceEmergencyStopArgs(BaseModel):
    reason: Optional[str] = Field("Direct voice emergency stop requested", description="Reason for triggering the audio emergency stop.")


def preview_trigger_voice_emergency_stop(args: Dict[str, Any]) -> str:
    return f"Trigger emergency Guardian kill switch via voice command: '{args.get('reason', 'emergency stop')}' (Tier 0)"


@registry.register(
    name="trigger_voice_emergency_stop",
    tier=0,
    description="Directly triggers the audio Guardian E-Stop kill switch in < 25ms SLA, halting all speech, tools, and background pipelines (Tier 0).",
    args_schema=TriggerVoiceEmergencyStopArgs,
    preview_fn=preview_trigger_voice_emergency_stop,
    can_remember_per_folder=False,
)
def handle_trigger_voice_emergency_stop(reason: str = "Direct voice emergency stop requested") -> Dict[str, Any]:
    t0 = time.perf_counter()
    barge_in_controller.stop_all_audio()
    guardian.trigger(f"Voice E-Stop tool: {reason}")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "status": "halted",
        "reason": reason,
        "elapsed_ms": round(elapsed_ms, 3),
        "sla_met": elapsed_ms < 25.0,
        "is_halted": guardian.is_halted,
    }
