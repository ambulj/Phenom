"""
Pydantic Schemas for Full-Duplex Voice Engine & Streaming Whisper
Milestone 43.0: Project FULL-DUPLEX JARVIS
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DuplexVoiceState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    USER_SPEAKING = "USER_SPEAKING"
    PROCESSING = "PROCESSING"
    AGENT_SPEAKING = "AGENT_SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    HALTED = "HALTED"


class AudioFramePayload(BaseModel):
    chunk_index: int = Field(default=0, description="Sequential chunk index")
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    samples_count: int = Field(default=512, description="Number of samples in chunk")
    rms_energy: float = Field(default=0.0, description="Root mean square energy level")
    speech_probability: float = Field(default=0.0, description="Silero VAD speech probability [0.0 - 1.0]")
    is_speech: bool = Field(default=False, description="True if probability exceeds threshold")


class SpeechOnsetEvent(BaseModel):
    onset_timestamp: float = Field(description="Epoch timestamp of speech onset")
    detection_latency_ms: float = Field(description="Latency between audio arrival and VAD trigger in milliseconds")
    consecutive_chunks: int = Field(description="Number of consecutive speech chunks confirming onset")
    initial_rms: float = Field(description="Audio energy at speech onset")


class SpeechTranscriptionResult(BaseModel):
    transcript: str = Field(default="", description="Transcribed text string")
    is_final: bool = Field(default=False, description="True if end-of-utterance detected")
    duration_seconds: float = Field(default=0.0, description="Audio utterance duration")
    total_chunks: int = Field(default=0, description="Total 512-sample chunks transcribed")
    latency_ms: float = Field(default=0.0, description="Transcription latency in milliseconds")
    confidence: float = Field(default=1.0, description="Transcription confidence score [0.0 - 1.0]")


class DuplexTelemetry(BaseModel):
    state: DuplexVoiceState = Field(default=DuplexVoiceState.IDLE, description="Current turn-taking state")
    is_active: bool = Field(default=True, description="True if duplex engine is active")
    active: bool = Field(default=True, description="Backwards compatible active flag")
    is_muted: bool = Field(default=False, description="True if microphone is muted")
    muted: bool = Field(default=False, description="Backwards compatible muted flag")
    is_halted: bool = Field(default=False, description="True if Guardian kill switch is active")
    halted: bool = Field(default=False, description="Backwards compatible halted flag")
    user_speaking: bool = Field(default=False, description="True if user is actively speaking")
    ring_buffer_chunks: int = Field(default=0, description="Current audio chunks in RAM ring buffer")
    max_ring_buffer_chunks: int = Field(default=300, description="Max allowed ring buffer capacity")
    total_utterances: int = Field(default=0, description="Total completed user speech utterances")
    total_barge_ins: int = Field(default=0, description="Total acoustic barge-in interruptions")
    last_barge_in_latency_ms: float = Field(default=0.0, description="Latency of most recent barge-in interrupt")
    speech_threshold: float = Field(default=0.50, description="VAD threshold for speech detection")
