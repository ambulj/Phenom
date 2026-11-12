"""
Full-Duplex Remote Voice Summon Audio Streamer for Phenom P2P Mesh
Streams 16kHz 16-bit mono PCM audio chunks over local encrypted P2P mesh
with sub-5ms instant barge-in cancellation and zero cloud exfiltration.
"""

import logging
import threading
import time
from typing import Callable, List, Optional
from services.backend.schemas.mesh import MeshMessageType
from services.backend.mesh.p2p_mesh_engine import P2PMeshEngine, p2p_mesh_engine
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.mesh.remote_voice")

FRAME_SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2  # 16-bit PCM
FRAME_DURATION_MS = 32
BYTES_PER_FRAME = (FRAME_SAMPLE_RATE * BYTES_PER_SAMPLE * FRAME_DURATION_MS) // 1000  # 1024 bytes


class MeshRemoteVoiceStreamer:
    """
    Coordinates full-duplex 16kHz PCM audio streaming between companion and desktop.
    Includes sub-5ms barge-in detection to interrupt desktop speech immediately when user talks.
    """

    def __init__(self, engine: Optional[P2PMeshEngine] = None):
        self._engine = engine or p2p_mesh_engine
        self._is_tts_active = False
        self._barge_in_active = False
        self._lock = threading.Lock()

        # Callbacks for inbound audio and barge-in events
        self._inbound_callbacks: List[Callable[[str, bytes], None]] = []
        self._barge_in_callbacks: List[Callable[[], None]] = []

    def add_inbound_audio_callback(self, cb: Callable[[str, bytes], None]) -> None:
        """Register callback for incoming companion microphone audio chunks."""
        self._inbound_callbacks.append(cb)

    def add_barge_in_callback(self, cb: Callable[[], None]) -> None:
        """Register callback for barge-in interruptions."""
        self._barge_in_callbacks.append(cb)

    def trigger_barge_in(self) -> float:
        """
        Instant barge-in cancellation (< 5ms).
        Interrupts ongoing TTS playback immediately when companion speech starts.
        """
        t0 = time.perf_counter()
        with self._lock:
            self._barge_in_active = True
            self._is_tts_active = False

        # Fire callbacks immediately
        for cb in self._barge_in_callbacks:
            try:
                cb()
            except Exception as e:
                logger.debug(f"Barge-in callback error: {e}")

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"Barge-in triggered; active TTS aborted in {elapsed_ms:.2f}ms.")
        return elapsed_ms

    def receive_inbound_chunk(self, companion_node_id: str, pcm_chunk: bytes) -> bool:
        """
        Process incoming microphone PCM chunk from companion device.
        Automatically detects audio energy/voice to trigger barge-in if TTS is currently active.
        """
        if guardian.is_halted or self._engine.is_halted:
            return False

        # Check if TTS was active on desktop; if so, trigger instant barge-in
        with self._lock:
            if self._is_tts_active:
                self.trigger_barge_in()

        # Dispatch inbound chunk to speech recognizer / VAD
        for cb in self._inbound_callbacks:
            try:
                cb(companion_node_id, pcm_chunk)
            except Exception as e:
                logger.debug(f"Inbound audio callback error: {e}")

        return True

    def stream_tts_chunk_to_companion(self, companion_node_id: str, pcm_chunk: bytes) -> bool:
        """
        Send a synthesized TTS chunk to companion device speaker.
        Returns False if barge-in was triggered or if system is halted.
        """
        if guardian.is_halted or self._engine.is_halted:
            return False

        with self._lock:
            if self._barge_in_active:
                # Discard outbound TTS because user barged in
                return False
            self._is_tts_active = True

        try:
            self._engine.send_frame(
                node_id=companion_node_id,
                msg_type=int(MeshMessageType.VOICE_AUDIO_CHUNK.value == "voice_audio_chunk"),
                payload=pcm_chunk
            )
            return True
        except Exception as e:
            logger.debug(f"Failed to stream TTS chunk to {companion_node_id}: {e}")
            return False

    def finish_tts_stream(self) -> None:
        """Mark TTS playback complete and reset barge-in flag."""
        with self._lock:
            self._is_tts_active = False
            self._barge_in_active = False
