"""
Phenom Full-Duplex Voice Pipeline
Manages continuous in-RAM microphone audio ingestion, Silero VAD speech activity detection,
natural conversational turn-taking, and instantaneous barge-in interruption (< 50ms stop latency).
Strictly adheres to the zero-disk audio invariant (audio buffers maintained purely in RAM).
"""

import time
import threading
from collections import deque
from enum import Enum
from typing import Optional, Callable, Dict, Any, List
import numpy as np

from services.backend.voice.vad import silero_vad
from services.backend.voice.tts import tts_engine
from services.backend.tools.media_tools import duck_system_audio, unduck_system_audio

CHUNK_SIZE = 512  # 32ms at 16kHz
SAMPLE_RATE = 16000


class DuplexState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    HALTED = "halted"


class FullDuplexVoicePipeline:
    """
    Sub-300ms turn-taking full-duplex conversational audio pipeline.
    Maintains circular in-RAM audio buffers, triggers Silero VAD voice activity detection,
    and executes sub-50ms barge-in speech interruption.
    """

    def __init__(
        self,
        speech_prob_threshold: float = 0.50,
        barge_in_chunks_required: int = 2,
        turn_end_silence_chunks: int = 15,  # ~480ms silence
        max_buffer_seconds: float = 5.0,
    ):
        self.speech_prob_threshold = speech_prob_threshold
        self.barge_in_chunks_required = barge_in_chunks_required
        self.turn_end_silence_chunks = turn_end_silence_chunks
        self.max_buffer_chunks = int(max_buffer_seconds * SAMPLE_RATE / CHUNK_SIZE)

        self._state = DuplexState.IDLE
        self._is_running = False
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # In-RAM circular audio ring buffer (ZERO disk persistence)
        self._ring_buffer: deque[np.ndarray] = deque(maxlen=self.max_buffer_chunks)
        self._utterance_chunks: List[np.ndarray] = []

        # Turn-taking tracking counters
        self._consecutive_speech_chunks = 0
        self._consecutive_silence_chunks = 0
        self._in_user_speech = False

        # Latency and metrics
        self.last_turn_taking_latency_ms: float = 0.0
        self.last_barge_in_latency_ms: float = 0.0
        self.total_barge_in_interruptions: int = 0
        self.total_turns_completed: int = 0
        self._speech_detected_ts: float = 0.0

        # Callbacks
        self._on_turn_completed_cb: Optional[Callable[[np.ndarray], None]] = None
        self._on_barge_in_cb: Optional[Callable[[], None]] = None
        self._on_state_change_cb: Optional[Callable[[DuplexState], None]] = None

    @property
    def state(self) -> DuplexState:
        with self._lock:
            return self._state

    def set_on_turn_completed(self, cb: Callable[[np.ndarray], None]):
        self._on_turn_completed_cb = cb

    def set_on_barge_in(self, cb: Callable[[], None]):
        self._on_barge_in_cb = cb

    def set_on_state_change(self, cb: Callable[[DuplexState], None]):
        self._on_state_change_cb = cb

    def _set_state(self, new_state: DuplexState):
        if self._state != new_state:
            self._state = new_state
            if self._on_state_change_cb:
                try:
                    self._on_state_change_cb(new_state)
                except Exception:
                    pass

    def start(self):
        """Starts the duplex pipeline in LISTENING mode."""
        with self._lock:
            self._stop_event.clear()
            self._is_running = True
            self._ring_buffer.clear()
            self._utterance_chunks.clear()
            self._consecutive_speech_chunks = 0
            self._consecutive_silence_chunks = 0
            self._in_user_speech = False
            self._set_state(DuplexState.LISTENING)

    def stop(self):
        """Gracefully stops the duplex pipeline."""
        with self._lock:
            self._stop_event.set()
            self._is_running = False
            self._set_state(DuplexState.IDLE)

    def halt(self) -> float:
        """
        Synchronous emergency halt invoked by Guardian kill switch (< 25ms SLA).
        Instantly halts all audio processing, purges buffers, and silences speech.
        Note: TTS engine stop_speech() is invoked by Guardian callback.
        """
        t0 = time.perf_counter()
        with self._lock:
            self._stop_event.set()
            self._is_running = False
            self._ring_buffer.clear()
            self._utterance_chunks.clear()
            self._consecutive_speech_chunks = 0
            self._consecutive_silence_chunks = 0
            self._in_user_speech = False
            self._set_state(DuplexState.HALTED)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return elapsed_ms

    def feed_audio_chunk(self, chunk: np.ndarray) -> Dict[str, Any]:
        """
        Processes an incoming 16kHz audio chunk (512 samples) in RAM.
        Can be invoked from sounddevice callback or unit tests.
        Returns evaluation dict with speech probability, state, and barge_in event.
        """
        if self._stop_event.is_set() or not self._is_running:
            return {
                "status": "halted_or_stopped",
                "state": self._state.value,
                "in_user_speech": False,
                "turn_completed": False,
                "barge_in": False,
            }

        if chunk is None or len(chunk) == 0:
            return {
                "status": "empty_chunk",
                "state": self._state.value,
                "in_user_speech": False,
                "turn_completed": False,
                "barge_in": False,
            }

        # Store in RAM ring buffer (ZERO disk persistence)
        self._ring_buffer.append(chunk)

        # Check speech with Silero VAD
        speech_prob = silero_vad.process_chunk(chunk)
        is_speech = speech_prob >= self.speech_prob_threshold

        barge_in_triggered = False
        turn_completed = False

        with self._lock:
            # Check for BARGE-IN INTERRUPTION if assistant is actively speaking
            if tts_engine.is_speaking or self._state == DuplexState.SPEAKING:
                if is_speech:
                    self._consecutive_speech_chunks += 1
                    if self._consecutive_speech_chunks >= self.barge_in_chunks_required:
                        # User interrupted the assistant!
                        barge_in_triggered = True
                        interrupt_latency = self._execute_barge_in()
                        return {
                            "status": "barge_in_interrupted",
                            "speech_prob": speech_prob,
                            "barge_in_latency_ms": interrupt_latency,
                            "state": self._state.value,
                            "in_user_speech": True,
                            "turn_completed": False,
                            "barge_in": True,
                        }
                else:
                    self._consecutive_speech_chunks = max(0, self._consecutive_speech_chunks - 1)
                return {
                    "status": "assistant_speaking",
                    "speech_prob": speech_prob,
                    "state": self._state.value,
                    "in_user_speech": False,
                    "turn_completed": False,
                    "barge_in": False,
                }

            # Normal Conversational Turn-Taking (User Speaking / Listening)
            if is_speech:
                self._consecutive_speech_chunks += 1
                self._consecutive_silence_chunks = 0

                if not self._in_user_speech and self._consecutive_speech_chunks >= 2:
                    self._in_user_speech = True
                    self._speech_detected_ts = time.perf_counter()
                    self._set_state(DuplexState.LISTENING)
                    self._utterance_chunks.clear()
                    # Pre-roll past 3 chunks from ring buffer for seamless phoneme onset
                    preroll = list(self._ring_buffer)[-4:]
                    self._utterance_chunks.extend(preroll)

                if self._in_user_speech:
                    self._utterance_chunks.append(chunk)

            else:
                self._consecutive_speech_chunks = 0
                if self._in_user_speech:
                    self._utterance_chunks.append(chunk)
                    self._consecutive_silence_chunks += 1

                    # End of turn detected (consecutive silence exceeded threshold)
                    if self._consecutive_silence_chunks >= self.turn_end_silence_chunks:
                        self._in_user_speech = False
                        turn_completed = True
                        now = time.perf_counter()
                        self.last_turn_taking_latency_ms = (now - self._speech_detected_ts) * 1000.0
                        self.total_turns_completed += 1
                        self._set_state(DuplexState.THINKING)

        if turn_completed and self._on_turn_completed_cb and self._utterance_chunks:
            full_audio = np.concatenate(self._utterance_chunks)
            try:
                self._on_turn_completed_cb(full_audio)
            except Exception:
                pass

        return {
            "status": "ok",
            "speech_prob": speech_prob,
            "in_user_speech": self._in_user_speech,
            "turn_completed": turn_completed,
            "barge_in": barge_in_triggered,
            "state": self._state.value,
        }

    def _execute_barge_in(self) -> float:
        """Executes instant barge-in interruption (< 50ms stop latency SLA)."""
        t0 = time.perf_counter()
        
        # 1. Purge and silence TTS immediately (< 5ms)
        tts_engine.stop_speech()
        
        # 2. Reset turn tracking and transition back to LISTENING
        self._consecutive_speech_chunks = 0
        self._consecutive_silence_chunks = 0
        self._in_user_speech = True
        self._speech_detected_ts = time.perf_counter()
        self._utterance_chunks.clear()
        preroll = list(self._ring_buffer)[-4:]
        self._utterance_chunks.extend(preroll)
        self._set_state(DuplexState.LISTENING)

        latency_ms = (time.perf_counter() - t0) * 1000.0
        self.last_barge_in_latency_ms = latency_ms
        self.total_barge_in_interruptions += 1

        # Duck system audio asynchronously
        threading.Thread(target=duck_system_audio, daemon=True).start()

        if self._on_barge_in_cb:
            try:
                self._on_barge_in_cb()
            except Exception:
                pass

        return latency_ms

    def get_metrics(self) -> Dict[str, Any]:
        """Returns runtime performance and duplex statistics."""
        with self._lock:
            return {
                "state": self._state.value,
                "is_running": self._is_running,
                "ring_buffer_chunks": len(self._ring_buffer),
                "last_turn_taking_latency_ms": round(self.last_turn_taking_latency_ms, 2),
                "last_barge_in_latency_ms": round(self.last_barge_in_latency_ms, 2),
                "total_barge_ins": self.total_barge_in_interruptions,
                "total_turns": self.total_turns_completed,
                "silero_vad_available": silero_vad.is_available,
                "speech_prob_threshold": self.speech_prob_threshold,
            }


# Global singleton instance
duplex_pipeline = FullDuplexVoicePipeline()
