"""
Unit tests for Full-Duplex Remote Voice Streamer and Sub-5ms Barge-In
Verifies inbound and outbound 16kHz PCM audio chunk transmission,
instant barge-in cancellation (< 5ms), and Guardian halt enforcement.
"""

import os
from services.backend.mesh.crypto import MeshCryptoEngine
from services.backend.mesh.p2p_mesh_engine import P2PMeshEngine
from services.backend.mesh.remote_voice import MeshRemoteVoiceStreamer
from services.backend.safety.guardian import GuardianKillSwitch


def test_remote_voice_streaming_and_barge_in(tmp_path):
    guardian = GuardianKillSwitch()
    engine = P2PMeshEngine(
        node_id="desktop-host",
        guardian=guardian,
        registry_path=str(tmp_path / "devices.json")
    )

    # Register active session
    key = os.urandom(32)
    engine.register_session("companion-phone", MeshCryptoEngine(key=key))

    streamer = MeshRemoteVoiceStreamer(engine=engine)

    received_inbound = []
    barge_in_fired = []

    streamer.add_inbound_audio_callback(lambda nid, chunk: received_inbound.append((nid, chunk)))
    streamer.add_barge_in_callback(lambda: barge_in_fired.append(True))

    mock_pcm_chunk = b"\x00\x01" * 512  # 1024 bytes (16kHz 16-bit 32ms)

    # 1. Normal inbound chunk without TTS active
    ok = streamer.receive_inbound_chunk("companion-phone", mock_pcm_chunk)
    assert ok is True
    assert len(received_inbound) == 1
    assert len(barge_in_fired) == 0

    # 2. Outbound TTS stream starts
    tts_sent = streamer.stream_tts_chunk_to_companion("companion-phone", mock_pcm_chunk)
    assert tts_sent is True
    assert streamer._is_tts_active is True

    # 3. Companion speaks (inbound chunk arrives while TTS is active) -> Instant Barge-in (< 5ms)
    elapsed_ms = streamer.trigger_barge_in()
    assert elapsed_ms < 5.0
    assert len(barge_in_fired) == 1
    assert streamer._barge_in_active is True
    assert streamer._is_tts_active is False

    # 4. Outbound TTS chunk must now be dropped because user barged in
    subsequent_tts = streamer.stream_tts_chunk_to_companion("companion-phone", mock_pcm_chunk)
    assert subsequent_tts is False

    # 5. Finish TTS stream resets barge-in
    streamer.finish_tts_stream()
    assert streamer._barge_in_active is False


def test_remote_voice_guardian_halt(tmp_path):
    guardian = GuardianKillSwitch()
    engine = P2PMeshEngine(
        node_id="desktop-host",
        guardian=guardian,
        registry_path=str(tmp_path / "devices.json")
    )
    streamer = MeshRemoteVoiceStreamer(engine=engine)
    mock_pcm_chunk = b"\x00\x00" * 512

    guardian.trigger("halt_voice_test")

    # Inbound and outbound audio must be rejected when halted
    assert streamer.receive_inbound_chunk("phone", mock_pcm_chunk) is False
    assert streamer.stream_tts_chunk_to_companion("phone", mock_pcm_chunk) is False
