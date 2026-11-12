"""
Omni-Modal Spatial Telepresence Tools (AVP-01, SAF-01, SAF-02).
Registers Tier 0 and Tier 1 tools for managing low-latency streaming AV sessions,
controlling microphone mute states and camera privacy shutters, and ingesting telemetry.
"""

from typing import Any, Dict, List, Optional, Tuple

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.telepresence import (
    SensorState,
    TelepresenceGetStatusArgs,
    TelepresenceIngestFrameArgs,
    TelepresenceSetCameraArgs,
    TelepresenceSetMicrophoneArgs,
)
from services.backend.telepresence import streaming_av_pipeline


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="telepresence_get_status",
    tier=0,
    description="Inspects active AV telepresence session state, sensor privacy status, and ambient metrics (Read-Only)",
    args_schema=TelepresenceGetStatusArgs,
    preview_fn=lambda a: "Inspect AV telepresence session state, microphone/camera statuses, and ambient presence metrics (Read-Only)",
)
def telepresence_get_status(**kwargs) -> Dict[str, Any]:
    """Inspect telepresence session state."""
    state = streaming_av_pipeline.get_state()
    return {
        "status": "success",
        "telepresence_state": state.model_dump(),
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

def _preview_set_microphone(args: Dict[str, Any]) -> str:
    state = args.get("state", "MUTED")
    gain = args.get("gain", 1.0)
    return f"Set microphone hardware state to {state} (Gain: {gain:.1f}x)"


@registry.register(
    name="telepresence_set_microphone",
    tier=1,
    description="Controls microphone hardware mute state and software gain (Tier 1 Preview)",
    args_schema=TelepresenceSetMicrophoneArgs,
    preview_fn=_preview_set_microphone,
)
def telepresence_set_microphone(state: SensorState, gain: float = 1.0, **kwargs) -> Dict[str, Any]:
    """Control microphone hardware state."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: microphone control blocked.")

    sensor_state = SensorState(state)
    new_state = streaming_av_pipeline.set_microphone(state=sensor_state, gain=gain)
    return {
        "status": "success",
        "action": "set_microphone",
        "new_state": new_state.model_dump(),
    }


def _preview_set_camera(args: Dict[str, Any]) -> str:
    state = args.get("state", "SHUTTERED")
    res = args.get("resolution", "1280x720")
    return f"Set camera privacy shutter to {state} (Target Resolution: {res})"


@registry.register(
    name="telepresence_set_camera",
    tier=1,
    description="Controls camera privacy shutter and resolution (Tier 1 Preview)",
    args_schema=TelepresenceSetCameraArgs,
    preview_fn=_preview_set_camera,
)
def telepresence_set_camera(state: SensorState, resolution: str = "1280x720", **kwargs) -> Dict[str, Any]:
    """Control camera privacy shutter."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: camera control blocked.")

    sensor_state = SensorState(state)
    new_state = streaming_av_pipeline.set_camera(state=sensor_state, resolution=resolution)
    return {
        "status": "success",
        "action": "set_camera",
        "new_state": new_state.model_dump(),
    }


def _preview_ingest_frame(args: Dict[str, Any]) -> str:
    rms = args.get("audio_rms", 0.0)
    speech = args.get("speech_probability", 0.0)
    landmarks = args.get("landmarks", [])
    return f"Ingest transient AV telemetry (Audio RMS: {rms:.2f}, Speech Prob: {speech:.2f}, Landmarks: {len(landmarks)}) without storing raw media (Rule 4)"


@registry.register(
    name="telepresence_ingest_frame",
    tier=1,
    description="Ingests transient audio-visual telemetry with zero raw media persistence (Tier 1 Preview)",
    args_schema=TelepresenceIngestFrameArgs,
    preview_fn=_preview_ingest_frame,
)
def telepresence_ingest_frame(
    audio_rms: float,
    speech_probability: float,
    timestamp: float,
    landmarks: Optional[List[Tuple[float, float]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Ingest transient telemetry without storing raw media."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: telemetry ingestion blocked.")

    landmarks_list = landmarks or []
    res = streaming_av_pipeline.ingest_telemetry(
        audio_rms=audio_rms,
        speech_probability=speech_probability,
        landmarks=landmarks_list,
        timestamp=timestamp,
    )
    return {
        "status": "success",
        "ingestion": res,
    }
