"""
Unit Tests for Streaming Whisper STT & In-RAM Circular VAD Buffer
Milestone 43.0: Project FULL-DUPLEX JARVIS (Phase 1)
"""

import time
import os
from pathlib import Path
import numpy as np
import pytest

from services.backend.safety.guardian import guardian
from services.backend.voice.vad import silero_vad
from services.backend.voice.streaming_whisper import (
    StreamingWhisperEngine,
    CHUNK_SIZE,
    SAMPLE_RATE,
    MAX_RING_BUFFER_CHUNKS
)
from services.backend.schemas.duplex_voice import DuplexVoiceState, SpeechTranscriptionResult


@pytest.fixture
def fresh_engine():
    guardian.resume()
    silero_vad.reset_states()
    engine = StreamingWhisperEngine(speech_threshold=0.50, silence_timeout_chunks=5)
    engine.reset()
    yield engine
    silero_vad.reset_states()
    guardian.resume()


def generate_speech_chunk(freq: float = 440.0, amplitude: float = 0.5) -> np.ndarray:
    """Generates a synthetic 512-sample sine wave chunk representing vocal speech."""
    t = np.linspace(0, CHUNK_SIZE / SAMPLE_RATE, CHUNK_SIZE, endpoint=False, dtype=np.float32)
    return amplitude * np.sin(2 * np.pi * freq * t)


def generate_silence_chunk() -> np.ndarray:
    """Generates a 512-sample silence chunk."""
    return np.zeros(CHUNK_SIZE, dtype=np.float32)


def test_speech_onset_detection_latency(fresh_engine):
    """Verifies that speech onset is detected within sub-50ms SLA upon speech frames."""
    engine = fresh_engine
    speech_chunk = generate_speech_chunk(amplitude=0.6)

    # First chunk initiates hysteresis
    res1 = engine.process_chunk(speech_chunk)
    assert res1["speech"] is True

    # Second chunk confirms speech onset (sub-50ms SLA)
    t0 = time.perf_counter()
    res2 = engine.process_chunk(speech_chunk)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert res2["speech"] is True
    assert engine.get_status()["user_speaking"] is True
    assert engine.get_status()["state"] == DuplexVoiceState.USER_SPEAKING.value
    assert res2["onset_latency_ms"] < 50.0, f"Onset detection latency too high: {res2['onset_latency_ms']}ms"


def test_in_ram_circular_buffer_bounds_and_zero_disk(fresh_engine, tmp_path):
    """Verifies that audio chunks remain in RAM, ring buffer never exceeds 300 chunks, and zero disk files are written."""
    engine = fresh_engine
    
    # Record existing files in directory to ensure zero disk persistence (Rule 4)
    initial_wav_count = len(list(Path(".").glob("**/*.wav")))

    # Ingest 500 chunks (more than max 300)
    for _ in range(500):
        chunk = generate_speech_chunk(amplitude=0.2)
        engine.process_chunk(chunk)

    telemetry = engine.get_duplex_telemetry()
    assert telemetry.ring_buffer_chunks <= MAX_RING_BUFFER_CHUNKS
    assert telemetry.ring_buffer_chunks == MAX_RING_BUFFER_CHUNKS

    # Verify zero disk writes
    final_wav_count = len(list(Path(".").glob("**/*.wav")))
    assert final_wav_count == initial_wav_count, "Disk persistence violation: .wav files detected!"


def test_turn_taking_fsm_lifecycle(fresh_engine):
    """Verifies turn-taking state transitions from IDLE -> USER_SPEAKING -> PROCESSING."""
    engine = fresh_engine
    state_transitions = []
    engine.set_state_change_callback(lambda s: state_transitions.append(s))

    speech = generate_speech_chunk(amplitude=0.5)
    silence = generate_silence_chunk()

    # User speaks 4 chunks
    engine.process_chunk(speech)
    engine.process_chunk(speech)
    engine.process_chunk(speech)
    engine.process_chunk(speech)
    assert engine.get_status()["user_speaking"] is True

    # User pauses for silence_timeout_chunks (5 chunks)
    for _ in range(5):
        engine.process_chunk(silence)

    assert engine.get_status()["user_speaking"] is False
    assert engine.get_status()["total_utterances"] == 1
    assert DuplexVoiceState.USER_SPEAKING in state_transitions
    assert DuplexVoiceState.PROCESSING in state_transitions


def test_silence_hangover_and_utterance_transcription(fresh_engine):
    """Verifies silence hangover triggers final transcription delivery."""
    engine = fresh_engine
    received_transcripts = []
    engine.set_transcript_callback(lambda t: received_transcripts.append(t))

    engine.inject_transcript("Deploy 5-stage cyber mission on loopback range")

    # Ingest speech then silence
    engine.process_chunk(generate_speech_chunk(amplitude=0.5))
    engine.process_chunk(generate_speech_chunk(amplitude=0.5))

    for _ in range(5):
        engine.process_chunk(generate_silence_chunk())

    assert len(received_transcripts) == 1
    tx = received_transcripts[0]
    assert isinstance(tx, SpeechTranscriptionResult)
    assert tx.is_final is True
    assert "Deploy 5-stage cyber mission" in tx.transcript


def test_universal_guardian_kill_switch_zeroizes_buffers(fresh_engine):
    """Verifies emergency kill switch activation zeroizes RAM buffers and enforces fail-closed halt (< 25ms SLA)."""
    engine = fresh_engine

    # Populate buffer with speech
    engine.process_chunk(generate_speech_chunk(amplitude=0.5))
    engine.process_chunk(generate_speech_chunk(amplitude=0.5))
    assert engine.get_duplex_telemetry().ring_buffer_chunks > 0

    # Trigger Guardian kill switch
    t0 = time.perf_counter()
    guardian.trigger("Emergency halt during active voice ingestion")
    lat_ms = (time.perf_counter() - t0) * 1000.0

    assert lat_ms < 25.0, f"Guardian halt SLA violation: {lat_ms}ms >= 25.0ms"
    assert guardian.is_halted is True
    assert engine.get_status()["halted"] is True
    assert engine.get_status()["ring_buffer_chunks"] == 0

    # Ensure subsequent audio chunks are rejected
    res = engine.process_chunk(generate_speech_chunk(amplitude=0.5))
    assert res["speech"] is False
    assert res["state"] == DuplexVoiceState.HALTED.value

    # Resume and verify recovery
    guardian.resume()
    assert engine.get_status()["active"] is True
