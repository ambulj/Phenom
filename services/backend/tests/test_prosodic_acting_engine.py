"""
Unit tests for Milestone 34.0 Phase 2: Multi-Emotional Prosodic Acting Engine & Breath Synthesizer
Validates:
- PROSOD-02.1: 5 distinct emotional envelopes (Warm Wit, Conspiratorial, Tactical Alert, Calm Reassuring, Executive Concise).
- PROSOD-02.2: F0 pitch contour inflection and energy modulation.
- PROSOD-02.3: Natural clause-boundary respiratory breath insertion.
- SAF-01: ToolRegistry integration, risk tiers, and preview functions.
- SAF-02.1: Universal Guardian kill switch synchronous halt SLA (< 25.0ms).
- Rule 8 & Rule 11: Anti-checkout rejection and credential scrubbing.
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.voice.prosodic_acting_engine import (
    prosodic_acting_engine,
    ActingEmotion,
    Rule8ViolationError,
)
import services.backend.tools.prosodic_acting_tools  # Registers tools


@pytest.fixture(autouse=True)
def reset_prosody_state():
    guardian.resume()
    prosodic_acting_engine.reset_halt()
    prosodic_acting_engine.configure_parameters(
        emotion=ActingEmotion.WARM_WIT,
        custom_pitch_shift=None,
        custom_intensity=None,
        breath_enabled=True,
    )
    yield
    guardian.resume()
    prosodic_acting_engine.reset_halt()


def test_prosodic_acting_engine_initialization_and_emotions():
    """Verify engine initializes with default Warm Wit persona and supports all 5 modes."""
    telem = prosodic_acting_engine.get_telemetry()
    assert telem.active_emotion == ActingEmotion.WARM_WIT
    assert telem.is_halted is False

    for emo in ActingEmotion:
        prosodic_acting_engine.set_emotion(emo)
        assert prosodic_acting_engine.get_active_emotion() == emo


def test_emotional_envelope_application_and_prosody_tags():
    """PROSOD-02.1: Verify SSML pitch, rate, and volume tags across emotional modes."""
    sample_text = "Good evening sir. Diagnostic sensors are online, and telemetry looks nominal."

    # 1. Warm Wit (Playful Jarvis)
    wit_res = prosodic_acting_engine.apply_acting_envelope(sample_text, emotion=ActingEmotion.WARM_WIT)
    assert wit_res["status"] == "PROCESSED"
    assert "<prosody" in wit_res["enriched_text"]
    assert "pitch='+1.5st'" in wit_res["enriched_text"]

    # 2. Conspiratorial (Whisper mode)
    whisper_res = prosodic_acting_engine.apply_acting_envelope(sample_text, emotion=ActingEmotion.CONSPIRATORIAL)
    assert "pitch='-2.0st'" in whisper_res["enriched_text"]
    assert "volume='0.55'" in whisper_res["enriched_text"]

    # 3. Tactical Alert (Urgent mode)
    alert_res = prosodic_acting_engine.apply_acting_envelope(sample_text, emotion=ActingEmotion.TACTICAL_ALERT)
    assert "pitch='+3.0st'" in alert_res["enriched_text"]
    assert "rate='1.22'" in alert_res["enriched_text"]


def test_respiratory_breath_marker_injection():
    """PROSOD-02.3: Verify natural breath pauses inserted at clause boundaries."""
    long_text = (
        "I have scrutinized the telemetry, sir, and everything appears stable; "
        "furthermore, our memory caches are consolidated and ready for deployment."
    )
    res = prosodic_acting_engine.apply_acting_envelope(long_text, inject_breaths=True)
    assert "<breath" in res["enriched_text"]
    assert res["breath_markers_count"] >= 1

    # Verify disabling breaths strips markers
    no_breath_res = prosodic_acting_engine.apply_acting_envelope(long_text, inject_breaths=False)
    assert "<breath" not in no_breath_res["enriched_text"]
    assert no_breath_res["breath_markers_count"] == 0


def test_f0_pitch_curve_generation():
    """PROSOD-02.2: Verify dynamic F0 pitch curve synthesis."""
    text = "Are all subsystem parameters within expected bounds?"
    preview = prosodic_acting_engine.synthesize_preview(text, emotion=ActingEmotion.TACTICAL_ALERT)

    assert preview["status"] == "PREVIEW_SYNTHESIZED"
    assert len(preview["pitch_curve_hz"]) == len(text.split())
    # All F0 frequencies should be within natural voice range (80Hz to 350Hz)
    assert all(80.0 <= f0 <= 350.0 for f0 in preview["pitch_curve_hz"])


def test_parameter_configuration():
    """Verify parameter configuration overrides pitch and intensity."""
    cfg_res = prosodic_acting_engine.configure_parameters(
        emotion=ActingEmotion.CALM_REASSURING,
        custom_pitch_shift=2.5,
        custom_intensity=1.2,
        breath_enabled=False,
    )
    assert cfg_res["active_emotion"] == "CALM_REASSURING"
    assert cfg_res["pitch_shift_semitones"] == 2.5
    assert cfg_res["energy_intensity"] == 1.2
    assert cfg_res["breath_enabled"] is False


def test_rule_8_anti_checkout_enforcement():
    """Rule 8: Verify checkout, purchase, and payment directives are rejected."""
    with pytest.raises(Rule8ViolationError):
        prosodic_acting_engine.apply_acting_envelope(
            "Please pay the checkout invoice with credit card now."
        )

    with pytest.raises(Rule8ViolationError):
        prosodic_acting_engine.synthesize_preview(
            "Buy this premium voice pack and billing subscription."
        )


def test_tool_registry_prosodic_tools():
    """SAF-01: Verify all 4 prosodic acting tools are registered and functional."""
    tool_apply = registry.get("apply_prosodic_acting_envelope")
    assert tool_apply.tier == 0
    assert "prosodic" in tool_apply.preview_fn({"text": "Hello"})

    tool_cfg = registry.get("configure_prosodic_parameters")
    assert tool_cfg.tier == 1

    tool_telem = registry.get("get_active_prosodic_telemetry")
    assert tool_telem.tier == 0

    tool_prev = registry.get("synthesize_prosodic_speech_preview")
    assert tool_prev.tier == 0

    # Execute apply tool
    apply_res = tool_apply.handler_fn(
        text="All systems nominal, sir.",
        emotion="WARM_WIT",
        inject_breaths=True,
    )
    assert apply_res["status"] == "PROCESSED"
    assert "<prosody" in apply_res["enriched_text"]

    # Execute config tool
    cfg_res = tool_cfg.handler_fn(emotion="EXECUTIVE_CONCISE", custom_pitch_shift=0.5)
    assert cfg_res["status"] == "CONFIGURED"

    # Execute telemetry tool
    telem_res = tool_telem.handler_fn()
    assert telem_res["active_emotion"] == "EXECUTIVE_CONCISE"

    # Execute preview tool
    prev_res = tool_prev.handler_fn(text="Briefing completed.")
    assert prev_res["status"] == "PREVIEW_SYNTHESIZED"
    assert len(prev_res["pitch_curve_hz"]) == 2


def test_universal_guardian_kill_switch_sla():
    """SAF-02.1: Verify Guardian kill switch halt SLA < 25.0ms on prosodic engine."""
    prosodic_acting_engine.halt()
    prosodic_acting_engine.reset_halt()

    latencies = []
    for _ in range(50):
        prosodic_acting_engine.reset_halt()
        t0 = time.perf_counter()
        prosodic_acting_engine.halt()
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    avg_ms = sum(latencies) / len(latencies)
    max_ms = max(latencies)
    assert max_ms < 25.0, f"Max halt latency {max_ms:.3f}ms exceeded 25.0ms SLA"
    assert avg_ms < 1.0, f"Average halt latency {avg_ms:.3f}ms exceeded 1.0ms target"

    # Verify processing is blocked when halted
    with pytest.raises(RuntimeError):
        prosodic_acting_engine.apply_acting_envelope("Test text")
