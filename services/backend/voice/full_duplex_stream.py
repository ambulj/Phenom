"""Low-Latency Full-Duplex Audio Stream Manager for Phenom Voice.

Phase 48-03: VOICE-01.
Maintains sub-300ms roundtrip audio streaming, RAM-only circular buffers,
Voice Activity Detection (VAD), and turn-taking state synchronization.
"""

from __future__ import annotations

from collections import deque
import logging
import time
from typing import Any, Callable, Deque, Dict, List, Optional
import numpy as np

from services.backend.schemas.voice_duplex import (
    BargeInEvent,
    DuplexAudioMetrics,
    DuplexStreamState,
)
from services.backend.voice.barge_in_handler import BargeInSoftMuteHandler

logger = logging.getLogger("phenom.voice.full_duplex_stream")


class FullDuplexStreamManager:
    """Manages low-latency bi-directional audio streams, VAD gating, and turn state."""

    SAMPLE_RATE: int = 16000
    CHUNK_SIZE: int = 512  # 32ms per chunk
    ROUNDTRIP_SLA_MS: float = 300.0

    def __init__(
        self,
        barge_in_handler: Optional[BargeInSoftMuteHandler] = None,
        vad_threshold: float = 0.40,
        buffer_seconds: float = 3.0,
    ) -> None:
        self.barge_in = barge_in_handler or BargeInSoftMuteHandler()
        self.vad_threshold = vad_threshold
        self.buffer_seconds = buffer_seconds

        # In-RAM circular ring buffer (zero disk writes per Rule 4)
        max_chunks = int(buffer_seconds * self.SAMPLE_RATE / self.CHUNK_SIZE)
        self._ring_buffer: Deque[np.ndarray] = deque(maxlen=max_chunks)

        self.state: DuplexStreamState = DuplexStreamState.LISTENING
        self._last_vad_prob: float = 0.0
        self._consecutive_speech: int = 0
        self._consecutive_silence: int = 0
        self.total_frames: int = 0
        self.last_roundtrip_ms: float = 0.0

    def compute_energy_vad(self, chunk: np.ndarray) -> float:
        """Lightweight, ultra-fast energy-based speech probability (0.0 to 1.0)."""
        if len(chunk) == 0:
            return 0.0
        rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2))
        # Normalized mapping: rms in [150, 1800] maps to [0.0, 1.0]
        prob = max(0.0, min(1.0, (rms - 150.0) / 1650.0))
        return float(prob)

    def process_input_frame(
        self,
        frame: bytes | np.ndarray,
        simulated_transcript: Optional[str] = None,
    ) -> DuplexStreamState:
        """Process incoming 16kHz audio frame, calculate VAD, and manage state transitions."""
        t_start = time.perf_counter()

        if isinstance(frame, bytes):
            audio = np.frombuffer(frame, dtype=np.int16)
        else:
            audio = frame

        self._ring_buffer.append(audio)
        self.total_frames += 1

        vad_prob = self.compute_energy_vad(audio)
        self._last_vad_prob = vad_prob
        is_speech = vad_prob >= self.vad_threshold

        if is_speech:
            self._consecutive_speech += 1
            self._consecutive_silence = 0
        else:
            self._consecutive_silence += 1
            self._consecutive_speech = 0

        # Speech onset: 2 consecutive speech frames (~64ms)
        if self._consecutive_speech >= 2:
            if self.state == DuplexStreamState.AGENT_SPEAKING or self.barge_in.is_tts_playing:
                # User interrupted while agent was speaking -> Execute instant soft-mute!
                self.barge_in.trigger_soft_mute(transcript=simulated_transcript)
                self.state = DuplexStreamState.SOFT_MUTED
            elif self.state in (DuplexStreamState.LISTENING, DuplexStreamState.IDLE):
                self.state = DuplexStreamState.USER_SPEAKING

        elif self._consecutive_silence >= 10:  # ~320ms silence hangover
            if self.state == DuplexStreamState.USER_SPEAKING:
                self.state = DuplexStreamState.PROCESSING
            elif self.state == DuplexStreamState.SOFT_MUTED:
                self.state = DuplexStreamState.PROCESSING
            elif self.state == DuplexStreamState.PROCESSING:
                self.state = DuplexStreamState.LISTENING

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        self.last_roundtrip_ms = round(elapsed_ms, 2)

        return self.state

    def set_agent_speaking(self, is_speaking: bool) -> None:
        """Signal whether TTS is actively outputting speech."""
        self.barge_in.is_tts_playing = is_speaking
        if is_speaking:
            self.state = DuplexStreamState.AGENT_SPEAKING
            self.barge_in.reset_output_gain()
        elif self.state == DuplexStreamState.AGENT_SPEAKING:
            self.state = DuplexStreamState.LISTENING

    def get_metrics(self) -> DuplexAudioMetrics:
        """Retrieve real-time telemetry metrics."""
        return DuplexAudioMetrics(
            roundtrip_latency_ms=self.last_roundtrip_ms,
            vad_probability=round(self._last_vad_prob, 2),
            tts_playing=self.barge_in.is_tts_playing,
            user_speaking=(self.state == DuplexStreamState.USER_SPEAKING),
            soft_muted=(self.state == DuplexStreamState.SOFT_MUTED),
            total_barge_ins=self.barge_in.total_barge_ins,
            last_barge_in_ms=self.barge_in.last_latency_ms,
            state=self.state,
        )
