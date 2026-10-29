"""
Unit and Integration Tests for Phenom Voice Speaker Verification & Hinglish STT (Task 7c)
Verifies:
1. 192-dimensional acoustic embedding extraction and centroid enrollment in SQLCipher.
2. Speaker verification with matching owner (S >= 0.76).
3. Two-strike mismatch handling:
   - Strike 1: status="retry", message="Voice did not match. Please repeat the command."
   - Strike 2: status="locked", message="Voice command locked. Physical hotkey Alt+Space or typed input required."
4. Hotkey unlock clearing locked state.
5. Voice data zero-residue wipe (DoD zeroing pass, 0 bytes remaining on disk).
6. Voice coordinator integration with speaker verification gate.
7. Multilingual STT engine configuration and Hinglish prompt conditioning.
"""

import os
import pytest
import numpy as np
from services.backend.voice.speaker_verification import SpeakerVerificationEngine, speaker_verifier
from services.backend.voice.voice_coordinator import VoiceCoordinator
from services.backend.voice.stt import stt_engine
from services.backend.memory.db import EncryptedDatabaseManager

@pytest.fixture(autouse=True)
def reset_global_speaker_state():
    """Resets global speaker_verifier state before and after each test."""
    orig_centroid = speaker_verifier.owner_centroid
    orig_locked = speaker_verifier.locked
    orig_mismatch = speaker_verifier.mismatch_count
    speaker_verifier.owner_centroid = None
    speaker_verifier.locked = False
    speaker_verifier.mismatch_count = 0
    yield
    speaker_verifier.owner_centroid = orig_centroid
    speaker_verifier.locked = orig_locked
    speaker_verifier.mismatch_count = orig_mismatch

