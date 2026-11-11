"""Unit test suite for Local Expressive Neural Voice Synthesis & Offline Zero-Shot Jarvis Voice Engine (Milestone 31 Phase 2).

Tests:
- Dynamic emotional modulation parameters and prosody presets (VOX-01.1, VOX-01.2).
- Non-verbal token parsing and acoustic cues (laughter, sigh, pause) (VOX-01.2).
- Low-latency streaming sentence buffering and TTFA < 250ms SLA (EXPR-02.1).
- Acoustic barge-in interruption with < 15.0ms halt SLA (EXPR-02.2).
- Strict Rule 8 anti-checkout enforcement.
- Rule 11 credential protection and sensitive token redaction.
- Guardian kill switch SLA < 25.0ms (Rule 3).
- Safety ToolRegistry registration and risk tiers (Tier 1 & Tier 0).
"""

from __future__ import annotations

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.voice.expressive_voice_engine import (
    ExpressiveVoiceEngine,
    EmotionStyle,
    Rule8ViolationError,
)
import services.backend.tools.expressive_voice_tools  # noqa: F401


@pytest.fixture(autouse=True)
def clean_guardian_and_engine():
    """Ensures guardian is resumed and expressive voice engine is reset before and after each test."""
    guardian.resume()
    engine = ExpressiveVoiceEngine()
    engine.purge_buffer()
    yield engine
    guardian.resume()


def test_emotional_modulation_parameters(clean_guardian_and_engine):
    """VOX-01.1 & VOX-01.2: Verify prosody parameters adapt to active emotion styles."""
    engine = clean_guardian_and_engine

    # Witty banter
    witty_prosody = engine.set_emotion_style(EmotionStyle.WITTY_BANTER)
    assert engine.active_emotion == EmotionStyle.WITTY_BANTER
    assert witty_prosody.rate_offset == 2
    assert witty_prosody.pitch_semitones == 1.2
    assert witty_prosody.cadence == "playful"
    assert witty_prosody.expressiveness > 1.0

    # Technical reasoning
    tech_prosody = engine.set_emotion_style(EmotionStyle.TECHNICAL_REASONING)
    assert tech_prosody.rate_offset == 0
    assert tech_prosody.pitch_semitones == 0.0
    assert tech_prosody.cadence == "measured"

    # Urgent warning
    warning_prosody = engine.set_emotion_style(EmotionStyle.URGENT_WARNING)
    assert warning_prosody.rate_offset == 3
    assert warning_prosody.pitch_semitones == 2.0
    assert warning_prosody.cadence == "crisp_staccato"

    # Empathic calm
    calm_prosody = engine.set_emotion_style(EmotionStyle.EMPATHIC_CALM)
    assert calm_prosody.rate_offset == -1
    assert calm_prosody.pitch_semitones == -0.8
    assert calm_prosody.cadence == "gentle"


def test_non_verbal_token_parsing(clean_guardian_and_engine):
    """VOX-01.2: Verify extraction of acoustic non-verbal tags and pause intervals."""
    engine = clean_guardian_and_engine
    raw_text = "System diagnostics complete [chuckle]. Matrix is fully aligned [pause:300ms], but check CPU thermals [sigh]."

    clean_text, events = engine.parse_non_verbal_tokens(raw_text)
    assert "[chuckle]" in clean_text
    assert "[sigh]" in clean_text
    assert "..." in clean_text
    assert len(events) == 3

    # Check parsed events
    event_types = [e["type"] for e in events]
    assert "ACOUSTIC_CUE" in event_types
    assert "PAUSE" in event_types

    pause_event = next(e for e in events if e["type"] == "PAUSE")
    assert pause_event["duration_ms"] == 300


def test_streaming_sentence_buffering_and_ttfa(clean_guardian_and_engine):
    """EXPR-02.1: Verify streaming sentence segmentation and TTFA < 250ms SLA."""
    engine = clean_guardian_and_engine

    # Chunk 1: Incomplete sentence -> buffered
    s1 = engine.feed_streaming_tokens("Good afternoon, ")
    assert len(s1) == 0

    # Chunk 2: Sentence completed -> yielded
    s2 = engine.feed_streaming_tokens("sir. ")
    assert len(s2) == 1
    assert s2[0] == "Good afternoon, sir."

    # Chunk 3: Multiple sentences
    s3 = engine.feed_streaming_tokens("All engines online! Next task?")
    assert len(s3) == 2
    assert s3[0] == "All engines online!"
    assert s3[1] == "Next task?"

    # Synthesis TTFA benchmark
    t0 = time.perf_counter()
    res = engine.synthesize(
        "Initiating full diagnostic scan across memory sectors.",
        style=EmotionStyle.WITTY_BANTER,
        simulate_playback=True,
    )
    total_ms = (time.perf_counter() - t0) * 1000.0

    assert res.success is True
    assert res.status == "SYNTHESIZED"
    assert res.ttfa_ms < 250.0, f"TTFA {res.ttfa_ms:.3f}ms exceeded 250ms SLA"
    assert total_ms < 250.0


