"""
Proactive Sensory Event Bus & Ambient Feedback Fabric Schemas (PRX-01, FBK-01, SAF-01, SAF-02).
Defines Pydantic v2 models for:
- Win32 system events (focus changes, crashes, terminal error codes, dialogs)
- Privacy scrubbing status and redacted field tracking
- Ambient spatial audio cue configurations and tone synthesis
- Local WebRTC mirror signaling sessions for companion devices
- Tool argument schemas for proactive event injection and feedback
"""

import time
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class Win32EventType(str, Enum):
    FOCUS_CHANGE = "FOCUS_CHANGE"
    WINDOW_CRASH = "WINDOW_CRASH"
    TERMINAL_ERROR_CODE = "TERMINAL_ERROR_CODE"
    EXCEPTION_DIALOG = "EXCEPTION_DIALOG"
    BACKGROUND_MILESTONE = "BACKGROUND_MILESTONE"
    SYSTEM_ALERT = "SYSTEM_ALERT"


class AudioCueType(str, Enum):
    SUBTLE_CHIME = "SUBTLE_CHIME"
    MILESTONE_FANFARE = "MILESTONE_FANFARE"
    RISK_GATE_WARNING = "RISK_GATE_WARNING"
    GUARDIAN_HALT_BUZZ = "GUARDIAN_HALT_BUZZ"
    DREAM_CYCLE_START = "DREAM_CYCLE_START"
    DREAM_CYCLE_COMPLETE = "DREAM_CYCLE_COMPLETE"


class Win32EventPayload(BaseModel):
    """Event received from Win32 UI Automation, hooks, or terminal monitors."""
    model_config = ConfigDict(use_enum_values=True)

    event_id: str = Field(..., description="Unique event identifier")
    event_type: Win32EventType = Field(..., description="Classification of the system event")
    process_name: str = Field(default="", description="Process executable originating the event")
    pid: int = Field(default=0, description="Process ID")
    window_title: str = Field(default="", description="Sanitized window title")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event-specific metadata or payload")
    timestamp: float = Field(default_factory=time.time, description="Event occurrence epoch timestamp")
    is_scrubbed: bool = Field(default=False, description="Whether event text was sanitized by PrivacyScrubber")
    scrubbed_fields: List[str] = Field(default_factory=list, description="Fields where sensitive tokens were redacted")


class AudioCuePayload(BaseModel):
    """Audio cue configuration for ambient spatial sound generation."""
    model_config = ConfigDict(use_enum_values=True)

    cue_id: str = Field(..., description="Unique audio cue invocation ID")
    cue_type: AudioCueType = Field(..., description="Type of ambient sound")
    frequency_hz: float = Field(default=440.0, description="Base frequency in Hz")
    duration_ms: int = Field(default=250, description="Sound duration in milliseconds")
    volume: float = Field(default=0.5, ge=0.0, le=1.0, description="Audio volume level")
    spatial_pan: float = Field(default=0.0, ge=-1.0, le=1.0, description="Stereo pan: -1.0 (left), 0.0 (center), 1.0 (right)")
    timestamp: float = Field(default_factory=time.time, description="Creation epoch timestamp")


class WebRTCMirrorSession(BaseModel):
    """Local WebRTC screen/canvas mirror session for companion devices."""
    model_config = ConfigDict(use_enum_values=True)

    session_id: str = Field(..., description="Unique WebRTC session ID")
    device_id: str = Field(..., description="Paired companion device ID")
    is_connected: bool = Field(default=False, description="Whether peer connection is active")
    fps_target: int = Field(default=30, description="Target frame rate")
    resolution: str = Field(default="1280x720", description="Streaming resolution")
    local_only: bool = Field(default=True, description="Strict local network enforcement")
    ice_candidates_count: int = Field(default=0, description="Exchanged ICE candidate count")
    created_at: float = Field(default_factory=time.time, description="Session establishment timestamp")


class ProactiveBusStatus(BaseModel):
    """Overall status and telemetry of the proactive sensory event bus."""
    model_config = ConfigDict(use_enum_values=True)

    is_running: bool = Field(default=True, description="Whether event bus is actively listening")
    is_halted: bool = Field(default=False, description="Whether event bus is halted by Guardian")
    total_events_ingested: int = Field(default=0, description="Lifetime ingested events count")
    total_events_scrubbed: int = Field(default=0, description="Events that had sensitive content redacted")
    active_subscriptions: int = Field(default=0, description="Count of active event subscribers")
    recent_events: List[Win32EventPayload] = Field(default_factory=list, description="Recently buffered events")
    active_webrtc_sessions: int = Field(default=0, description="Count of active local WebRTC mirror streams")


# ==========================================
# Tool Argument Schemas (SAF-01)
# ==========================================

class ProactiveGetBusStatusArgs(BaseModel):
    """Arguments for querying proactive sensory event bus status (Tier 0)."""
    model_config = ConfigDict(extra="forbid")


class ProactiveIngestEventArgs(BaseModel):
    """Arguments for manually or programmatically ingesting a system event (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(..., description="Event type: FOCUS_CHANGE, WINDOW_CRASH, TERMINAL_ERROR_CODE, EXCEPTION_DIALOG, BACKGROUND_MILESTONE, SYSTEM_ALERT")
    process_name: str = Field(default="system", description="Process originating the event")
    pid: int = Field(default=0, description="Process ID")
    window_title: str = Field(default="", description="Window title associated with the event")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details or error information")


class AmbientTriggerAudioCueArgs(BaseModel):
    """Arguments for triggering an ambient spatial audio cue (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    cue_type: str = Field(..., description="Cue type: SUBTLE_CHIME, MILESTONE_FANFARE, RISK_GATE_WARNING, GUARDIAN_HALT_BUZZ, DREAM_CYCLE_START, DREAM_CYCLE_COMPLETE")
    spatial_pan: float = Field(default=0.0, ge=-1.0, le=1.0, description="Spatial pan from -1.0 (left) to 1.0 (right)")
    volume: float = Field(default=0.5, ge=0.0, le=1.0, description="Volume level (0.0 to 1.0)")


class WebRTCInitMirrorSessionArgs(BaseModel):
    """Arguments for establishing a local WebRTC mirror session (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(..., description="Target companion device ID")
    fps_target: int = Field(default=30, ge=10, le=60, description="Streaming frame rate")
    resolution: str = Field(default="1280x720", description="Target video stream resolution")


class WebRTCTerminateMirrorArgs(BaseModel):
    """Arguments for terminating an active WebRTC mirror session (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="Session identifier to disconnect")
