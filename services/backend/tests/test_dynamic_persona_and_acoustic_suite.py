"""Comprehensive Unit Test Suite for Dynamic Persona Modulation & Acoustic Emotion Perception.

Phase 48-04: PERSONA-01, PERSONA-02, PERSONA-03.
Tests acoustic prosody feature extraction, emotion classification (calm, conversational, urgent, frustrated),
dynamic Jarvis persona adaptation, concise spoken milestone briefings (<25 words), and ToolRegistry tools.
"""

import pytest
import numpy as np
from typing import Dict, Any

from services.backend.schemas.dynamic_persona import (
    EmotionalState,
    PersonaCadenceMode,
    AcousticFeatures,
    PersonaStyleProfile,
    SpokenMilestoneBriefing,
)
from services.backend.voice.acoustic_analyzer import AcousticProsodyAnalyzer
from services.backend.voice.persona_modulator import DynamicPersonaModulator
from services.backend.voice.proactive_cues import SpokenHandoffNotifier
import services.backend.tools.persona_tools
from services.backend.safety.registry import registry


# ============================================================================
# 1. Dynamic Persona Schemas Validation
# ============================================================================

def test_dynamic_persona_schemas():
    """Verify enum states, defaults, and model serialization."""
    features = AcousticFeatures(
        pitch_mean_hz=145.0,
        pitch_variance=38.2,
        energy_rms=1540.0,
        speech_rate_wpm=155.0,
        detected_emotion=EmotionalState.CONVERSATIONAL,
    )
    dumped = features.model_dump()
    assert dumped["detected_emotion"] == "conversational"
    assert dumped["energy_rms"] == 1540.0

    profile = PersonaStyleProfile(
        cadence_mode=PersonaCadenceMode.CRITICAL_INCIDENT,
        speech_rate_multiplier=1.25,
        humor_level=0.0,
        brevity_score=1.0,
    )
    assert profile.humor_level == 0.0
    assert profile.brevity_score == 1.0


# ============================================================================
# 2. Acoustic Prosody Analyzer (PERSONA-01)
# ============================================================================

def test_acoustic_prosody_analyzer_classification():
    """Verify classification of emotional states from acoustic values."""
    # 1. Urgent: High energy and high pitch variability
    feat_urgent = AcousticProsodyAnalyzer.classify_from_values(
        energy_rms=2600.0,
        pitch_variance=52.0,
        speech_rate_wpm=175.0,
    )
    assert feat_urgent.detected_emotion == EmotionalState.URGENT
    assert feat_urgent.confidence >= 0.90

    # 2. Frustrated: High energy with flat, tense pitch variability
    feat_frust = AcousticProsodyAnalyzer.classify_from_values(
        energy_rms=2300.0,
        pitch_variance=22.0,
        speech_rate_wpm=140.0,
    )
    assert feat_frust.detected_emotion == EmotionalState.FRUSTRATED

    # 3. Calm: Low energy and low pitch variance
    feat_calm = AcousticProsodyAnalyzer.classify_from_values(
        energy_rms=450.0,
        pitch_variance=12.0,
        speech_rate_wpm=110.0,
    )
    assert feat_calm.detected_emotion == EmotionalState.CALM

    # 4. Conversational: Moderate energy and natural dynamics
    feat_conv = AcousticProsodyAnalyzer.classify_from_values(
        energy_rms=1200.0,
        pitch_variance=28.0,
        speech_rate_wpm=135.0,
    )
    assert feat_conv.detected_emotion == EmotionalState.CONVERSATIONAL


def test_acoustic_prosody_analyzer_raw_audio():
    """Verify feature extraction from raw int16 PCM audio array."""
    # Synthetic speech-like audio (500Hz sine wave with amplitude 1200)
    sample_rate = 16000
    t = np.linspace(0, 1.0, sample_rate)
    sine = (np.sin(2 * np.pi * 500 * t) * 1200).astype(np.int16)

    feat = AcousticProsodyAnalyzer.extract_features(sine, sample_rate=sample_rate)
    assert feat.energy_rms > 500.0
    assert feat.pitch_mean_hz > 50.0
    assert feat.duration_sec == 1.0


