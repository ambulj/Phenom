"""Pydantic v2 schemas for Real-Time Full-Duplex Voice Engine & Barge-In Soft-Mute.

Phase 48-03: VOICE-01, VOICE-02, VOICE-03.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DuplexStreamState(str, Enum):
    """Lifecycle states of the bi-directional audio duplex pipeline."""
    IDLE = "idle"
    LISTENING = "listening"
    USER_SPEAKING = "user_speaking"
    PROCESSING = "processing"
    AGENT_SPEAKING = "agent_speaking"
    SOFT_MUTED = "soft_muted"


class BargeInType(str, Enum):
    """Classification of user vocal interruption during active operations."""
    EMERGENCY_HALT = "emergency_halt"
    STEERING_GUIDANCE = "steering_guidance"
    CORRECTION = "correction"
    CONVERSATIONAL = "conversational"


class BargeInEvent(BaseModel):
    """Telemetry record for an acoustic user interruption."""
    event_id: str
    detected_at: float = Field(default_factory=time.time)
    latency_ms: float = Field(..., ge=0.0, description="Elapsed time from speech onset to soft-mute in ms")
    tts_attenuated: bool = Field(default=True)
    transcript: Optional[str] = None
    barge_in_type: BargeInType = Field(default=BargeInType.CONVERSATIONAL)
    injected_guidance: Optional[str] = None
    swarm_continued: bool = Field(default=True, description="True if background swarm execution was preserved")


class DuplexAudioMetrics(BaseModel):
    """Real-time latency and state telemetry for the full-duplex stream."""
    roundtrip_latency_ms: float = Field(default=0.0, ge=0.0)
    vad_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    tts_playing: bool = Field(default=False)
    user_speaking: bool = Field(default=False)
    soft_muted: bool = Field(default=False)
    total_barge_ins: int = Field(default=0, ge=0)
    last_barge_in_ms: float = Field(default=0.0)
    state: DuplexStreamState = Field(default=DuplexStreamState.IDLE)


class SwarmGuidanceInjection(BaseModel):
    """A high-priority user directive injected dynamically into the active swarm."""
    injection_id: str
    target_task_id: Optional[str] = None
    priority: int = Field(default=10, description="High priority for immediate steering")
    guidance_text: str
    barge_in_type: BargeInType
    created_at: float = Field(default_factory=time.time)
    applied: bool = Field(default=False)
