"""Tests for Full-Duplex Conversational Voice & Instant Acoustic Barge-In (Milestone 30 Phase 3).

Validates:
- Speech onset detection within < 50ms (VOICE-01.2)
- Acoustic barge-in interruption SLA < 15.0ms (BARGE-02.1)
- Turn-taking finite state machine with conversational pause hangover (BARGE-02.2)
- Rule 8 checkout / payment rejection (raises Rule8ViolationError)
- Rule 11 credential protection ([REDACTED])
- Rule 3 Universal Guardian kill switch SLA < 25.0ms
- Safety Tool Registry integration (Tiers 0 & 1)
"""

import time
import numpy as np
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.voice.full_duplex_voice_engine import (
    FullDuplexVoiceEngine,
    Rule8ViolationError,
    TurnTakingState,
)
import services.backend.tools.full_duplex_voice_tools  # Registers tools in ToolRegistry


class MockVAD:
    """Mock VAD evaluating speech energy reliably for unit tests."""
    def __init__(self):
        self.reset_count = 0

    def process_chunk(self, chunk: np.ndarray) -> float:
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
        return 0.88 if rms > 0.05 else 0.02

    def reset_states(self):
        self.reset_count += 1


@pytest.fixture(autouse=True)
def reset_guardian():
    """Ensure Guardian is resumed before and after every test."""
    guardian.resume()
    yield
    guardian.resume()


@pytest.fixture
def voice_engine():
    """Creates a fresh FullDuplexVoiceEngine instance for isolated testing."""
    return FullDuplexVoiceEngine(
        vad_engine=MockVAD(),
        vad_threshold=0.40,
        required_consecutive_chunks=2,
        pause_hangover_chunks=10,  # 10 chunks ~ 320ms for fast test execution
    )