def test_barge_in_interruption_sla(clean_guardian_and_engine):
    """EXPR-02.2: Verify acoustic barge-in halts speech and clears buffers in < 15.0ms."""
    engine = clean_guardian_and_engine
    engine.feed_streaming_tokens("Long streaming sentence currently in transit to audio buffer")

    # Trigger acoustic barge-in
    t0 = time.perf_counter()
    halt_ms = engine.interrupt_speech()
    total_elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert halt_ms < 15.0, f"Barge-in halt latency {halt_ms:.3f}ms exceeded 15.0ms SLA"
    assert total_elapsed_ms < 15.0
    assert engine.total_barge_ins == 1

    # Buffer must be purged immediately
    status = engine.purge_buffer()
    assert status["status"] == "PURGED"
    assert len(engine._token_buffer) == 0


def test_rule_8_anti_checkout_rejection(clean_guardian_and_engine):
    """Rule 8: Anti-checkout enforcement rejects payment/billing speech directives."""
    engine = clean_guardian_and_engine

    checkout_phrases = [
        "Please checkout my Amazon cart now.",
        "Authorize payment for $49.99 immediately.",
        "Submit credit card details for billing.",
        "Complete this purchase.",
    ]

    for phrase in checkout_phrases:
        with pytest.raises(Rule8ViolationError):
            engine.synthesize(phrase, simulate_playback=True)

        with pytest.raises(Rule8ViolationError):
            engine.feed_streaming_tokens(phrase)


def test_rule_11_credential_protection(clean_guardian_and_engine):
    """Rule 11: Scrubbing sensitive API keys, tokens, and passwords before synthesis."""
    engine = clean_guardian_and_engine

    sensitive_text = "Logging in with api_key: sk-proj-1234567890abcdef12345678 and token: auth-token-9876543210"
    scrubbed, count = engine.scrub_credentials(sensitive_text)
    assert count == 2
    assert "sk-proj" not in scrubbed
    assert "auth-token" not in scrubbed
    assert "[REDACTED]" in scrubbed

    res = engine.synthesize(sensitive_text, simulate_playback=True)
    assert "sk-proj" not in res.text
    assert "[REDACTED]" in res.text


def test_guardian_kill_switch_sla(clean_guardian_and_engine):
    """Rule 3: Guardian kill switch halts expressive voice engine with SLA < 25.0ms."""
    engine = clean_guardian_and_engine

    # Trip guardian
    t0 = time.perf_counter()
    guardian.trigger("Emergency acoustic halt")
    trip_latency_ms = (time.perf_counter() - t0) * 1000.0
    assert trip_latency_ms < 25.0

    # Engine must halt immediately
    t1 = time.perf_counter()
    with pytest.raises(RuntimeError, match="Execution halted by Guardian kill switch"):
        engine.synthesize("Welcome back, sir.", simulate_playback=True)
    check_latency_ms = (time.perf_counter() - t1) * 1000.0

    assert check_latency_ms < 25.0, f"Guardian SLA {check_latency_ms:.3f}ms exceeded 25.0ms"


def test_tool_registry_and_tiers():
    """Verify all 4 expressive voice tools are registered with correct Safety tiers."""
    speak_tool = registry.get("synthesize_expressive_speech")
    style_tool = registry.get("set_voice_emotion_style")
    metrics_tool = registry.get("get_expressive_voice_metrics")
    purge_tool = registry.get("purge_expressive_voice_buffer")

    assert speak_tool is not None
    assert speak_tool.tier == 1  # Tier 1 confirmation required

    assert style_tool is not None
    assert style_tool.tier == 1  # Tier 1 configuration

    assert metrics_tool is not None
    assert metrics_tool.tier == 0  # Tier 0 read-only

    assert purge_tool is not None
    assert purge_tool.tier == 0  # Tier 0 safe reset
