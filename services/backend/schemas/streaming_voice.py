"""
Pydantic Schemas for Phenom Streaming Conversational Voice Engine
Strict typing for sub-200ms turnaround pipeline, Silero VAD barge-in,
and smart minimalist Jarvis persona policy.
"""

from typing import Optional
from pydantic import BaseModel, Field


class StreamingVoiceConfig(BaseModel):
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz (16kHz standard)")
    chunk_size: int = Field(default=512, description="Number of samples per chunk (32ms at 16kHz)")
    vad_threshold: float = Field(default=0.50, ge=0.0, le=1.0, description="Silero VAD speech probability threshold")
    barge_in_consecutive_chunks: int = Field(default=2, ge=1, le=10, description="Consecutive speech chunks required to trigger barge-in hysteresis")
    silence_turn_end_chunks: int = Field(default=6, ge=2, le=30, description="Consecutive silence chunks to trigger end of user speech (~192ms)")
    persona_mode: str = Field(default="minimalist", description="Persona mode: 'minimalist' or 'conversational'")
    speech_speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech playback speed multiplier")


class StreamingVoiceStatus(BaseModel):
    state: str = Field(..., description="Engine state: idle, listening, thinking, speaking, interrupted, halted")
    turnaround_latency_ms: float = Field(default=0.0, description="Latency from end of speech detection to first audio packet")
    last_barge_in_latency_ms: float = Field(default=0.0, description="Stop latency of the most recent barge-in interruption")
    total_interruptions: int = Field(default=0, description="Total count of barge-in interruptions")
    total_turns: int = Field(default=0, description="Total conversation turns processed")
    is_muted: bool = Field(default=False, description="Whether microphone/voice input is muted")
    active_persona: str = Field(default="minimalist", description="Currently active persona mode")
    is_halted: bool = Field(default=False, description="Whether engine is halted by Guardian kill switch")


class VoiceInterruptionEvent(BaseModel):
    timestamp: float = Field(..., description="Epoch timestamp of interruption")
    latency_ms: float = Field(..., description="Interruption execution latency in milliseconds")
    trigger: str = Field(default="user_speech_vad", description="Trigger mechanism (e.g. user_speech_vad, force_interrupt)")
    audio_offset_ms: float = Field(default=0.0, description="Playback position offset at time of interruption")


class SpontaneousSpeechDecision(BaseModel):
    should_speak: bool = Field(..., description="Whether spontaneous speech is permitted")
    reason: str = Field(..., description="Decision rationale")
    urgency_level: str = Field(default="none", description="Urgency: critical, urgent, security, direct, none")
    suggested_tone: str = Field(default="witty_concise", description="Suggested Jarvis tone")


class VoiceConfigureArgs(BaseModel):
    persona_mode: Optional[str] = Field(
        default=None,
        description="Persona mode to enforce ('minimalist', 'conversational')"
    )
    speech_speed: Optional[float] = Field(
        default=None,
        ge=0.5,
        le=2.0,
        description="Speech playback speed multiplier (0.5 to 2.0)"
    )
    barge_in_sensitivity: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=1.0,
        description="Silero VAD threshold for barge-in detection (0.10 to 1.0)"
    )
    silence_turn_end_chunks: Optional[int] = Field(
        default=None,
        ge=2,
        le=30,
        description="Consecutive silence chunks to trigger end of turn"
    )


class VoiceSpeakArgs(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        description="Spoken utterance text to synthesize and play with Jarvis cadence"
    )
    urgency: Optional[str] = Field(
        default="normal",
        description="Urgency level ('normal', 'urgent', 'critical')"
    )


class VoiceStatusArgs(BaseModel):
    """Schema for voice_get_engine_status (no arguments required)."""
    pass
