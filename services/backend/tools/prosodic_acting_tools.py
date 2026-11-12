"""
Phenom Prosodic Acting Safety Tools
ToolRegistry integration for dynamic emotion envelopes, pitch contour modulation,
and respiratory breath synthesis.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.voice.prosodic_acting_engine import (
    prosodic_acting_engine,
    ActingEmotion,
    enforce_anti_checkout,
    Rule8ViolationError,
)


# ==========================================
# 1. Apply Prosodic Acting Envelope (Tier 0)
# ==========================================

class ApplyProsodicActingEnvelopeArgs(BaseModel):
    text: str = Field(
        ...,
        description="Text utterance to enrich with prosodic pitch tags and respiratory breath pauses",
    )
    emotion: Optional[str] = Field(
        None,
        description="Optional acting emotion: 'WARM_WIT', 'CONSPIRATORIAL', 'TACTICAL_ALERT', 'CALM_REASSURING', 'EXECUTIVE_CONCISE'",
    )
    inject_breaths: bool = Field(
        True,
        description="Whether to insert natural respiratory breath markers at syntactic clause boundaries",
    )


def preview_apply_prosodic_acting_envelope(args: Dict[str, Any]) -> str:
    emo = args.get("emotion", "ACTIVE_EMOTION")
    txt = args.get("text", "")
    preview_txt = (txt[:30] + "...") if len(txt) > 30 else txt
    return f"Apply prosodic envelope ({emo}) to text: '{preview_txt}'."


@registry.register(
    name="apply_prosodic_acting_envelope",
    tier=0,
    description="Enriches text with emotional prosodic pitch tags and respiratory breath pauses (Tier 0 text processing).",
    args_schema=ApplyProsodicActingEnvelopeArgs,
    preview_fn=preview_apply_prosodic_acting_envelope,
    can_remember_per_folder=False,
)
def handle_apply_prosodic_acting_envelope(
    text: str,
    emotion: Optional[str] = None,
    inject_breaths: bool = True,
) -> Dict[str, Any]:
    target_emotion = None
    if emotion:
        try:
            target_emotion = ActingEmotion(emotion.upper())
        except ValueError:
            target_emotion = None

    return prosodic_acting_engine.apply_acting_envelope(
        text=text,
        emotion=target_emotion,
        inject_breaths=inject_breaths,
    )


# ==========================================
# 2. Configure Prosodic Parameters (Tier 1)
# ==========================================

class ConfigureProsodicParametersArgs(BaseModel):
    emotion: Optional[str] = Field(
        None,
        description="Active acting emotion: 'WARM_WIT', 'CONSPIRATORIAL', 'TACTICAL_ALERT', 'CALM_REASSURING', 'EXECUTIVE_CONCISE'",
    )
    custom_pitch_shift: Optional[float] = Field(
        None,
        ge=-12.0,
        le=12.0,
        description="Pitch shift in semitones (-12.0 to +12.0)",
    )
    custom_intensity: Optional[float] = Field(
        None,
        ge=0.1,
        le=2.0,
        description="Energy intensity multiplier (0.1 to 2.0)",
    )
    breath_enabled: Optional[bool] = Field(
        None,
        description="Toggle natural respiratory breath insertion",
    )


def preview_configure_prosodic_parameters(args: Dict[str, Any]) -> str:
    emo = args.get("emotion", "unchanged")
    return f"Configure prosodic acting parameters: emotion={emo}."


@registry.register(
    name="configure_prosodic_parameters",
    tier=1,
    description="Updates emotional acting mode, custom pitch shift, and respiratory breath settings (Tier 1 configuration).",
    args_schema=ConfigureProsodicParametersArgs,
    preview_fn=preview_configure_prosodic_parameters,
    can_remember_per_folder=False,
)
def handle_configure_prosodic_parameters(
    emotion: Optional[str] = None,
    custom_pitch_shift: Optional[float] = None,
    custom_intensity: Optional[float] = None,
    breath_enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    target_emotion = None
    if emotion:
        try:
            target_emotion = ActingEmotion(emotion.upper())
        except ValueError:
            return {"status": "ERROR", "message": f"Invalid emotion: {emotion}"}

    config = prosodic_acting_engine.configure_parameters(
        emotion=target_emotion,
        custom_pitch_shift=custom_pitch_shift,
        custom_intensity=custom_intensity,
        breath_enabled=breath_enabled,
    )
    return {
        "status": "CONFIGURED",
        "config": config,
    }


# ==========================================
# 3. Get Active Prosodic Telemetry (Tier 0)
# ==========================================

class GetActiveProsodicTelemetryArgs(BaseModel):
    pass


def preview_get_active_prosodic_telemetry(args: Dict[str, Any]) -> str:
    return "Query active emotional acting envelope, pitch contour telemetry, and breath stats."


@registry.register(
    name="get_active_prosodic_telemetry",
    tier=0,
    description="Queries active emotional envelope, pitch shift, cadence multiplier, and breath stats (Tier 0 read-only).",
    args_schema=GetActiveProsodicTelemetryArgs,
    preview_fn=preview_get_active_prosodic_telemetry,
    can_remember_per_folder=False,
)
def handle_get_active_prosodic_telemetry() -> Dict[str, Any]:
    telem = prosodic_acting_engine.get_telemetry()
    return {
        "active_emotion": telem.active_emotion.value,
        "pitch_shift_semitones": telem.pitch_shift_semitones,
        "cadence_multiplier": telem.cadence_multiplier,
        "energy_intensity": telem.energy_intensity,
        "breath_markers_inserted": telem.breath_markers_inserted,
        "prosodic_tags_count": telem.prosodic_tags_count,
        "is_halted": telem.is_halted,
        "timestamp": telem.timestamp,
    }


# ==========================================
# 4. Synthesize Prosodic Speech Preview (Tier 0)
# ==========================================

class SynthesizeProsodicSpeechPreviewArgs(BaseModel):
    text: str = Field(
        ...,
        description="Text utterance to evaluate with prosodic pitch curves and breath pauses",
    )
    emotion: Optional[str] = Field(
        None,
        description="Optional acting emotion for the preview",
    )


def preview_synthesize_prosodic_speech_preview(args: Dict[str, Any]) -> str:
    txt = args.get("text", "")
    preview_txt = (txt[:30] + "...") if len(txt) > 30 else txt
    return f"Synthesize prosodic preview with F0 pitch curve for: '{preview_txt}'."


@registry.register(
    name="synthesize_prosodic_speech_preview",
    tier=0,
    description="Synthesizes speech preview metadata with calculated F0 pitch curves and breath points (Tier 0 preview).",
    args_schema=SynthesizeProsodicSpeechPreviewArgs,
    preview_fn=preview_synthesize_prosodic_speech_preview,
    can_remember_per_folder=False,
)
def handle_synthesize_prosodic_speech_preview(
    text: str,
    emotion: Optional[str] = None,
) -> Dict[str, Any]:
    target_emotion = None
    if emotion:
        try:
            target_emotion = ActingEmotion(emotion.upper())
        except ValueError:
            target_emotion = None

    return prosodic_acting_engine.synthesize_preview(
        text=text,
        emotion=target_emotion,
    )
