"""
Unit Tests for Ambient Feedback Synthesizer & Local WebRTC Mirror (FBK-01, SAF-02).
Verifies:
- Procedural audio parameter synthesis & stereo spatial panning
- In-memory 16-bit PCM WAV byte generation with header validation
- Guardian halt on feedback synthesizer
- Local WebRTC mirror session lifecycle, network constraints, and halt
"""

import io
import wave
import pytest
from services.backend.ambient.feedback_synthesizer import AmbientFeedbackSynthesizer
from services.backend.ambient.webrtc_mirror import LocalWebRTCMirror
from services.backend.schemas.proactive_bus import AudioCueType


def test_ambient_feedback_tone_synthesis():
    """Verify procedural cue parameter creation and profile retrieval."""
    synth = AmbientFeedbackSynthesizer()

    # Subtle Chime
    cue = synth.trigger_cue(AudioCueType.SUBTLE_CHIME, spatial_pan=-0.5)
    assert cue.cue_type == AudioCueType.SUBTLE_CHIME
    assert cue.frequency_hz > 0
    assert cue.spatial_pan == -0.5
    assert len(synth.get_recent_cues()) == 1

    # Fanfare
    fanfare = synth.trigger_cue("MILESTONE_FANFARE", spatial_pan=0.8)
    assert fanfare.cue_type == AudioCueType.MILESTONE_FANFARE
    assert fanfare.spatial_pan == 0.8


def test_ambient_feedback_wav_generation():
    """Verify in-memory WAV byte generation matches valid 16-bit stereo standard."""
    synth = AmbientFeedbackSynthesizer()
    wav_bytes = synth.synthesize_wav_bytes(
        frequency_hz=440.0,
        duration_ms=200,
        volume=0.5,
        spatial_pan=0.0,
    )

    assert len(wav_bytes) > 44  # Valid WAV header size
    assert wav_bytes.startswith(b"RIFF")
    assert b"WAVE" in wav_bytes[:16]

    # Verify via wave module
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 2      # Stereo
        assert wf.getsampwidth() == 2      # 16-bit
        assert wf.getframerate() == 22050


def test_ambient_feedback_guardian_halt():
    """Verify synthesizer stops generating when halted."""
    synth = AmbientFeedbackSynthesizer()
    synth.halt()
    assert synth.is_halted() is True

    with pytest.raises(PermissionError, match="Audio feedback halted"):
        synth.trigger_cue(AudioCueType.SUBTLE_CHIME)

    synth.reset()
    assert synth.is_halted() is False
    cue = synth.trigger_cue(AudioCueType.SUBTLE_CHIME)
    assert cue.cue_type == AudioCueType.SUBTLE_CHIME


def test_local_webrtc_mirror_lifecycle():
    """Verify WebRTC session initialization, local enforcement, and termination."""
    mirror = LocalWebRTCMirror()

    # Init
    session = mirror.init_session(device_id="companion_tablet", fps_target=30, resolution="1920x1080")
    assert session.device_id == "companion_tablet"
    assert session.local_only is True
    assert session.is_connected is True
    assert len(mirror.get_active_sessions()) == 1

    # Terminate
    terminated = mirror.terminate_session(session.session_id)
    assert terminated is True
    assert len(mirror.get_active_sessions()) == 0


def test_local_webrtc_mirror_guardian_halt():
    """Verify WebRTC mirror tears down all active streams on halt."""
    mirror = LocalWebRTCMirror()
    s = mirror.init_session(device_id="phone_1")
    assert len(mirror.get_active_sessions()) == 1

    mirror.halt()
    assert mirror.is_halted() is True
    assert len(mirror.get_active_sessions()) == 0

    with pytest.raises(PermissionError, match="WebRTC streaming halted"):
        mirror.init_session(device_id="phone_2")

    mirror.reset()
    assert mirror.is_halted() is False
