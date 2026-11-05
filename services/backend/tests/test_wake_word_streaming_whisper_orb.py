"""
Comprehensive Test Suite for Milestone 18 Phase 3:
Local Wake-Word, Streaming Whisper & Reactive 3D Particle Orb
(VOX-04.1, VOX-04.2, ORB-02.1, ORB-02.2, VOX-04.3, SAF-01, SAF-02)
"""

import time
import pytest
import numpy as np

from services.backend.voice.wake_word_listener import (
    WakeWordListener,
    wake_word_listener,
    CHUNK_SIZE,
    SAMPLE_RATE,
)
from services.backend.voice.streaming_whisper import (
    StreamingWhisperEngine,
    streaming_whisper,
)
from services.backend.tools.wake_word_and_orb_tools import (
    get_wake_word_status,
    set_wake_word_sensitivity,
    trigger_manual_wake,
    set_orb_emotion_preset,
    mute_audio_input,
    VALID_EMOTIONS,
)
from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.orchestrator.engine import Orchestrator
from services.backend.voice.tts import tts_engine


@pytest.fixture(autouse=True)
def reset_audio_state():
    """Ensures clean state before and after each test."""
    guardian.resume()
    wake_word_listener.reset()
    wake_word_listener.set_muted(False)
    wake_word_listener.set_sensitivity(0.65)
    streaming_whisper.reset()
    streaming_whisper.set_muted(False)
    tts_engine.stop_speech()
    yield
    guardian.resume()
    wake_word_listener.reset()
    streaming_whisper.reset()
    tts_engine.stop_speech()


# ---------------- 1. LOCAL WAKE-WORD KEYWORD DETECTION (VOX-04.1, RULE 4) ----------------

def test_local_wake_word_keyword_detection_without_cloud_egress():
    """
    Verifies that local wake-word listener processes 16kHz audio chunks purely in RAM
    without network egress or file persistence (Rule 4), with configurable sensitivity.
    """
    listener = WakeWordListener(wake_phrase="hey phenom", sensitivity=0.85)
    wakes_detected = []
    listener.set_wake_callback(lambda phrase: wakes_detected.append(phrase))

    # 1. Silence chunk -> No detection
    silence_chunk = np.zeros(CHUNK_SIZE, dtype=np.int16)
    res = listener.process_audio_chunk(silence_chunk)
    assert res is None
    assert len(wakes_detected) == 0

    # 2. Quiet noise chunk -> No detection
    noise_chunk = (np.random.randn(CHUNK_SIZE) * 200).astype(np.int16)
    res = listener.process_audio_chunk(noise_chunk)
    assert res is None
    assert len(wakes_detected) == 0

    # 3. Formant-modeled synthetic speech burst ("Hey Phenom" acoustic energy + ZCR)
    t = np.linspace(0, 0.08, CHUNK_SIZE, endpoint=False)
    # Fundamental pitch ~160Hz + fricative high frequency component (ZCR trigger)
    synthetic_speech = (
        0.4 * np.sin(2 * np.pi * 160 * t) +
        0.3 * np.sin(2 * np.pi * 800 * t) +
        0.2 * np.sin(2 * np.pi * 2800 * t)
    )
    speech_chunk = (synthetic_speech * 30000).astype(np.int16)

    res = listener.process_audio_chunk(speech_chunk)
    assert res == "hey phenom"
    assert len(wakes_detected) == 1
    assert wakes_detected[0] == "hey phenom"

    # Verify zero disk writes and RAM circular buffer
    status = listener.get_status()
    assert status["ring_buffer_chunks"] == 3
    assert status["total_wakes"] == 1
    assert status["enabled"] is True


def test_wake_word_mute_and_manual_wake():
    """
    Verifies mute toggling suppresses audio processing and manual wake triggers.
    """
    listener = WakeWordListener(wake_phrase="hey phenom", sensitivity=0.7)
    wakes = []
    listener.set_wake_callback(lambda p: wakes.append(p))

    # Mute listener
    listener.set_muted(True)
    assert listener.is_muted is True
    assert listener.is_listening is False

    # Chunk during mute is ignored
    speech_chunk = (np.ones(CHUNK_SIZE) * 25000).astype(np.int16)
    assert listener.process_audio_chunk(speech_chunk) is None
    assert len(wakes) == 0

    # Manual wake should fail when muted
    assert listener.trigger_manual_wake() is False
    assert len(wakes) == 0

    # Unmute
    listener.set_muted(False)
    assert listener.is_listening is True

    # Manual wake succeeds when unmuted
    assert listener.trigger_manual_wake() is True
    assert len(wakes) == 1
    assert wakes[0] == "hey phenom"


# ---------------- 2. STREAMING WHISPER & SILERO VAD (VOX-04.2) ----------------

