"""Dynamic Persona Tools Registration (Phase 48-04, PERSONA-01, PERSONA-02, PERSONA-03).

Registers acoustic prosody analysis, dynamic persona modulation,
and spoken milestone briefings into Phenom's Safety ToolRegistry.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.schemas.dynamic_persona import EmotionalState
from services.backend.voice.acoustic_analyzer import AcousticProsodyAnalyzer
from services.backend.voice.persona_modulator import DynamicPersonaModulator
from services.backend.voice.proactive_cues import SpokenHandoffNotifier


# ============================================================================
# 1. analyze_vocal_acoustics (Tier 0 - Read Only)
# ============================================================================

class AnalyzeVocalAcousticsArgs(BaseModel):
    energy_rms: float = Field(..., description="Root Mean Square audio energy")
    pitch_variance: float = Field(..., description="Pitch frequency variance / standard deviation")
    speech_rate_wpm: Optional[float] = Field(default=140.0, description="Estimated speaking rate in words per minute")


def analyze_vocal_acoustics_preview(args: Dict[str, Any]) -> str:
    rms = args.get("energy_rms", 0.0)
    return f"Analyze vocal prosody metrics (RMS={rms:.1f}) to classify emotional urgency."


@registry.register(
    name="analyze_vocal_acoustics",
    tier=0,
    description="Evaluates vocal prosody features (energy, pitch variance, rate) to detect user emotional urgency.",
    args_schema=AnalyzeVocalAcousticsArgs,
    preview_fn=analyze_vocal_acoustics_preview,
)
def handle_analyze_vocal_acoustics(
    energy_rms: float,
    pitch_variance: float,
    speech_rate_wpm: Optional[float] = 140.0,
) -> Dict[str, Any]:
    features = AcousticProsodyAnalyzer.classify_from_values(
        energy_rms=energy_rms,
        pitch_variance=pitch_variance,
        speech_rate_wpm=speech_rate_wpm or 140.0,
    )
    return features.model_dump()


# ============================================================================
# 2. modulate_persona_style (Tier 0 - Read Only / Settings)
# ============================================================================

class ModulatePersonaStyleArgs(BaseModel):
    emotion: str = Field(..., description="Detected emotional state (calm, conversational, urgent, frustrated)")


def modulate_persona_style_preview(args: Dict[str, Any]) -> str:
    emo = args.get("emotion", "conversational")
    return f"Calculate dynamic Jarvis persona speech parameters for emotional state '{emo}'."


@registry.register(
    name="modulate_persona_style",
    tier=0,
    description="Returns dynamic Jarvis persona synthesis settings (humor, brevity, pacing) based on emotional state.",
    args_schema=ModulatePersonaStyleArgs,
    preview_fn=modulate_persona_style_preview,
)
def handle_modulate_persona_style(emotion: str) -> Dict[str, Any]:
    try:
        e_state = EmotionalState(emotion.lower())
    except ValueError:
        e_state = EmotionalState.CONVERSATIONAL

    profile = DynamicPersonaModulator.get_profile_for_emotion(e_state)
    return profile.model_dump()


# ============================================================================
# 3. dispatch_spoken_briefing (Tier 1)
# ============================================================================

class DispatchSpokenBriefingArgs(BaseModel):
    event_type: str = Field(..., description="Type of briefing: handoff, quorum, or complete")
    detail_a: Optional[str] = Field(default="", description="First detail (e.g. from_role, state, patch_id)")
    detail_b: Optional[str] = Field(default="", description="Second detail (e.g. to_role, is_approved, file_count)")


def dispatch_spoken_briefing_preview(args: Dict[str, Any]) -> str:
    etype = args.get("event_type", "handoff")
    return f"Generate and play spoken audio milestone briefing for '{etype}' event."


@registry.register(
    name="dispatch_spoken_briefing",
    tier=1,
    description="Generates concise (<25 words) spoken voice briefing announcing swarm handoffs or milestone progress.",
    args_schema=DispatchSpokenBriefingArgs,
    preview_fn=dispatch_spoken_briefing_preview,
    can_remember_per_folder=False,
)
def handle_dispatch_spoken_briefing(
    event_type: str,
    detail_a: Optional[str] = "",
    detail_b: Optional[str] = "",
) -> Dict[str, Any]:
    etype = event_type.lower()
    if etype == "handoff":
        briefing = SpokenHandoffNotifier.create_handoff_briefing(
            from_role=detail_a or "architect",
            to_role=detail_b or "coder",
        )
    elif etype == "quorum":
        approved = str(detail_b).lower() in ("true", "1", "yes")
        briefing = SpokenHandoffNotifier.create_quorum_briefing(
            state=detail_a or "quorum_reached",
            is_approved=approved,
        )
    elif etype == "complete":
        count = int(detail_b) if detail_b and str(detail_b).isdigit() else 1
        briefing = SpokenHandoffNotifier.create_mission_complete_briefing(
            patch_id=detail_a or "patch_001",
            file_count=count,
        )
    else:
        briefing = SpokenHandoffNotifier.create_handoff_briefing("agent", "agent", detail_a or "")

    return briefing.model_dump()
