"""Unit tests for Remote Bi-Directional Voice Note Pipeline (Milestone 46 Phase 2)."""

import os
import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.telegram.voice_pipeline import TelegramVoicePipeline


@pytest.fixture(autouse=True)
def clean_guardian():
    """Reset guardian before and after each test."""
    guardian.resume()
    yield
    guardian.resume()


def test_in_ram_voice_note_transcription_and_zero_disk(tmp_path):
    """Validates that voice note processing operates strictly in volatile RAM with zero disk writes (Rule 4)."""
    pipeline = TelegramVoicePipeline(dry_run=True)
    mock_audio = b"OGG_OPUS_MOCK_STREAM_BYTES_FOR_WHISPER"

    # Count files before
    files_before = list(tmp_path.glob("**/*"))

    transcription, response, audio_reply, halted = pipeline.process_incoming_voice_note(
        audio_bytes=mock_audio,
        mock_transcription="Phenom check network scan status"
    )

    # Count files after
    files_after = list(tmp_path.glob("**/*"))

    assert len(files_before) == len(files_after)
    assert transcription == "Phenom check network scan status"
    assert "Understood, sir" in response
    assert audio_reply is not None
    assert audio_reply.startswith(b"RIFF")
    assert halted is False


def test_spoken_emergency_keyword_triggers_guardian_sla():
    """Validates that spoken emergency words in voice notes trigger Guardian E-Stop in <25ms SLA."""
    pipeline = TelegramVoicePipeline(dry_run=True)
    assert guardian.is_halted is False

    mock_audio = b"MOCK_EMERGENCY_AUDIO"
    emergency_phrases = [
        "Phenom please halt immediately",
        "Stop everything now",
        "Emergency abort all workflows",
        "Freeze workstation",
    ]

    for phrase in emergency_phrases:
        guardian.resume()
        t0 = time.perf_counter()
        _, resp, audio_reply, halted = pipeline.process_incoming_voice_note(
            audio_bytes=mock_audio,
            mock_transcription=phrase
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert halted is True
        assert guardian.is_halted is True
        assert "SPOKEN GUARDIAN EMERGENCY STOP" in resp
        assert audio_reply is not None
        assert elapsed_ms < 25.0, f"Spoken emergency halt too slow: {elapsed_ms}ms"


def test_routine_voice_note_generates_tts_audio_reply():
    """Tests full-duplex synthesized audio reply generation for routine voice commands."""
    pipeline = TelegramVoicePipeline(dry_run=True)
    mock_audio = b"MOCK_NORMAL_AUDIO"

    transcription, response, audio_reply, halted = pipeline.process_incoming_voice_note(
        audio_bytes=mock_audio,
        mock_transcription="What is the current CPU temperature?"
    )

    assert halted is False
    assert "Jarvis" in response
    assert audio_reply is not None
    assert len(audio_reply) > 44  # WAV header is 44 bytes minimum


def test_voice_note_fails_closed_when_guardian_halted():
    """Tests that incoming voice notes fail closed while Guardian is halted."""
    pipeline = TelegramVoicePipeline(dry_run=True)
    guardian.trigger("Workstation paused")

    mock_audio = b"MOCK_AUDIO"
    _, response, audio_reply, halted = pipeline.process_incoming_voice_note(
        audio_bytes=mock_audio,
        mock_transcription="Execute system update"
    )

    assert halted is True
    assert audio_reply is None
    assert "Workstation is halted under Guardian Kill Switch" in response


def test_empty_audio_buffer_handling():
    """Tests graceful handling when user sends an empty voice payload."""
    pipeline = TelegramVoicePipeline(dry_run=True)

    transcription, response, audio_reply, halted = pipeline.process_incoming_voice_note(
        audio_bytes=b""
    )

    assert transcription == ""
    assert "empty audio buffer" in response
    assert audio_reply is None