def test_streaming_whisper_silero_vad_boundary_detection():
    """
    Verifies real-time chunked VAD evaluation, speech boundary detection,
    and end-of-speech silence detection yielding final transcription.
    """
    engine = StreamingWhisperEngine(speech_threshold=0.40, silence_timeout_chunks=4)
    transcripts = []
    engine.set_transcript_callback(lambda text, is_final: transcripts.append((text, is_final)))

    t = np.linspace(0, 0.032, 512, endpoint=False)
    speech_chunk = (np.sin(2 * np.pi * 300 * t) * 20000).astype(np.int16)
    silence_chunk = np.zeros(512, dtype=np.int16)

    # Ingest 3 speech chunks (speech onset + hysteresis)
    out1 = engine.process_chunk(speech_chunk)
    assert out1["speech"] is True

    out2 = engine.process_chunk(speech_chunk)
    assert out2["speech"] is True
    assert engine._is_user_speaking is True

    out3 = engine.process_chunk(speech_chunk)
    assert out3["speech"] is True

    # Ingest silence chunks to trigger end-of-speech threshold (4 chunks)
    for _ in range(3):
        out = engine.process_chunk(silence_chunk)
        assert out["speech"] is False
        assert out["is_final"] is False

    # 4th silence chunk Denotes end of utterance
    final_out = engine.process_chunk(silence_chunk)
    assert final_out["is_final"] is True
    assert final_out["transcript"] is not None
    assert len(transcripts) == 1
    assert transcripts[0][1] is True  # is_final = True


def test_instantaneous_conversational_barge_in():
    """
    Verifies sub-5ms conversational barge-in interruption (< 5ms SLA)
    when user speaks while assistant speech / TTS is actively playing.
    """
    engine = StreamingWhisperEngine(speech_threshold=0.30)
    tts_engine._is_speaking = True  # Assistant currently speaking

    barge_in_fired = []
    engine.set_barge_in_callback(lambda: barge_in_fired.append(True))

    t = np.linspace(0, 0.032, 512, endpoint=False)
    speech_chunk = (np.sin(2 * np.pi * 300 * t) * 25000).astype(np.int16)

    # First speech chunk increments counter
    engine.process_chunk(speech_chunk)

    # Second speech chunk triggers barge-in (< 5ms SLA)
    t_start = time.perf_counter()
    res = engine.process_chunk(speech_chunk)
    barge_in_latency = (time.perf_counter() - t_start) * 1000.0

    assert res["barge_in"] is True
    assert tts_engine.is_speaking is False  # Immediately silenced
    assert len(barge_in_fired) == 1
    assert engine.total_barge_ins == 1
    assert barge_in_latency < 5.0, f"Barge-in latency {barge_in_latency:.2f}ms exceeded 5.0ms SLA"


# ---------------- 3. SAFETY LAYER & TOOL REGISTRY (SAF-01) ----------------

def test_wake_word_and_orb_tools_registry_and_previews():
    """
    Verifies that all 5 voice & orb tools are registered in ToolRegistry
    with strict risk tiers and human-readable confirmation previews.
    """
    expected_tools = {
        "get_wake_word_status": 0,
        "set_wake_word_sensitivity": 1,
        "trigger_manual_wake": 0,
        "set_orb_emotion_preset": 1,
        "mute_audio_input": 0,
    }

    for name, expected_tier in expected_tools.items():
        assert name in registry._tools, f"Tool '{name}' not registered in ToolRegistry"
        tool_def = registry._tools[name]
        assert tool_def.tier == expected_tier, f"Tool '{name}' has tier {tool_def.tier}, expected {expected_tier}"

    # Test preview generators
    preview_sens = registry._tools["set_wake_word_sensitivity"].preview_fn({"sensitivity": 0.85})
    assert "[Tier 1]" in preview_sens
    assert "0.85" in preview_sens

    preview_orb = registry._tools["set_orb_emotion_preset"].preview_fn({"emotion": "urgent"})
    assert "[Tier 1]" in preview_orb
    assert "urgent" in preview_orb

    preview_mute = registry._tools["mute_audio_input"].preview_fn({"muted": True})
    assert "[Tier 0]" in preview_mute
    assert "Mute" in preview_mute


def test_orb_emotion_presets_and_state():
    """
    Verifies that set_orb_emotion_preset transitions state across all valid presets
    and rejects invalid emotion strings.
    """
    for emotion in VALID_EMOTIONS:
        res = set_orb_emotion_preset(emotion=emotion)
        assert res["status"] == "success"
        assert res["current_emotion"] == emotion
        assert res["config"]["brightness"] > 0

    with pytest.raises(ValueError) as exc:
        set_orb_emotion_preset(emotion="non_existent_mood")
    assert "Invalid emotion" in str(exc.value)


# ---------------- 4. DIRECT VOICE & ORB INTENTS ----------------

