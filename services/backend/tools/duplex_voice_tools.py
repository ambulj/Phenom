"""Duplex Voice Tools Registration (Phase 48-03, VOICE-01, VOICE-02, VOICE-03).

Registers full-duplex streaming configuration, guidance injection,
and real-time audio telemetry into Phenom's Safety ToolRegistry.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.voice.full_duplex_stream import FullDuplexStreamManager
from services.backend.voice.swarm_voice_bridge import SwarmVoiceBridge

# Singleton instances for duplex voice pipeline
duplex_manager = FullDuplexStreamManager()
swarm_bridge = SwarmVoiceBridge(barge_in_handler=duplex_manager.barge_in)


# ============================================================================
# 1. configure_duplex_streaming (Tier 0 - Read Only / Settings)
# ============================================================================

class ConfigureDuplexStreamingArgs(BaseModel):
    vad_threshold: Optional[float] = Field(
        default=0.40,
        ge=0.1,
        le=0.9,
        description="Voice Activity Detection sensitivity threshold",
    )
    buffer_seconds: Optional[float] = Field(
        default=3.0,
        ge=1.0,
        le=10.0,
        description="Pre-roll in-RAM ring buffer duration in seconds",
    )


def configure_duplex_streaming_preview(args: Dict[str, Any]) -> str:
    thresh = args.get("vad_threshold", 0.40)
    return f"Tune duplex audio VAD threshold to {thresh} and set buffer."


@registry.register(
    name="configure_duplex_streaming",
    tier=0,
    description="Configures sensitivity and buffer size for full-duplex audio stream.",
    args_schema=ConfigureDuplexStreamingArgs,
    preview_fn=configure_duplex_streaming_preview,
)
def handle_configure_duplex_streaming(
    vad_threshold: Optional[float] = 0.40,
    buffer_seconds: Optional[float] = 3.0,
) -> Dict[str, Any]:
    if vad_threshold is not None:
        duplex_manager.vad_threshold = vad_threshold
    if buffer_seconds is not None:
        duplex_manager.buffer_seconds = buffer_seconds

    return {
        "status": "configured",
        "vad_threshold": duplex_manager.vad_threshold,
        "buffer_seconds": duplex_manager.buffer_seconds,
    }


# ============================================================================
# 2. inject_voice_guidance (Tier 1)
# ============================================================================

class InjectVoiceGuidanceArgs(BaseModel):
    transcript: str = Field(..., description="Spoken operator directive or guidance text")
    target_task_id: Optional[str] = Field(
        default=None,
        description="Optional target task ID in active swarm queue",
    )


def inject_voice_guidance_preview(args: Dict[str, Any]) -> str:
    text = args.get("transcript", "")
    return f"Inject spoken guidance into active swarm queue: '{text}'."


@registry.register(
    name="inject_voice_guidance",
    tier=1,
    description="Injects high-priority spoken steering guidance into active swarm tasks without aborting worker threads.",
    args_schema=InjectVoiceGuidanceArgs,
    preview_fn=inject_voice_guidance_preview,
    can_remember_per_folder=False,
)
def handle_inject_voice_guidance(
    transcript: str,
    target_task_id: Optional[str] = None,
) -> Dict[str, Any]:
    injection = swarm_bridge.inject_guidance(
        transcript=transcript,
        target_task_id=target_task_id,
    )
    return injection.model_dump()


# ============================================================================
# 3. get_duplex_voice_metrics (Tier 0 - Read Only)
# ============================================================================

class GetDuplexVoiceMetricsArgs(BaseModel):
    pass


def get_duplex_voice_metrics_preview(args: Dict[str, Any]) -> str:
    return "Query real-time full-duplex audio telemetry and barge-in metrics."


@registry.register(
    name="get_duplex_voice_metrics",
    tier=0,
    description="Returns real-time audio roundtrip latency, VAD probability, and soft-mute telemetry.",
    args_schema=GetDuplexVoiceMetricsArgs,
    preview_fn=get_duplex_voice_metrics_preview,
)
def handle_get_duplex_voice_metrics() -> Dict[str, Any]:
    metrics = duplex_manager.get_metrics()
    return metrics.model_dump()