# ============================================================================
# 3. Dynamic Persona Modulator (PERSONA-02)
# ============================================================================

def test_dynamic_persona_modulator():
    """Verify humor, brevity, and text adaptation across cadence modes."""
    # 1. Urgent Mode
    p_urgent = DynamicPersonaModulator.get_profile_for_emotion(EmotionalState.URGENT)
    assert p_urgent.cadence_mode == PersonaCadenceMode.CRITICAL_INCIDENT
    assert p_urgent.humor_level == 0.0
    assert p_urgent.brevity_score == 1.0
    assert p_urgent.speech_rate_multiplier >= 1.2

    # Check text formatting: pleasantries stripped
    raw_response = "Certainly, sir! I would be pleased to help you with that. Reverting diff now."
    cleaned = DynamicPersonaModulator.format_response_text(raw_response, p_urgent)
    assert "Certainly" not in cleaned
    assert "pleased to help" not in cleaned
    assert "Reverting diff now." in cleaned

    # 2. Calm / Conversational Mode
    p_calm = DynamicPersonaModulator.get_profile_for_emotion(EmotionalState.CALM)
    assert p_calm.cadence_mode == PersonaCadenceMode.PLAYFUL_JARVIS
    assert p_calm.humor_level >= 0.75
    assert p_calm.brevity_score <= 0.6


# ============================================================================
# 4. Spoken Milestone & Handoff Briefings (PERSONA-03)
# ============================================================================

def test_spoken_milestone_briefings():
    """Verify word limit invariant (<25 words) and formatting for voice cues."""
    # 1. Handoff briefing
    b_handoff = SpokenHandoffNotifier.create_handoff_briefing(
        from_role="architect",
        to_role="coder",
        task_title="isolated workspace patch",
    )
    word_count = len(b_handoff.text.split())
    assert word_count <= 25, f"Word count {word_count} exceeds limit 25"
    assert "Architect handed off to Coder" in b_handoff.text

    # 2. Quorum approved briefing
    b_quorum = SpokenHandoffNotifier.create_quorum_briefing(state="quorum_reached", is_approved=True)
    assert len(b_quorum.text.split()) <= 25
    assert "Two-tier quorum approved" in b_quorum.text
    assert b_quorum.audio_earcon == "chime_quorum_pass.wav"

    # 3. Mission complete briefing
    b_complete = SpokenHandoffNotifier.create_mission_complete_briefing(patch_id="patch_123", file_count=3)
    assert len(b_complete.text.split()) <= 25
    assert "Mission complete, sir" in b_complete.text


# ============================================================================
# 5. Tool Registry Integration & Execution
# ============================================================================

def test_persona_tools_registry():
    """Verify tool registration, tier numbers, preview generation, and execution."""
    tool_analyze = registry.get("analyze_vocal_acoustics")
    tool_modulate = registry.get("modulate_persona_style")
    tool_briefing = registry.get("dispatch_spoken_briefing")

    assert tool_analyze is not None
    assert tool_analyze.tier == 0  # Tier 0 read-only
    assert tool_modulate is not None
    assert tool_modulate.tier == 0  # Tier 0 read-only
    assert tool_briefing is not None
    assert tool_briefing.tier == 1  # Tier 1 audio action

    # Execute analyze_vocal_acoustics
    res_analyze = tool_analyze.handler_fn(energy_rms=2400.0, pitch_variance=50.0, speech_rate_wpm=170.0)
    assert res_analyze["detected_emotion"] == "urgent"

    # Execute modulate_persona_style
    res_mod = tool_modulate.handler_fn(emotion="urgent")
    assert res_mod["cadence_mode"] == "critical_incident"
    assert res_mod["humor_level"] == 0.0

    # Execute dispatch_spoken_briefing
    res_brief = tool_briefing.handler_fn(event_type="handoff", detail_a="architect", detail_b="coder")
    assert "Architect handed off to Coder" in res_brief["text"]
    assert len(res_brief["text"].split()) <= 25
