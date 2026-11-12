from typing import Dict, Any, Optional

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.voice_action import (
    VoiceKernelGetStatusArgs,
    VoiceKernelConfigureArgs,
    VoiceKernelSimulateChunkArgs,
    VoiceKernelAbortIntentArgs,
)
from services.backend.voice_action import streaming_voice_action_kernel


@registry.register(
    name="voice_kernel_get_status",
    tier=0,
    description="Get real-time telemetry, noise floor, and recent actions from the Voice-to-Action Kernel.",
    args_schema=VoiceKernelGetStatusArgs,
    preview_fn=lambda args: "Querying voice-to-action kernel status (Tier 0 read-only)",
)
def voice_kernel_get_status(session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Retrieve current voice kernel state and action telemetry."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is engaged.")
    return streaming_voice_action_kernel.get_status().model_dump()


def _preview_voice_kernel_configure(args: Dict[str, Any]) -> str:
    return (
        f"Configure Voice-to-Action Kernel: VAD threshold={args.get('vad_threshold')}, "
        f"noise_floor={args.get('noise_floor_rms')}, barge_in_sensitivity={args.get('barge_in_sensitivity')}"
    )


@registry.register(
    name="voice_kernel_configure",
    tier=1,
    description="Configure VAD sensitivity, noise floor calibration, and barge-in thresholds.",
    args_schema=VoiceKernelConfigureArgs,
    preview_fn=_preview_voice_kernel_configure,
)
def voice_kernel_configure(
    vad_threshold: Optional[float] = None,
    noise_floor_rms: Optional[float] = None,
    barge_in_sensitivity: Optional[float] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Configure acoustic and VAD thresholds."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is engaged.")
    return streaming_voice_action_kernel.configure(
        vad_threshold=vad_threshold,
        noise_floor_rms=noise_floor_rms,
        barge_in_sensitivity=barge_in_sensitivity,
    )


def _preview_voice_kernel_simulate_chunk(args: Dict[str, Any]) -> str:
    return (
        f"Simulate voice chunk: RMS={args.get('rms_energy')}, "
        f"speech_prob={args.get('speech_prob')}, transcript='{args.get('transcript_text')}'"
    )


@registry.register(
    name="voice_kernel_simulate_chunk",
    tier=1,
    description="Simulate acoustic audio chunk ingestion with optional transcript intent dispatch.",
    args_schema=VoiceKernelSimulateChunkArgs,
    preview_fn=_preview_voice_kernel_simulate_chunk,
)
def voice_kernel_simulate_chunk(
    rms_energy: float,
    speech_prob: float,
    transcript_text: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Simulate audio chunk ingestion with intent dispatch."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is engaged.")
    return streaming_voice_action_kernel.ingest_chunk(
        rms_energy=rms_energy,
        speech_prob=speech_prob,
        transcript_text=transcript_text,
    )


def _preview_voice_kernel_abort_intent(args: Dict[str, Any]) -> str:
    return f"Abort dispatched voice action with ID '{args.get('action_id')}'"


@registry.register(
    name="voice_kernel_abort_intent",
    tier=1,
    description="Abort an active or pending voice action.",
    args_schema=VoiceKernelAbortIntentArgs,
    preview_fn=_preview_voice_kernel_abort_intent,
)
def voice_kernel_abort_intent(action_id: str, **kwargs) -> Dict[str, Any]:
    """Abort an active or pending voice action."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is engaged.")
    aborted = streaming_voice_action_kernel.abort_action(action_id)
    return {"action_id": action_id, "aborted": aborted}
