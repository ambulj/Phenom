"""Full-Duplex Conversational Voice & Acoustic Barge-In Tools for Phenom (Milestone 30 Phase 3).

Registers 4 specialized full-duplex tools in ToolRegistry:
1. get_full_duplex_voice_state (Tier 0)
2. configure_full_duplex_thresholds (Tier 1)
3. trigger_acoustic_barge_in_test (Tier 1)
4. reset_full_duplex_state_machine (Tier 0)
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.voice.full_duplex_voice_engine import (
    full_duplex_voice_engine,
)


# ==========================================
# 1. Get Full-Duplex Voice State (Tier 0)
# ==========================================

class GetFullDuplexVoiceStateArgs(BaseModel):
    pass


def preview_get_full_duplex_voice_state(args: Dict[str, Any]) -> str:
    return "Query real-time full-duplex turn-taking state, VAD speech probability, and barge-in latencies"


@registry.register(
    name="get_full_duplex_voice_state",
    tier=0,
    description="Returns real-time turn-taking state (LISTENING, USER_SPEAKING, PROCESSING, AGENT_SPEAKING), VAD probability, and acoustic barge-in telemetry (Tier 0 read-only).",
    args_schema=GetFullDuplexVoiceStateArgs,
    preview_fn=preview_get_full_duplex_voice_state,
    can_remember_per_folder=False,
)
def handle_get_full_duplex_voice_state() -> Dict[str, Any]:
    return full_duplex_voice_engine.get_state()


# ==========================================
# 2. Configure Full-Duplex Thresholds (Tier 1)
# ==========================================

class ConfigureFullDuplexThresholdsArgs(BaseModel):
    vad_threshold: Optional[float] = Field(
        None, description="VAD speech detection confidence threshold (0.1 to 0.95)."
    )
    pause_hangover_chunks: Optional[int] = Field(
        None, description="Number of consecutive silence chunks (~32ms each) before concluding user turn."
    )
    required_consecutive_chunks: Optional[int] = Field(
        None, description="Consecutive speech chunks required for onset hysteresis (default 2)."
    )


def preview_configure_full_duplex_thresholds(args: Dict[str, Any]) -> str:
    thresh = args.get("vad_threshold", "unchanged")
    hangover = args.get("pause_hangover_chunks", "unchanged")
    return f"Configure voice full-duplex thresholds: vad_threshold={thresh}, hangover_chunks={hangover}"


@registry.register(
    name="configure_full_duplex_thresholds",
    tier=1,
    description="Configures VAD sensitivity and turn-taking conversational pause hangover durations (Tier 1 state mutation).",
    args_schema=ConfigureFullDuplexThresholdsArgs,
    preview_fn=preview_configure_full_duplex_thresholds,
    can_remember_per_folder=False,
)
def handle_configure_full_duplex_thresholds(
    vad_threshold: Optional[float] = None,
    pause_hangover_chunks: Optional[int] = None,
    required_consecutive_chunks: Optional[int] = None,
) -> Dict[str, Any]:
    return full_duplex_voice_engine.configure_thresholds(
        vad_threshold=vad_threshold,
        pause_hangover_chunks=pause_hangover_chunks,
        required_consecutive_chunks=required_consecutive_chunks,
    )


# ==========================================
# 3. Trigger Acoustic Barge-In Test (Tier 1)
# ==========================================

class TriggerAcousticBargeInTestArgs(BaseModel):
    pass


def preview_trigger_acoustic_barge_in_test(args: Dict[str, Any]) -> str:
    return "Simulate incoming user speech chunk during agent playback and benchmark acoustic halt latency (< 15ms SLA)"


@registry.register(
    name="trigger_acoustic_barge_in_test",
    tier=1,
    description="Simulates incoming user speech to benchmark acoustic barge-in interruption latency against the 15.0ms SLA target (Tier 1 execution).",
    args_schema=TriggerAcousticBargeInTestArgs,
    preview_fn=preview_trigger_acoustic_barge_in_test,
    can_remember_per_folder=False,
)
def handle_trigger_acoustic_barge_in_test() -> Dict[str, Any]:
    return full_duplex_voice_engine.trigger_acoustic_barge_in_test()


# ==========================================
# 4. Reset Full-Duplex State Machine (Tier 0)
# ==========================================

class ResetFullDuplexStateMachineArgs(BaseModel):
    pass


def preview_reset_full_duplex_state_machine(args: Dict[str, Any]) -> str:
    return "Reset full-duplex turn-taking state to LISTENING and purge active audio buffers"


@registry.register(
    name="reset_full_duplex_state_machine",
    tier=0,
    description="Resets the voice turn-taking finite state machine to LISTENING and clears RAM audio ring buffers (Tier 0 safe reset).",
    args_schema=ResetFullDuplexStateMachineArgs,
    preview_fn=preview_reset_full_duplex_state_machine,
    can_remember_per_folder=False,
)
def handle_reset_full_duplex_state_machine() -> Dict[str, Any]:
    return full_duplex_voice_engine.reset_state_machine()
