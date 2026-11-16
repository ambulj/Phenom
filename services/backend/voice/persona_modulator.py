"""Dynamic Persona Modulator for Phenom Voice.

Phase 48-04: PERSONA-02.
Adapts Jarvis wit, speech pacing, brevity, and prompt framing in real time based on
the operator's detected vocal prosody and emotional urgency.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Optional

from services.backend.schemas.dynamic_persona import (
    EmotionalState,
    PersonaCadenceMode,
    PersonaStyleProfile,
)

logger = logging.getLogger("phenom.voice.persona_modulator")


class DynamicPersonaModulator:
    """Modulates Jarvis persona parameters dynamically in response to emotional urgency."""

    CONVERSATIONAL_FILLERS = [
        r"\b(?:hello|hi|hey)(?:\s+there)?\b\s*[,.]?\s*",
        r"\b(?:sure|certainly|absolutely|of\s+course)\b\s*[,.]?\s*",
        r"\b(?:sir|ma'?am)\b\s*[!.,]?\s*",
        r"\b(?:i(?:'d|\s+would|\s+am)?\s+(?:be\s+)?(?:happy|delighted|pleased)\s+to\s+help(?:\s+you)?(?:\s+with\s+that)?)\b\s*[,.]?\s*",
        r"\b(?:allow\s+me\s+to\s+inform\s+you\s+that)\b\s*",
        r"\b(?:right\s+away|as\s+you\s+wish)\b\s*[,.]?\s*",
    ]

    _PROFILES: Dict[EmotionalState, PersonaStyleProfile] = {
        EmotionalState.CALM: PersonaStyleProfile(
            cadence_mode=PersonaCadenceMode.PLAYFUL_JARVIS,
            speech_rate_multiplier=1.0,
            pitch_shift_semitones=0.0,
            humor_level=0.85,
            brevity_score=0.5,
            system_prompt_modifier=(
                "Adopt a witty, playful British Jarvis persona. Employ subtle dry humor, "
                "address the user politely, and maintain an effortless, intelligent demeanor."
            ),
        ),
        EmotionalState.CONVERSATIONAL: PersonaStyleProfile(
            cadence_mode=PersonaCadenceMode.PLAYFUL_JARVIS,
            speech_rate_multiplier=1.0,
            pitch_shift_semitones=0.0,
            humor_level=0.75,
            brevity_score=0.55,
            system_prompt_modifier=(
                "Adopt an intelligent Jarvis tone. Balanced, witty, concise, and focused on collaborative execution."
            ),
        ),
        EmotionalState.URGENT: PersonaStyleProfile(
            cadence_mode=PersonaCadenceMode.CRITICAL_INCIDENT,
            speech_rate_multiplier=1.2,
            pitch_shift_semitones=0.5,
            humor_level=0.0,
            brevity_score=1.0,
            system_prompt_modifier=(
                "CRITICAL INCIDENT MODE: The operator is in a high-urgency situation. "
                "Suppress all humor, pleasantries, conversational fillers, and commentary. "
                "State only facts, actions taken, and immediate next steps with surgical brevity."
            ),
        ),
        EmotionalState.FRUSTRATED: PersonaStyleProfile(
            cadence_mode=PersonaCadenceMode.EMPATHETIC_COPILOT,
            speech_rate_multiplier=1.05,
            pitch_shift_semitones=-0.5,
            humor_level=0.1,
            brevity_score=0.8,
            system_prompt_modifier=(
                "The operator is experiencing friction or frustration. "
                "Be calm, reassuring, and direct. Acknowledge the issue concisely and execute remedies without hesitation."
            ),
        ),
    }

    @classmethod
    def get_profile_for_emotion(cls, emotion: EmotionalState) -> PersonaStyleProfile:
        """Retrieve dynamic speech synthesis and prompt profile for an emotional state."""
        return cls._PROFILES.get(emotion, cls._PROFILES[EmotionalState.CONVERSATIONAL])

    @classmethod
    def format_system_prompt_prefix(cls, profile: PersonaStyleProfile) -> str:
        """Generate system prompt framing based on active cadence mode."""
        return f"[PERSONA: {profile.cadence_mode.value.upper()}]\n{profile.system_prompt_modifier}"

    @classmethod
    def format_response_text(cls, raw_text: str, profile: PersonaStyleProfile) -> str:
        """Adjust and filter output text according to brevity and cadence constraints."""
        text = raw_text.strip()

        # In CRITICAL_INCIDENT mode, strip all pleasantries and fillers
        if profile.cadence_mode == PersonaCadenceMode.CRITICAL_INCIDENT:
            for pattern in cls.CONVERSATIONAL_FILLERS:
                text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
            # Capitalize first character if needed
            if text:
                text = text[0].upper() + text[1:]

        return text
