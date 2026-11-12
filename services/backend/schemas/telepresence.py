"""
Telepresence and Low-Latency Audio/Video Fabric Schemas.
Pydantic v2 schemas for streaming AV ingestion, ambient room perception,
and hardware privacy controls (Permanent Rule 4).
"""

from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class MediaStreamType(str, Enum):
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    AUDIO_VIDEO = "AUDIO_VIDEO"


class SensorState(str, Enum):
    ACTIVE = "ACTIVE"
    MUTED = "MUTED"
    SHUTTERED = "SHUTTERED"
    DISABLED = "DISABLED"


class AudioMetrics(BaseModel):
    rms_energy: float = Field(0.0, ge=0.0, le=1.0, description="Normalized root-mean-square audio energy")
    peak_volume_db: float = Field(-96.0, description="Peak volume in decibels relative to full scale (dBFS)")
    speech_probability: float = Field(0.0, ge=0.0, le=1.0, description="Estimated voice activity probability")
    sample_rate_hz: int = Field(16000, description="Audio sampling rate in Hz")


class VideoMetrics(BaseModel):
    fps: float = Field(0.0, ge=0.0, description="Current stream frames per second")
    resolution: str = Field("1280x720", description="Active camera stream resolution")
    face_detected: bool = Field(False, description="Whether a face is detected in the field of view")
    landmark_count: int = Field(0, ge=0, description="Number of detected facial/body landmarks")
    zero_frame_retention: bool = Field(True, description="Strict Rule 4 guarantee that raw frames are never stored")


class TelepresenceSessionState(BaseModel):
    session_id: str = Field(..., description="Unique telepresence session identifier")
    is_active: bool = Field(False, description="Whether telepresence pipeline is actively streaming")
    stream_type: MediaStreamType = Field(MediaStreamType.AUDIO_VIDEO, description="Configured media stream type")
    microphone_state: SensorState = Field(SensorState.MUTED, description="Current microphone hardware state")
    camera_state: SensorState = Field(SensorState.SHUTTERED, description="Current camera privacy shutter state")
    audio_metrics: AudioMetrics = Field(default_factory=AudioMetrics)
    video_metrics: VideoMetrics = Field(default_factory=VideoMetrics)
    ambient_presence: bool = Field(False, description="Whether user presence is detected in the room")
    started_at: Optional[float] = Field(None, description="UNIX timestamp when session started")


# =============================================================================
# Tool Argument Models
# =============================================================================

class TelepresenceGetStatusArgs(BaseModel):
    """Arguments for querying current telepresence engine status."""
    pass


class TelepresenceSetMicrophoneArgs(BaseModel):
    """Arguments for controlling microphone hardware state and gain."""
    state: SensorState = Field(..., description="Desired microphone state: ACTIVE or MUTED")
    gain: float = Field(1.0, ge=0.0, le=2.0, description="Software gain multiplier (0.0 to 2.0)")


class TelepresenceSetCameraArgs(BaseModel):
    """Arguments for controlling camera privacy shutter and resolution."""
    state: SensorState = Field(..., description="Desired camera state: ACTIVE or SHUTTERED")
    resolution: str = Field("1280x720", description="Target video resolution, e.g., '1280x720' or '1920x1080'")


class TelepresenceIngestFrameArgs(BaseModel):
    """Arguments for ingesting transient audio-visual telemetry without storing raw media."""
    audio_rms: float = Field(..., ge=0.0, le=1.0, description="Normalized RMS audio energy")
    speech_probability: float = Field(..., ge=0.0, le=1.0, description="VAD speech probability")
    landmarks: List[Tuple[float, float]] = Field(default_factory=list, description="Normalized landmark coordinates")
    timestamp: float = Field(..., description="Sample timestamp")
