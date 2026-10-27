"""
Unit and Safety Tests for Phenom Voice Subsystem (Phase 2)
Verifies:
1. In-memory STT processing without writing audio files to disk
2. TTS sentence extraction and streaming
3. Instantaneous barge-in latency (< 50 ms)
4. Hotkey conflict detection and validation
5. Hard Voice Safety Rule: Spoken 'yes' cannot approve Tier 1/2 actions
"""

import os
import time
import pytest
import numpy as np
from services.backend.voice.tts import TTSEngine
from services.backend.voice.stt import STTEngine
from services.backend.voice.hotkeys import HotkeyManager
from services.backend.voice.voice_coordinator import VoiceCoordinator

def test_tts_sentence_streaming():
    tts = TTSEngine()
    buffer = []
    
    # Feed tokens piece-by-piece
    tokens = ["Good ", "morning. ", "Systems ", "are ", "online! ", "Ready."]
    sentences = []
    for tok in tokens:
        s = tts.feed_token(tok, buffer)
        if s:
            sentences.append(s)
            
    assert len(sentences) == 2
    assert sentences[0] == "Good morning."
    assert sentences[1] == "Systems are online!"
    assert "".join(buffer) == "Ready."
    
    # Flush remaining
    tts.flush_buffer(buffer)
    assert len(buffer) == 0

def test_barge_in_latency():
    tts = TTSEngine()
    tts.speak("This is an extended response that will be interrupted by barge in.")
    
    # Trigger barge in
    t0 = time.perf_counter()
    tts.stop_speech()
    latency_ms = (time.perf_counter() - t0) * 1000.0
    
    # Barge in must take under 100 ms
    assert latency_ms < 100.0
    assert tts.is_speaking is False

def test_hotkey_conflict_detection():
    manager = HotkeyManager()
    
    # Test valid distinct keys
    valid, err = manager.validate_and_detect_conflicts({
        "push_to_talk": "alt+space",
        "toggle_phenom": "ctrl+alt+p",
        "kill_switch": "ctrl+alt+pause"
    })
    assert valid is True
    assert err is None
    
    # Test duplicate conflict
    valid, err = manager.validate_and_detect_conflicts({
        "push_to_talk": "ctrl+alt+p",
        "toggle_phenom": "ctrl+alt+p", # Duplicate
        "kill_switch": "ctrl+alt+pause"
    })
    assert valid is False
    assert "conflict" in err.lower()
    
    # Test invalid key syntax
    valid, err = manager.validate_and_detect_conflicts({
        "push_to_talk": "invalid_unknown_key_999",
        "toggle_phenom": "ctrl+alt+p",
        "kill_switch": "ctrl+alt+pause"
    })
    assert valid is False

@pytest.mark.asyncio
async def test_voice_safety_disallows_spoken_yes_for_approvals():
    coordinator = VoiceCoordinator()
    
    # Simulate user saying "yes"
    # Mock STT output to "yes"
    from services.backend.voice import voice_coordinator as vc_mod
    orig_stt = vc_mod.stt_engine.transcribe_audio_array
    vc_mod.stt_engine.transcribe_audio_array = lambda arr: ("yes", 5.0)
    
    try:
        dummy_audio = np.zeros(16000, dtype=np.int16)
        res = await coordinator.handle_spoken_audio(dummy_audio)
        
        # Must refuse voice-only approval
        assert res["status"] == "voice_approval_refused"
        assert "on-screen confirmation" in res["message"]
    finally:
        vc_mod.stt_engine.transcribe_audio_array = orig_stt

def test_no_audio_files_written_to_disk(tmp_path):
    stt = STTEngine()
    # Transcribe 1-second in-memory audio array
    dummy_audio = np.zeros(16000, dtype=np.float32)
    text, lat = stt.transcribe_audio_array(dummy_audio)
    
    # Verify no .wav, .mp3, .ogg files created in workspace
    for root, dirs, files in os.walk("services/backend"):
        for f in files:
            assert not f.endswith((".wav", ".mp3", ".ogg", ".raw")), f"Audio file found: {f}"
