"""
Phenom Voice Persona Tools (VOX-03.3, SAF-01)
Registers tools in ToolRegistry for voice persona style management,
adaptive prosody tuning, and emotion state inspection.
"""

from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.voice.prosody_manager import prosody_manager, STYLE_PRESETS


# =========================================================================
# Pydantic Argument Schemas
# =========================================================================

class GetVoicePersonaStatusArgs(BaseModel):
    pass


class SetVoicePersonaStyleArgs(BaseModel):
    style: str = Field(
        ...,
        description="Target style preset: 'witty_jarvis', 'whisper', 'calm', 'fast', 'urgent', 'normal', or 'auto'/'none' to restore dynamic emotion adaptation."
    )


class AdjustVoiceProsodyArgs(BaseModel):
    rate_delta: Optional[int] = Field(
        default=None,
        ge=-10,
        le=10,
        description="Relative rate change [-10 to +10], e.g. +2 for faster, -2 for slower"
    )
    volume_scale: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Absolute volume scaling [0.0 to 1.0], e.g. 0.5 for 50% volume"
    )


class ResetVoicePersonaArgs(BaseModel):
    pass


# =========================================================================
# Tool Implementations & Registrations
# =========================================================================

@registry.register(
    name="get_voice_persona_status",
    tier=0,
    description="Returns active voice persona telemetry: current emotion, locked style, speech rate, volume, and mute state.",
    args_schema=GetVoicePersonaStatusArgs,
    preview_fn=lambda a: "Inspect active voice persona telemetry"
)
async def get_voice_persona_status() -> Dict[str, Any]:
    """Retrieves current voice persona telemetry and prosody settings."""
    return {
        "status": "success",
        "telemetry": prosody_manager.get_status()
    }


@registry.register(
    name="set_voice_persona_style",
    tier=1,
    description="Locks or sets the voice persona style preset (e.g. witty_jarvis, whisper, calm, fast, urgent, normal, or auto).",
    args_schema=SetVoicePersonaStyleArgs,
    preview_fn=lambda a: f"Lock voice persona style to '{a.get('style', 'auto')}'"
)
async def set_voice_persona_style(style: str) -> Dict[str, Any]:
    """Sets or unlocks the assistant voice style preset."""
    res = prosody_manager.set_style(style)
    return res


@registry.register(
    name="adjust_voice_prosody",
    tier=1,
    description="Fine-tunes speech cadence rate or volume scaling.",
    args_schema=AdjustVoiceProsodyArgs,
    preview_fn=lambda a: f"Adjust speech prosody: rate_delta={a.get('rate_delta')}, volume_scale={a.get('volume_scale')}"
)
async def adjust_voice_prosody(rate_delta: Optional[int] = None, volume_scale: Optional[float] = None) -> Dict[str, Any]:
    """Adjusts speech rate and volume scale directly."""
    res = prosody_manager.adjust_prosody(rate_delta=rate_delta, volume_scale=volume_scale)
    return res


@registry.register(
    name="reset_voice_persona",
    tier=0,
    description="Resets the voice persona and speech prosody to baseline defaults.",
    args_schema=ResetVoicePersonaArgs,
    preview_fn=lambda a: "Reset voice persona and prosody to default baseline"
)
async def reset_voice_persona() -> Dict[str, Any]:
    """Resets voice persona and prosody to default baseline."""
    res = prosody_manager.reset_persona()
    return res
