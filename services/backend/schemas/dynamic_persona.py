"""Pydantic v2 schemas for Dynamic Persona Modulation & Acoustic Emotion Perception.

Phase 48-04: PERSONA-01, PERSONA-02, PERSONA-03.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EmotionalState(str, Enum):
    """Classified emotional and vocal urgency state of the operator."""
    CALM = "calm"
    CONVERSATIONAL = "conversational"
    URGENT = "urgent"
    FRUSTRATED = "frustrated"


class PersonaCadenceMode(str, Enum):
    """Dynamic speech cadence and personality style modes for Jarvis."""
    PLAYFUL_JARVIS = "playful_jarvis"
    COLLABORATIVE_PARTNER = "collaborative_partner"
    CRITICAL_INCIDENT = "critical_incident"
    EMPATHETIC_COPILOT = "empathetic_copilot"


class AcousticFeatures(BaseModel):
    """Vocal prosody and acoustic characteristics extracted from raw audio."""
    pitch_mean_hz: float = Field(default=120.0, ge=40.0, le=500.0)
    pitch_variance: float = Field(default=25.0, ge=0.0)
    energy_rms: float = Field(default=1000.0, ge=0.0)
    speech_rate_wpm: float = Field(default=140.0, ge=40.0, le=350.0)
    duration_sec: float = Field(default=1.0, ge=0.0)
    detected_emotion: EmotionalState = Field(default=EmotionalState.CONVERSATIONAL)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class PersonaStyleProfile(BaseModel):
    """Active personality and TTS speech synthesis parameters."""
    cadence_mode: PersonaCadenceMode
    speech_rate_multiplier: float = Field(default=1.0, ge=0.7, le=1.6)
    pitch_shift_semitones: float = Field(default=0.0, ge=-4.0, le=4.0)
    humor_level: float = Field(default=0.8, ge=0.0, le=1.0, description="0.0 = zero banter, 1.0 = witty Jarvis")
    brevity_score: float = Field(default=0.5, ge=0.0, le=1.0, description="1.0 = terse/surgical, 0.0 = elaborate")
    system_prompt_modifier: str = Field(default="")


class SpokenMilestoneBriefing(BaseModel):
    """A brief, concise spoken notification for swarm progress or alerts."""
    briefing_id: str
    event_type: str = Field(..., description="handoff, quorum, complete, or alert")
    text: str = Field(..., description="Spoken text guaranteed to be under 25 words")
    urgency: int = Field(default=1, ge=1, le=5)
    audio_earcon: str = Field(default="chime_success.wav")
    timestamp: float = Field(default_factory=time.time)
