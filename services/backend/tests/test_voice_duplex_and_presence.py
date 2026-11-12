"""
Phenom 6.0 Phase 4 Verification Suite: Full-Duplex Voice & Presence Awareness
Tests Silero VAD inference throughput, full-duplex turn-taking, sub-50ms barge-in latency,
contextual speech modulation, zero-disk audio invariant, tool safety schemas, and <25ms Guardian halt SLA.
"""

import time
import os
import glob
import numpy as np
import pytest

from services.backend.voice.vad import SileroVAD, silero_vad
from services.backend.voice.duplex_pipeline import FullDuplexVoicePipeline, DuplexState, duplex_pipeline
from services.backend.voice.voice_modulator import VoiceModulator, AssistantMode, voice_modulator
from services.backend.voice.tts import tts_engine
from services.backend.voice.barge_in_controller import barge_in_controller
from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.main import on_guardian_state_change
import services.backend.tools.voice_tools  # Ensure voice tools are registered


def generate_synthetic_audio(freq_hz: float = 440.0, duration_samples: int = 512, sample_rate: int = 16000) -> np.ndarray:
    """Generates synthetic harmonic audio chunk in float32 normalized [-1.0, 1.0]."""
    t = np.arange(duration_samples) / float(sample_rate)
    samples = 0.5 * np.sin(2 * np.pi * freq_hz * t)
    return samples.astype(np.float32)


def test_silero_vad_inference_throughput_and_states():
    """VOX-01: Verifies Silero VAD ONNX loads, recurrent states update, and inference latency is < 2ms."""
    assert silero_vad.is_available, "Silero VAD ONNX model should be loaded and available"
    
    # Reset states
    silero_vad.reset_states()
    assert np.all(silero_vad._h == 0)
    assert np.all(silero_vad._c == 0)

    # Evaluate silence chunk
    silence = np.zeros(512, dtype=np.float32)
    t0 = time.perf_counter()
    prob_silence = silero_vad.process_chunk(silence)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 5.0, f"Silero VAD single chunk inference exceeded 5ms: {latency_ms:.2f}ms"
    assert prob_silence < 0.20, f"Expected low speech prob for silence, got {prob_silence}"

    # Verify recurrent hidden states updated
    assert not np.all(silero_vad._h == 0) or not np.all(silero_vad._c == 0)

    # Throughput benchmark: 50 consecutive 32ms chunks
    latencies = []
    chunk = generate_synthetic_audio(300.0, 512)
    for _ in range(50):
        t_start = time.perf_counter()
        silero_vad.process_chunk(chunk)
        latencies.append((time.perf_counter() - t_start) * 1000.0)

    avg_lat = float(np.mean(latencies))
    assert avg_lat < 2.0, f"Average Silero VAD latency {avg_lat:.2f}ms exceeds 2.0ms SLA"


def test_duplex_pipeline_continuous_listening_and_turn_taking():
    """VOX-01: Verifies full-duplex continuous listening, speech onset, and turn-taking completion."""
    pipeline = FullDuplexVoicePipeline(turn_end_silence_chunks=5)
    turns_received = []

    def on_turn(audio: np.ndarray):
        turns_received.append(audio)

    pipeline.set_on_turn_completed(on_turn)
    tts_engine.stop_speech()
    pipeline.start()
    assert pipeline.state == DuplexState.LISTENING

    # 1. Ingest silence - stays in LISTENING
    silence = np.zeros(512, dtype=np.float32)
    for _ in range(5):
        res = pipeline.feed_audio_chunk(silence)
        assert res["state"] == "listening"
        assert not res["in_user_speech"]

    # 2. Simulate user speech (high probability)
    # We monkeypatch silero_vad.process_chunk for deterministic speech detection
    orig_process = silero_vad.process_chunk
    try:
        silero_vad.process_chunk = lambda c: 0.95
        for _ in range(3):
            res = pipeline.feed_audio_chunk(silence)
        assert res["in_user_speech"], "Pipeline should detect user speech onset"

        # 3. Simulate user silence after speech to trigger end-of-turn
        silero_vad.process_chunk = lambda c: 0.05
        turn_done = False
        for _ in range(6):
            res = pipeline.feed_audio_chunk(silence)
            if res.get("turn_completed"):
                turn_done = True
                break

        assert turn_done, "Pipeline should complete conversational turn upon silence timeout"
        assert pipeline.state == DuplexState.THINKING
        assert len(turns_received) == 1
        assert len(turns_received[0]) > 0
    finally:
        silero_vad.process_chunk = orig_process
        pipeline.stop()


def test_instant_barge_in_interruption_sla():
    """VOX-01: Verifies assistant speech interruption when user speaks, with stop latency < 50ms."""
    pipeline = FullDuplexVoicePipeline(barge_in_chunks_required=2)
    barge_in_events = []

    pipeline.set_on_barge_in(lambda: barge_in_events.append(time.time()))
    pipeline.start()

    # Simulate assistant speaking
    pipeline._set_state(DuplexState.SPEAKING)
    tts_engine._is_speaking = True

    orig_process = silero_vad.process_chunk
    try:
        silero_vad.process_chunk = lambda c: 0.92
        silence = np.zeros(512, dtype=np.float32)

        # Chunk 1: first speech chunk
        res1 = pipeline.feed_audio_chunk(silence)
        assert res1["status"] == "assistant_speaking"

        # Chunk 2: second speech chunk -> triggers barge-in
        t_pre = time.perf_counter()
        res2 = pipeline.feed_audio_chunk(silence)
        t_post = time.perf_counter()
        total_time_ms = (t_post - t_pre) * 1000.0

        assert res2["status"] == "barge_in_interrupted"
        assert res2["state"] == "listening"
        assert len(barge_in_events) == 1
        assert res2["barge_in_latency_ms"] < 50.0, f"Barge-in stop latency {res2['barge_in_latency_ms']:.2f}ms exceeded 50ms SLA"
        assert total_time_ms < 50.0, f"Total chunk execution {total_time_ms:.2f}ms exceeded 50ms SLA"
    finally:
        silero_vad.process_chunk = orig_process
        tts_engine.stop_speech()
        pipeline.stop()