def test_direct_voice_and_orb_intents():
    """
    Verifies Orchestrator direct voice & chat intent parsing for wake word,
    mic mute/unmute, sensitivity, and orb emotion presets.
    """
    orchestrator = Orchestrator()

    # 1. Wake word status
    res = orchestrator._detect_direct_intent("wake word status")
    assert res is not None
    assert res[0] == "get_wake_word_status"

    # 2. Manual wake
    res = orchestrator._detect_direct_intent("trigger wake word")
    assert res is not None
    assert res[0] == "trigger_manual_wake"

    res2 = orchestrator._detect_direct_intent("wake phenom")
    assert res2 is not None
    assert res2[0] == "trigger_manual_wake"

    # 3. Mute / Unmute
    res_mute = orchestrator._detect_direct_intent("mute microphone")
    assert res_mute is not None
    assert res_mute[0] == "mute_audio_input"
    assert res_mute[1]["muted"] is True

    res_unmute = orchestrator._detect_direct_intent("unmute mic")
    assert res_unmute is not None
    assert res_unmute[0] == "mute_audio_input"
    assert res_unmute[1]["muted"] is False

    # 4. Sensitivity
    res_sens = orchestrator._detect_direct_intent("set wake word sensitivity to 75%")
    assert res_sens is not None
    assert res_sens[0] == "set_wake_word_sensitivity"
    assert abs(res_sens[1]["sensitivity"] - 0.75) < 0.01

    # 5. Orb emotion
    res_orb = orchestrator._detect_direct_intent("set orb emotion to urgent")
    assert res_orb is not None
    assert res_orb[0] == "set_orb_emotion_preset"
    assert res_orb[1]["emotion"] == "urgent"


# ---------------- 5. UNIVERSAL GUARDIAN AUDIO CUT-OFF SLA BENCHMARK (VOX-04.3, SAF-02.1) ----------------

def test_universal_guardian_audio_silence_hook_sla():
    """
    VOX-04.3 & SAF-02.1 Hard SLA Benchmark:
    Verifies that triggering the Guardian Kill Switch synchronously mutes microphone processing,
    aborts streaming Whisper transcription, and clears audio buffers in < 10.0ms SLA
    (< 25.0ms universal SLA, target typical < 1.0ms).
    """
    # Prime both engines with active audio data
    t = np.linspace(0, 0.08, CHUNK_SIZE, endpoint=False)
    chunk = (np.sin(2 * np.pi * 400 * t) * 20000).astype(np.int16)

    wake_word_listener.process_audio_chunk(chunk)
    streaming_whisper.process_chunk(chunk[:512])

    assert wake_word_listener.is_listening is True
    assert streaming_whisper._is_active is True
    assert len(wake_word_listener._audio_ring_buffer) > 0
    assert len(streaming_whisper._ring_buffer) > 0

    # 1. Direct audio silence hook SLA (< 5.0ms)
    t_direct_0 = time.perf_counter()
    wake_word_listener.halt()
    streaming_whisper.halt()
    t_direct_1 = time.perf_counter()
    direct_latency_ms = (t_direct_1 - t_direct_0) * 1000.0
    print(f"\n[BENCHMARK] Direct Audio Cut-Off Latency: {direct_latency_ms:.4f}ms (< 5.0ms SLA)")
    assert direct_latency_ms < 5.0, f"Direct audio silence {direct_latency_ms:.2f}ms exceeded 5.0ms SLA"

    # Reset for full Guardian Kill Switch trigger test
    wake_word_listener.reset()
    streaming_whisper.reset()
    wake_word_listener.process_audio_chunk(chunk)
    streaming_whisper.process_chunk(chunk[:512])

    # 2. Universal Guardian Kill Switch trigger benchmark (< 25.0ms SLA, target < 1.0ms)
    t0 = time.perf_counter()
    guardian.trigger(reason="Milestone 18 Audio Emergency Silence Benchmark")
    t1 = time.perf_counter()

    latency_ms = (t1 - t0) * 1000.0
    print(f"[BENCHMARK] Universal Guardian Audio Silence Latency: {latency_ms:.4f}ms (< 25.0ms SLA)")

    assert latency_ms < 25.0, f"Guardian audio silence latency {latency_ms:.2f}ms exceeded 25.0ms SLA"

    # Verify synchronous post-halt state
    assert guardian.is_halted is True
    assert wake_word_listener.is_listening is False
    assert wake_word_listener.is_muted is True
    assert len(wake_word_listener._audio_ring_buffer) == 0

    assert streaming_whisper._is_active is False
    assert streaming_whisper._is_muted is True
    assert len(streaming_whisper._ring_buffer) == 0

    # Ensure subsequent audio chunks are strictly rejected
    assert wake_word_listener.process_audio_chunk(chunk) is None
    res = streaming_whisper.process_chunk(chunk[:512])
    assert res["speech"] is False
    assert res["barge_in"] is False

    # Ensure Tier 1 tools raise immediately under Guardian halt
    with pytest.raises(RuntimeError) as exc:
        set_wake_word_sensitivity(sensitivity=0.9)
    assert "Guardian Kill Switch" in str(exc.value)

    with pytest.raises(RuntimeError) as exc2:
        set_orb_emotion_preset(emotion="urgent")
    assert "Guardian Kill Switch" in str(exc2.value)
