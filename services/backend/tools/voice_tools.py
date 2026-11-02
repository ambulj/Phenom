"""
Phenom Voice & Presence Tools
Provides tool endpoints for inspecting full-duplex conversational voice state,
configuring presence-based speech modulation, and triggering instantaneous barge-in.
Strictly respects SAFETY.md:
- get_voice_duplex_status (Tier 0): Read-only status overview.
- configure_voice_presence (Tier 1): Requires interactive preview confirmation.
- trigger_voice_barge_in (Tier 0): Instantaneous speech interruption.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.voice.duplex_pipeline import duplex_pipeline
from services.backend.voice.voice_modulator import voice_modulator, AssistantMode
from services.backend.voice.barge_in_controller import barge_in_controller


class GetVoiceDuplexStatusArgs(BaseModel):
    """Schema for get_voice_duplex_status query (no arguments required)."""
    pass


class ConfigureVoicePresenceArgs(BaseModel):
    mode: Optional[str] = Field(
        default=None,
        description="Assistant mode to enforce ('work', 'study', 'chill', 'deep_focus')"
    )
    volume: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Master voice volume scale (0.0 to 1.0)"
    )
    rate: Optional[int] = Field(
        default=None,
        ge=-10,
        le=10,
        description="Speech cadence rate (-10 to 10)"
    )
    clear_overrides: Optional[bool] = Field(
        default=False,
        description="Whether to clear all manual overrides and return to automatic context detection"
    )


class TriggerVoiceBargeInArgs(BaseModel):
    """Schema for trigger_voice_barge_in (no arguments required)."""
    pass


@registry.register(
    name="get_voice_duplex_status",
    tier=0,
    description="Returns real-time metrics of the full-duplex voice pipeline, Silero VAD availability, and contextual speech modulation settings. Read-only.",
    args_schema=GetVoiceDuplexStatusArgs,
    preview_fn=lambda a: "Inspect full-duplex voice pipeline and speech modulation status (Read-only)",
)
def get_voice_duplex_status(**kwargs) -> Dict[str, Any]:
    pipeline_metrics = duplex_pipeline.get_metrics()
    modulator_status = voice_modulator.get_status()
    return {
        "status": "ok",
        "duplex_pipeline": pipeline_metrics,
        "voice_modulation": modulator_status,
    }


@registry.register(
    name="configure_voice_presence",
    tier=1,
    description="Configures voice presence mode and adapts speech volume scale, cadence rate, or conversational tone. Requires confirmation.",
    args_schema=ConfigureVoicePresenceArgs,
    preview_fn=lambda a: f"Configure voice presence: mode='{a.get('mode')}', volume={a.get('volume')}, rate={a.get('rate')}, clear={a.get('clear_overrides')}",
)
def configure_voice_presence(
    mode: Optional[str] = None,
    volume: Optional[float] = None,
    rate: Optional[int] = None,
    clear_overrides: bool = False,
    **kwargs
) -> Dict[str, Any]:
    if clear_overrides:
        voice_modulator.clear_overrides()
        return {
            "status": "cleared_overrides",
            "effective_profile": voice_modulator.get_effective_profile(),
        }

    target_mode = None
    if mode:
        try:
            target_mode = AssistantMode(mode.lower().strip())
        except ValueError:
            return {
                "status": "error",
                "message": f"Invalid mode '{mode}'. Choose from 'work', 'study', 'chill', 'deep_focus'.",
            }

    voice_modulator.set_override(volume=volume, rate=rate, mode=target_mode)
    updated_profile = voice_modulator.get_effective_profile()
    return {
        "status": "configured",
        "effective_profile": updated_profile,
    }


@registry.register(
    name="trigger_voice_barge_in",
    tier=0,
    description="Triggers instantaneous conversational barge-in, immediately silencing assistant speech in < 50ms. Read-only / low-risk.",
    args_schema=TriggerVoiceBargeInArgs,
    preview_fn=lambda a: "Trigger instantaneous conversational barge-in speech interruption (Read-only)",
)
def trigger_voice_barge_in(**kwargs) -> Dict[str, Any]:
    stop_latency = barge_in_controller.interrupt_now()
    return {
        "status": "interrupted",
        "stop_latency_ms": round(stop_latency, 2),
    }
