from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class VoiceKernelState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    DISPATCHING = "dispatching"
    BARGED_IN = "barged_in"
    HALTED = "halted"


class IntentType(str, Enum):
    TOOL_CALL = "tool_call"
    SYSTEM_COMMAND = "system_command"
    QUERY = "query"
    INTERRUPTION = "interruption"
    UNKNOWN = "unknown"


class VoiceChunkMetadata(BaseModel):
    chunk_id: str
    rms_energy: float = Field(..., ge=0.0, le=1.0)
    speech_prob: float = Field(..., ge=0.0, le=1.0)
    duration_ms: float = Field(..., ge=0.0)
    timestamp: float


class DispatchedActionRecord(BaseModel):
    action_id: str
    raw_transcript: str
    matched_intent: IntentType
    tool_name: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    latency_ms: float = Field(..., ge=0.0)
    status: str
    timestamp: float


class VoiceActionKernelStatus(BaseModel):
    state: VoiceKernelState
    is_listening: bool
    noise_floor_rms: float
    vad_threshold: float
    active_session_id: Optional[str] = None
    total_dispatched: int
    recent_actions: List[DispatchedActionRecord] = []


class VoiceKernelGetStatusArgs(BaseModel):
    session_id: Optional[str] = None


class VoiceKernelConfigureArgs(BaseModel):
    vad_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="VAD speech probability threshold")
    noise_floor_rms: Optional[float] = Field(None, ge=0.0, le=1.0, description="Calibrated ambient noise floor RMS")
    barge_in_sensitivity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Barge-in interruption sensitivity")


class VoiceKernelSimulateChunkArgs(BaseModel):
    rms_energy: float = Field(..., ge=0.0, le=1.0, description="Acoustic RMS energy of the chunk")
    speech_prob: float = Field(..., ge=0.0, le=1.0, description="Silero VAD speech probability")
    transcript_text: Optional[str] = Field(None, description="Simulated transcribed speech text")


class VoiceKernelAbortIntentArgs(BaseModel):
    action_id: str = Field(..., description="Unique ID of the dispatched voice action to abort")