def generate_audio_chunk(is_speech: bool = True, samples: int = 512) -> np.ndarray:
    """Generates synthetic 16kHz PCM audio chunk (sine wave for speech, near-zero for silence)."""
    t = np.linspace(0, samples / 16000, samples, endpoint=False)
    if is_speech:
        return (0.6 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    return (0.0001 * np.random.randn(samples)).astype(np.float32)


def test_vad_onset_detection(voice_engine):
    """VOICE-01.2: Real-time VAD detects user speech onset within < 50ms."""
    speech_chunk = generate_audio_chunk(is_speech=True)

    t0 = time.perf_counter()
    res1 = voice_engine.process_audio_chunk(speech_chunk)
    res2 = voice_engine.process_audio_chunk(speech_chunk)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert res1["is_speech"] is True
    assert res2["is_speech"] is True
    assert res2["state"] == TurnTakingState.USER_SPEAKING.value
    # 2 chunks evaluated in < 50.0ms SLA (typical < 5.0ms)
    assert elapsed_ms < 50.0, f"Onset detection took {elapsed_ms:.2f}ms >= 50ms SLA"


def test_acoustic_barge_in_sla(voice_engine):
    """BARGE-02.1: Sub-15ms acoustic barge-in interruption halts speech immediately."""
    voice_engine.state = TurnTakingState.AGENT_SPEAKING
    speech_chunk = generate_audio_chunk(is_speech=True)

    # First speech chunk primes hysteresis
    voice_engine.process_audio_chunk(speech_chunk)

    # Second speech chunk triggers barge-in
    t0 = time.perf_counter()
    res = voice_engine.process_audio_chunk(speech_chunk)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert res["barge_in_triggered"] is True
    assert res["state"] == TurnTakingState.USER_SPEAKING.value
    assert elapsed_ms < 15.0, f"Acoustic barge-in took {elapsed_ms:.2f}ms >= 15.0ms SLA"
    assert voice_engine.total_barge_ins == 1

    # Also test the trigger_acoustic_barge_in_test benchmark helper
    bench_res = voice_engine.trigger_acoustic_barge_in_test()
    assert bench_res["sla_passed"] is True
    assert bench_res["barge_in_latency_ms"] < 15.0


def test_turn_taking_pause_hangover(voice_engine):
    """BARGE-02.2: Conversational pause hangover handles breathing without cutting off."""
    speech_chunk = generate_audio_chunk(is_speech=True)
    silence_chunk = generate_audio_chunk(is_speech=False)

    # Enter USER_SPEAKING
    voice_engine.process_audio_chunk(speech_chunk)
    res_speaking = voice_engine.process_audio_chunk(speech_chunk)
    assert res_speaking["state"] == TurnTakingState.USER_SPEAKING.value

    # Feed 4 silence chunks (less than pause_hangover_chunks = 10)
    for _ in range(4):
        mid_res = voice_engine.process_audio_chunk(silence_chunk)
        assert mid_res["state"] == TurnTakingState.USER_SPEAKING.value, "Premature cutoff during pause!"

    # Feed remaining 6 silence chunks to reach pause hangover threshold
    final_res = None
    for _ in range(6):
        final_res = voice_engine.process_audio_chunk(silence_chunk)

    assert final_res is not None
    assert final_res["state"] == TurnTakingState.PROCESSING.value, "Failed to transition to PROCESSING after hangover"


def test_rule_8_anti_checkout_rejection(voice_engine):
    """Rule 8: Voice channel strictly blocks payment, checkout, or billing requests."""
    speech_chunk = generate_audio_chunk(is_speech=True)
    with pytest.raises(Rule8ViolationError) as exc_info:
        voice_engine.process_audio_chunk(
            speech_chunk,
            simulated_transcript="Phenom, proceed to checkout and pay for the order",
        )
    assert "Rule 8 Violation" in str(exc_info.value)

    with pytest.raises(Rule8ViolationError):
        voice_engine.check_safety("Buy the subscription using my credit card")


def test_rule_11_credential_protection(voice_engine):
    """Rule 11: Scrubbing of passwords, tokens, and secrets from transcribed voice buffers."""
    dirty_text = "Here is the auth token Bearer eyJhbGciOiJIUzI1Ni... and password=SuperSecretPassword456"
    clean_text, count = voice_engine.scrub_credentials(dirty_text)
    assert count >= 1
    assert "SuperSecretPassword456" not in clean_text
    assert "[REDACTED]" in clean_text


def test_guardian_kill_switch_sla(voice_engine):
    """Rule 3: Universal Guardian kill switch halts full-duplex voice engine in < 25.0ms."""
    guardian.trigger("EMERGENCY TEST TRIGGER")
    assert guardian.is_halted

    speech_chunk = generate_audio_chunk(is_speech=True)
    t0 = time.perf_counter()
    with pytest.raises(RuntimeError) as exc_info:
        voice_engine.process_audio_chunk(speech_chunk)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert "Execution halted by Guardian kill switch" in str(exc_info.value)
    assert elapsed_ms < 25.0, f"Guardian SLA violated: took {elapsed_ms:.2f}ms >= 25.0ms"


def test_tool_registry_and_tiers():
    """Verify tool registration, risk tiers (Tier 0 & Tier 1), and preview functions."""
    # 1. get_full_duplex_voice_state (Tier 0)
    state_tool = registry.get("get_full_duplex_voice_state")
    assert state_tool is not None
    assert state_tool.tier == 0
    state_out = state_tool.handler_fn()
    assert "state" in state_out
    assert "vad_threshold" in state_out

    # 2. configure_full_duplex_thresholds (Tier 1)
    cfg_tool = registry.get("configure_full_duplex_thresholds")
    assert cfg_tool is not None
    assert cfg_tool.tier == 1
    assert "configure" in cfg_tool.preview_fn({"vad_threshold": 0.65}).lower()

    # 3. trigger_acoustic_barge_in_test (Tier 1)
    test_tool = registry.get("trigger_acoustic_barge_in_test")
    assert test_tool is not None
    assert test_tool.tier == 1
    bench_out = test_tool.handler_fn()
    assert bench_out["sla_passed"] is True
    assert bench_out["barge_in_latency_ms"] < 15.0

    # 4. reset_full_duplex_state_machine (Tier 0)
    reset_tool = registry.get("reset_full_duplex_state_machine")
    assert reset_tool is not None
    assert reset_tool.tier == 0
    reset_out = reset_tool.handler_fn()
    assert reset_out["status"] == "RESET"
    assert reset_out["state"] == TurnTakingState.LISTENING.value
