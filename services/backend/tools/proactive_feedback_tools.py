"""
Proactive Sensory Event Bus & Ambient Feedback Safety Tools (PRX-01, FBK-01, SAF-01, SAF-02).
Registers Tier 0 and Tier 1 governance tools for system context event monitoring,
real-time privacy scrubbing, ambient spatial audio cue generation, and local WebRTC screen mirroring.
"""

from typing import Dict, Any, Optional

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.proactive_bus import (
    ProactiveGetBusStatusArgs,
    ProactiveIngestEventArgs,
    AmbientTriggerAudioCueArgs,
    WebRTCInitMirrorSessionArgs,
    WebRTCTerminateMirrorArgs,
)
from services.backend.proactive.event_bus import proactive_event_bus
from services.backend.ambient.feedback_synthesizer import ambient_feedback_synthesizer
from services.backend.ambient.webrtc_mirror import local_webrtc_mirror


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="proactive_get_bus_status",
    tier=0,
    description="Queries proactive sensory event bus status, privacy scrubbing metrics, and recent events (Read-Only)",
    args_schema=ProactiveGetBusStatusArgs,
    preview_fn=lambda a: "Inspect proactive sensory event bus status and privacy scrubber metrics (Read-Only)",
)
def proactive_get_bus_status(**kwargs) -> Dict[str, Any]:
    """Inspect event bus status and scrubbing telemetry."""
    status = proactive_event_bus.get_status()
    active_webrtc = len(local_webrtc_mirror.get_active_sessions())
    data = status.model_dump()
    data["active_webrtc_sessions"] = active_webrtc
    return {
        "status": "success",
        "bus_status": data,
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

@registry.register(
    name="proactive_ingest_event",
    tier=1,
    description="Ingests a Win32 system context event with automatic real-time privacy scrubbing (Reversible change with preview)",
    args_schema=ProactiveIngestEventArgs,
    preview_fn=lambda a: (
        f"Ingest Win32 context event: {a.get('event_type') if isinstance(a, dict) else getattr(a, 'event_type', '')} "
        f"from {a.get('process_name', 'system') if isinstance(a, dict) else getattr(a, 'process_name', 'system')}"
    ),
)
def proactive_ingest_event(
    event_type: str,
    process_name: str = "system",
    pid: int = 0,
    window_title: str = "",
    details: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Ingest and scrub a system event."""
    if guardian.is_halted or proactive_event_bus.is_halted():
        raise PermissionError("Event bus operations halted by Guardian kill switch.")

    event = proactive_event_bus.ingest_event(
        event_type=event_type,
        process_name=process_name,
        pid=pid,
        window_title=window_title,
        details=details,
    )
    return {
        "status": "success",
        "event": event.model_dump(),
    }


@registry.register(
    name="ambient_trigger_audio_cue",
    tier=1,
    description="Generates and plays a subtle ambient spatial audio cue (Reversible change with preview)",
    args_schema=AmbientTriggerAudioCueArgs,
    preview_fn=lambda a: (
        f"Play ambient audio cue '{a.get('cue_type') if isinstance(a, dict) else getattr(a, 'cue_type', '')}' "
        f"(pan={a.get('spatial_pan', 0.0) if isinstance(a, dict) else getattr(a, 'spatial_pan', 0.0)})"
    ),
)
def ambient_trigger_audio_cue(
    cue_type: str,
    spatial_pan: float = 0.0,
    volume: float = 0.5,
    **kwargs,
) -> Dict[str, Any]:
    """Trigger procedural ambient audio cue."""
    if guardian.is_halted or ambient_feedback_synthesizer.is_halted():
        raise PermissionError("Audio feedback operations halted by Guardian kill switch.")

    payload = ambient_feedback_synthesizer.trigger_cue(
        cue_type=cue_type,
        spatial_pan=spatial_pan,
        volume=volume,
    )
    return {
        "status": "success",
        "audio_cue": payload.model_dump(),
    }


@registry.register(
    name="webrtc_init_mirror_session",
    tier=1,
    description="Initializes a local WebRTC screen mirror stream to a paired companion device (Reversible change with preview)",
    args_schema=WebRTCInitMirrorSessionArgs,
    preview_fn=lambda a: (
        f"Establish local WebRTC screen mirror session to companion device '{a.get('device_id') if isinstance(a, dict) else getattr(a, 'device_id', '')}' "
        f"({a.get('resolution', '1280x720') if isinstance(a, dict) else getattr(a, 'resolution', '1280x720')} @ {a.get('fps_target', 30) if isinstance(a, dict) else getattr(a, 'fps_target', 30)}fps)"
    ),
)
def webrtc_init_mirror_session(
    device_id: str,
    fps_target: int = 30,
    resolution: str = "1280x720",
    **kwargs,
) -> Dict[str, Any]:
    """Initialize local WebRTC mirror session."""
    if guardian.is_halted or local_webrtc_mirror.is_halted():
        raise PermissionError("WebRTC mirror operations halted by Guardian kill switch.")

    session = local_webrtc_mirror.init_session(
        device_id=device_id,
        fps_target=fps_target,
        resolution=resolution,
    )
    return {
        "status": "success",
        "session": session.model_dump(),
    }


@registry.register(
    name="webrtc_terminate_mirror",
    tier=1,
    description="Terminates an active local WebRTC mirror streaming session (Reversible change with preview)",
    args_schema=WebRTCTerminateMirrorArgs,
    preview_fn=lambda a: (
        f"Terminate local WebRTC mirror session '{a.get('session_id') if isinstance(a, dict) else getattr(a, 'session_id', '')}'"
    ),
)
def webrtc_terminate_mirror(
    session_id: str,
    **kwargs,
) -> Dict[str, Any]:
    """Terminate WebRTC mirror session."""
    if guardian.is_halted or local_webrtc_mirror.is_halted():
        raise PermissionError("WebRTC mirror operations halted by Guardian kill switch.")

    terminated = local_webrtc_mirror.terminate_session(session_id=session_id)
    return {
        "status": "success" if terminated else "not_found",
        "session_id": session_id,
        "terminated": terminated,
    }