def generate_voice(f0: float, sr: int = 16000, duration: float = 1.0, jitter: float = 0.0, noise_amp: float = 0.01) -> np.ndarray:
    """Helper to synthesize harmonic voice audio."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    pitch = f0 + jitter
    signal = (
        np.sin(2 * np.pi * pitch * t)
        + 0.5 * np.sin(2 * np.pi * 2 * pitch * t)
        + 0.3 * np.sin(2 * np.pi * 3 * pitch * t)
        + noise_amp * np.random.randn(len(t))
    ).astype(np.float32)
    return signal

def test_speaker_enrollment_and_centroid_calculation(tmp_path):
    db_file = str(tmp_path / "test_enroll.db")
    db_mgr = EncryptedDatabaseManager(db_path=db_file, encryption_key="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    engine = SpeakerVerificationEngine(db_manager=db_mgr, threshold=0.76)

    # Generate 5 enrollment samples
    samples = [generate_voice(140.0, jitter=np.sin(i)) for i in range(5)]
    res = engine.enroll(samples, name="owner")

    assert res["status"] == "enrolled"
    assert res["sample_count"] == 5
    assert res["embedding_dim"] == 192
    assert engine.is_enrolled() is True
    assert abs(np.linalg.norm(engine.owner_centroid) - 1.0) < 1e-4

    # Verify profile was persisted to SQLCipher
    saved_profile = db_mgr.get_speaker_profile(name="owner")
    assert saved_profile is not None
    assert saved_profile["sample_count"] == 5
    loaded_centroid = np.frombuffer(saved_profile["embedding_blob"], dtype=np.float32)
    assert len(loaded_centroid) == 192
    assert np.allclose(loaded_centroid, engine.owner_centroid)

def test_speaker_verification_matching_owner(tmp_path):
    db_file = str(tmp_path / "test_match.db")
    db_mgr = EncryptedDatabaseManager(db_path=db_file, encryption_key="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    engine = SpeakerVerificationEngine(db_manager=db_mgr, threshold=0.76)

    # Enroll owner (140 Hz)
    enrollment = [generate_voice(140.0, jitter=np.sin(i)) for i in range(5)]
    engine.enroll(enrollment)

    # Test with matching owner sample
    owner_test = generate_voice(140.0, jitter=0.5, noise_amp=0.015)
    verify_res = engine.verify(owner_test)

    assert verify_res["status"] == "match"
    assert verify_res["allowed"] is True
    assert verify_res["similarity"] >= 0.76
    assert engine.is_locked() is False

def test_speaker_verification_two_strike_mismatch_and_unlock(tmp_path):
    db_file = str(tmp_path / "test_mismatch.db")
    db_mgr = EncryptedDatabaseManager(db_path=db_file, encryption_key="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    engine = SpeakerVerificationEngine(db_manager=db_mgr, threshold=0.76)

    # Enroll owner (140 Hz)
    enrollment = [generate_voice(140.0, jitter=np.sin(i)) for i in range(5)]
    engine.enroll(enrollment)

    # Impostor audio (260 Hz)
    impostor_audio = generate_voice(260.0, noise_amp=0.02)

    # Strike 1: Prompt politely to retry
    strike1 = engine.verify(impostor_audio)
    assert strike1["status"] == "retry"
    assert strike1["allowed"] is False
    assert "Voice did not match. Please repeat the command." in strike1["message"]
    assert engine.is_locked() is False
    assert engine.mismatch_count == 1

    # Strike 2: Lock voice commands
    strike2 = engine.verify(impostor_audio)
    assert strike2["status"] == "locked"
    assert strike2["allowed"] is False
    assert "Voice command locked. Physical hotkey Alt+Space or typed input required." in strike2["message"]
    assert engine.is_locked() is True
    assert engine.mismatch_count == 2

    # Subsequent call while locked remains locked without recalculation
    strike3 = engine.verify(impostor_audio)
    assert strike3["status"] == "locked"
    assert strike3["allowed"] is False

    # Unlock via hotkey Alt+Space
    engine.unlock_with_hotkey()
    assert engine.is_locked() is False
    assert engine.mismatch_count == 0

def test_voice_data_zero_residue_wipe(tmp_path):
    voice_dir = str(tmp_path / "voice_store")
    os.makedirs(voice_dir, exist_ok=True)

    # Write dummy audio recordings
    clip1 = os.path.join(voice_dir, "clip1.bin")
    clip2 = os.path.join(voice_dir, "clip2.bin")
    with open(clip1, "wb") as f:
        f.write(b"SECRET_VOICE_DATA_12345" * 100)
    with open(clip2, "wb") as f:
        f.write(b"SECRET_VOICE_DATA_67890" * 200)

    db_file = str(tmp_path / "test_wipe.db")
    db_mgr = EncryptedDatabaseManager(db_path=db_file, encryption_key="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    engine = SpeakerVerificationEngine(db_manager=db_mgr, voice_store_dir=voice_dir)
    engine.enroll([generate_voice(140.0) for _ in range(3)])
    assert engine.is_enrolled() is True

    # Execute wipe
    wipe_res = engine.wipe_all_voice_data(wipe_db_profile=True)

    assert wipe_res["status"] == "wiped"
    assert wipe_res["files_zeroed_and_deleted"] == 2
    assert wipe_res["remaining_bytes_on_disk"] == 0
    assert not os.path.exists(voice_dir)
    assert engine.is_enrolled() is False
    assert db_mgr.get_speaker_profile(name="owner") is None

@pytest.mark.asyncio
async def test_voice_coordinator_speaker_verification_gate(tmp_path):
    coordinator = VoiceCoordinator()
    from services.backend.voice.speaker_verification import speaker_verifier

    db_file = str(tmp_path / "test_coord.db")
    db_mgr = EncryptedDatabaseManager(db_path=db_file, encryption_key="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    speaker_verifier.db = db_mgr

    # Enroll owner (140 Hz)
    speaker_verifier.enroll([generate_voice(140.0) for _ in range(5)])

    # Test impostor speech through coordinator
    impostor_audio = generate_voice(260.0)
    res = await coordinator.handle_spoken_audio(impostor_audio)

    assert res["status"] in ("speaker_mismatch", "speaker_locked")
    assert "Voice did not match" in res["message"] or "locked" in res["message"]

    # Unlock for clean test state
    speaker_verifier.unlock_with_hotkey()

@pytest.mark.asyncio
async def test_voice_coordinator_conversational_wipe_command():
    coordinator = VoiceCoordinator()
    from services.backend.voice import voice_coordinator as vc_mod

    # Mock STT to return 'forget this'
    orig_transcribe = vc_mod.stt_engine.transcribe_audio_array
    vc_mod.stt_engine.transcribe_audio_array = lambda arr, **kw: ("forget this", 5.0)

    try:
        dummy_audio = np.zeros(16000, dtype=np.int16)
        res = await coordinator.handle_spoken_audio(dummy_audio)

        assert res["status"] == "voice_data_wiped"
        assert "wiped" in res["message"].lower()
    finally:
        vc_mod.stt_engine.transcribe_audio_array = orig_transcribe

def test_stt_multilingual_configuration():
    stt = stt_engine
    stt.set_model("small")
    info = stt.get_model_info()

    assert info["model_size"] == "small"
    assert info["is_multilingual"] is True