def test_zero_disk_audio_invariant(tmp_path):
    """VOX-01 / Rule 4: Verifies audio buffers are held strictly in RAM with zero disk writes."""
    pipeline = FullDuplexVoicePipeline()
    pipeline.start()

    # Capture file list before streaming
    before_files = set(glob.glob("*.wav") + glob.glob("*.mp3") + glob.glob("*.raw"))

    # Feed 20 audio chunks in RAM
    for _ in range(20):
        chunk = generate_synthetic_audio(500.0, 512)
        pipeline.feed_audio_chunk(chunk)

    # Capture file list after streaming
    after_files = set(glob.glob("*.wav") + glob.glob("*.mp3") + glob.glob("*.raw"))
    new_audio_files = after_files - before_files

    assert len(new_audio_files) == 0, f"Discovered persisted audio files violating zero-disk invariant: {new_audio_files}"
    assert len(pipeline._ring_buffer) == 20, "Chunks must reside in memory ring buffer"
    pipeline.stop()


def test_contextual_voice_modulation_across_modes():
    """VOX-02: Verifies dynamic speech volume, cadence, and tone presets across all assistant modes."""
    modulator = VoiceModulator()

    # 1. Work mode: 100% volume, cadence rate 1
    modulator.set_override(mode=AssistantMode.WORK)
    work_prof = modulator.apply_to_tts()
    assert work_prof["mode"] == "work"
    assert work_prof["volume_scale"] == 1.0
    assert work_prof["cadence_rate"] == 1
    assert not work_prof["is_muted"]

    # 2. Study mode: 35% volume, cadence rate 0
    modulator.set_override(mode=AssistantMode.STUDY)
    study_prof = modulator.apply_to_tts()
    assert study_prof["mode"] == "study"
    assert study_prof["volume_scale"] == 0.35
    assert study_prof["cadence_rate"] == 0
    assert not study_prof["is_muted"]

    # 3. Chill mode: 65% volume, relaxed pace
    modulator.set_override(mode=AssistantMode.CHILL)
    chill_prof = modulator.apply_to_tts()
    assert chill_prof["mode"] == "chill"
    assert chill_prof["volume_scale"] == 0.65
    assert not chill_prof["is_muted"]

    # 4. Deep Focus mode: 0% volume (strictly muted)
    modulator.set_override(mode=AssistantMode.DEEP_FOCUS)
    focus_prof = modulator.apply_to_tts()
    assert focus_prof["mode"] == "deep_focus"
    assert focus_prof["volume_scale"] == 0.0
    assert focus_prof["is_muted"]
    assert tts_engine.get_volume() == 0.0

    # Verify speech is suppressed in deep focus
    initial_q_size = tts_engine.get_queued_count()
    tts_engine.speak("This announcement should be muted in deep focus mode.")
    assert tts_engine.get_queued_count() == initial_q_size, "TTS speak should be suppressed when volume scale is 0.0"

    # 5. Clear overrides restores default
    modulator.clear_overrides()
    assert not modulator.has_overrides()


def test_voice_safety_tool_registrations_and_execution():
    """Verifies all Phase 4 voice tools are properly registered with Pydantic schemas in ToolRegistry."""
    # 1. get_voice_duplex_status (Tier 0)
    status_entry = registry.get("get_voice_duplex_status")
    assert status_entry is not None, "get_voice_duplex_status must be registered"
    assert status_entry.tier == 0
    status_res = status_entry.handler_fn()
    assert status_res["status"] == "ok"
    assert "duplex_pipeline" in status_res
    assert "voice_modulation" in status_res

    # 2. configure_voice_presence (Tier 1)
    cfg_entry = registry.get("configure_voice_presence")
    assert cfg_entry is not None, "configure_voice_presence must be registered"
    assert cfg_entry.tier == 1

    cfg_res = cfg_entry.handler_fn(mode="study", volume=0.40)
    assert cfg_res["status"] == "configured"
    assert cfg_res["effective_profile"]["mode"] == "study"
    assert cfg_res["effective_profile"]["volume_scale"] == 0.40

    # Clear overrides
    clear_res = cfg_entry.handler_fn(clear_overrides=True)
    assert clear_res["status"] == "cleared_overrides"

    # 3. trigger_voice_barge_in (Tier 0)
    barge_entry = registry.get("trigger_voice_barge_in")
    assert barge_entry is not None, "trigger_voice_barge_in must be registered"
    assert barge_entry.tier == 0
    barge_res = barge_entry.handler_fn()
    assert barge_res["status"] == "interrupted"
    assert "stop_latency_ms" in barge_res


def test_guardian_synchronous_duplex_halt_latency_sla():
    """Rule 3: Verifies Guardian trigger halts full-duplex voice loops synchronously in < 25ms SLA."""
    guardian.resume()
    duplex_pipeline.start()
    assert duplex_pipeline.state == DuplexState.LISTENING

    t0 = time.perf_counter()
    guardian.trigger("Voice duplex emergency halt test")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert duplex_pipeline.state == DuplexState.HALTED, "Duplex pipeline must be HALTED after guardian trigger"
    assert elapsed_ms < 25.0, f"Guardian synchronous voice halt exceeded 25ms SLA: {elapsed_ms:.2f} ms"

    # Clean up guardian state
    guardian.resume()
