"""
Unit Tests for Instant Acoustic Barge-In & Audio Guardian Kill Switch
Milestone 43.0: Project FULL-DUPLEX JARVIS (Phase 2)
"""

import time
import numpy as np
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.voice.tts import tts_engine
from services.backend.voice.vad import silero_vad
from services.backend.voice.barge_in_controller import barge_in_controller, BargeInController
from services.backend.voice.streaming_whisper import StreamingWhisperEngine, CHUNK_SIZE, SAMPLE_RATE
from services.backend.tools.barge_in_tools import (
    handle_set_duplex_voice_state,
    handle_query_voice_latency_metrics,
    handle_trigger_voice_emergency_stop,
)


@pytest.fixture(autouse=True)
def clean_guardian_state():
    guardian.resume()
    silero_vad.reset_states()
    tts_engine.stop_speech()
    barge_in_controller.configure(energy_threshold=0.040, required_chunks=2)
    yield
    guardian.resume()
    silero_vad.reset_states()
    tts_engine.stop_speech()


def generate_speech_chunk(freq: float = 440.0, amplitude: float = 0.5) -> np.ndarray:
    t = np.linspace(0, CHUNK_SIZE / SAMPLE_RATE, CHUNK_SIZE, endpoint=False, dtype=np.float32)
    return amplitude * np.sin(2 * np.pi * freq * t)


def generate_silence_chunk() -> np.ndarray:
    return np.zeros(CHUNK_SIZE, dtype=np.float32)


def test_acoustic_barge_in_latency_under_15ms():
    """Verifies that acoustic barge-in interrupts active TTS within < 15ms SLA."""
    controller = barge_in_controller
    tts_engine._is_speaking = True

    barge_in_events = []
    controller.set_barge_in_callback(lambda: barge_in_events.append(True))

    speech = generate_speech_chunk(amplitude=0.6)

    # First chunk: onset initiation
    res1 = controller.process_audio_chunk(speech)
    assert res1 is False
    assert tts_engine.is_speaking is True

    # Second chunk: triggers barge-in (< 15ms SLA)
    t0 = time.perf_counter()
    res2 = controller.process_audio_chunk(speech)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert res2 is True
    assert tts_engine.is_speaking is False
    assert len(barge_in_events) == 1
    assert controller.last_interrupt_latency_ms < 15.0, (
        f"Barge-in SLA violation: {controller.last_interrupt_latency_ms}ms >= 15.0ms"
    )
    assert elapsed_ms < 25.0


def test_spoken_emergency_keyword_detection_sla_under_25ms():
    """Verifies spoken emergency keywords synchronously trigger Guardian in < 25ms."""
    controller = barge_in_controller
    guardian.resume()
    assert guardian.is_halted is False

    test_phrases = [
        "Phenom halt immediately",
        "Please stop all actions",
        "freeze the system",
        "guardian emergency protocol",
        "abort the mission right now",
    ]

    for phrase in test_phrases:
        guardian.resume()
        assert guardian.is_halted is False

        t0 = time.perf_counter()
        triggered = controller.check_emergency_spoken_command(phrase)
        lat_ms = (time.perf_counter() - t0) * 1000.0

        assert triggered is True, f"Failed to detect emergency keyword in: '{phrase}'"
        assert guardian.is_halted is True
        assert lat_ms < 25.0, f"Spoken Guardian SLA violation: {lat_ms}ms >= 25.0ms"
        assert controller.last_emergency_halt_latency_ms < 25.0


def test_streaming_whisper_spoken_emergency_integration():
    """Verifies that StreamingWhisperEngine transcribing an emergency directive trips Guardian."""
    guardian.resume()
    engine = StreamingWhisperEngine(silence_timeout_chunks=3)
    engine.inject_transcript("Phenom freeze everything and halt execution")

    # Ingest speech then silence
    engine.process_chunk(generate_speech_chunk(amplitude=0.5))
    engine.process_chunk(generate_speech_chunk(amplitude=0.5))
    for _ in range(3):
        engine.process_chunk(generate_silence_chunk())

    assert guardian.is_halted is True
    assert engine.get_status()["halted"] is True


def test_barge_in_tools_registration_and_execution():
    """Verifies barge-in tools in ToolRegistry: set_duplex_voice_state, query_voice_latency_metrics, trigger_voice_emergency_stop."""
    # Verify registration tiers
    assert registry.get_tier("set_duplex_voice_state") == 1
    assert registry.get_tier("query_voice_latency_metrics") == 0
    assert registry.get_tier("trigger_voice_emergency_stop") == 0

    # Test query metrics
    metrics = handle_query_voice_latency_metrics()
    assert "last_interrupt_latency_ms" in metrics
    assert "emergency_keywords" in metrics
    assert "halt" in metrics["emergency_keywords"]

    # Test configure state
    conf_res = handle_set_duplex_voice_state(energy_threshold=0.035, required_chunks=3)
    assert conf_res["status"] == "success"
    assert barge_in_controller.energy_threshold == 0.035
    assert barge_in_controller.required_chunks == 3

    # Test trigger emergency stop tool (< 25ms SLA)
    guardian.resume()
    assert guardian.is_halted is False
    stop_res = handle_trigger_voice_emergency_stop(reason="Unit test emergency")
    assert stop_res["status"] == "halted"
    assert stop_res["sla_met"] is True
    assert stop_res["elapsed_ms"] < 25.0
    assert guardian.is_halted is True


def test_fail_closed_under_guardian_halt():
    """Verifies that when Guardian is halted, barge-in audio processing fails closed."""
    guardian.trigger("Simulated emergency")
    assert guardian.is_halted is True

    speech = generate_speech_chunk(amplitude=0.8)
    res = barge_in_controller.process_audio_chunk(speech)
    assert res is False
    assert tts_engine.is_speaking is False
