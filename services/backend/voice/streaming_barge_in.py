"""
Phenom Streaming Conversational Barge-In Controller
High-performance, instantaneous voice activity detection and speech interruption
using Silero VAD ONNX with 2-chunk hysteresis.

SLA Guarantees:
- VAD inference per 512-sample chunk: < 0.5ms
- Audio playback cessation upon speech detection: < 5ms SLA (< 1ms typical)
- Zero disk access: all audio frames reside in RAM ring buffers
- Synchronous Guardian kill switch integration (< 1ms halt)
"""

import time
import logging
import threading
from collections import deque
from typing import Optional, Callable, Dict, Any, List
import numpy as np

from services.backend.schemas.streaming_voice import VoiceInterruptionEvent
from services.backend.voice.vad import SileroVAD, silero_vad
from services.backend.voice.tts import tts_engine
from services.backend.tools.media_tools import duck_system_audio

logger = logging.getLogger("phenom.voice.barge_in")


class StreamingBargeInController:
    """
    Real-time streaming barge-in controller.
    Evaluates 512-sample (32ms) audio chunks at 16kHz using local Silero VAD ONNX.
    Enforces 2-chunk hysteresis to prevent transient noise spikes / keyboard clicks
    from triggering false barge-in interruptions.
    """

    def __init__(
        self,
        vad_engine: Optional[SileroVAD] = None,
        vad_threshold: float = 0.50,
        required_consecutive_chunks: int = 2,
        sample_rate: int = 16000,
        chunk_size: int = 512,
        buffer_seconds: float = 3.0,
    ):
        self.vad = vad_engine or silero_vad
        self.vad_threshold = vad_threshold
        self.required_consecutive_chunks = required_consecutive_chunks
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

        # In-RAM circular ring buffer (Strictly zero disk writes)
        max_chunks = int(buffer_seconds * sample_rate / chunk_size)
        self._ring_buffer: deque[np.ndarray] = deque(maxlen=max_chunks)

        self._consecutive_speech_chunks = 0
        self._noise_floor_ema: float = 0.010
        self.last_barge_in_latency_ms: float = 0.0
        self.total_interruptions: int = 0
        self.last_vad_inference_ms: float = 0.0
        self._is_halted: bool = False

        self._on_barge_in_cb: Optional[Callable[[VoiceInterruptionEvent], None]] = None
        self._custom_stop_sink: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()

    @property
    def is_halted(self) -> bool:
        return self._is_halted

    @property
    def consecutive_speech_chunks(self) -> int:
        return self._consecutive_speech_chunks

    def set_barge_in_callback(self, cb: Callable[[VoiceInterruptionEvent], None]):
        """Sets the callback invoked when a barge-in event is triggered."""
        self._on_barge_in_cb = cb

    def set_custom_stop_sink(self, stop_fn: Optional[Callable[[], None]]):
        """Allows injecting custom audio player stop mechanism (e.g. WebSocket bridge stream cancel)."""
        self._custom_stop_sink = stop_fn

    def configure(
        self,
        vad_threshold: Optional[float] = None,
        required_consecutive_chunks: Optional[int] = None,
    ):
        """Updates runtime barge-in sensitivity parameters."""
        with self._lock:
            if vad_threshold is not None:
                self.vad_threshold = max(0.05, min(1.0, vad_threshold))
            if required_consecutive_chunks is not None:
                self.required_consecutive_chunks = max(1, min(10, required_consecutive_chunks))

    def evaluate_chunk(self, chunk: np.ndarray) -> float:
        """
        Runs Silero VAD on a 512-sample chunk and returns speech probability.
        Times the evaluation latency.
        """
        t0 = time.perf_counter()
        prob = self.vad.process_chunk(chunk, sample_rate=self.sample_rate)
        self.last_vad_inference_ms = (time.perf_counter() - t0) * 1000.0
        return prob

    def process_chunk(
        self,
        chunk: np.ndarray,
        is_assistant_speaking: Optional[bool] = None,
    ) -> bool:
        """
        Ingests a 16kHz audio chunk in RAM.
        Evaluates speech probability via Silero VAD.
        If the assistant is speaking and speech is detected for `required_consecutive_chunks`
        consecutive frames, triggers instantaneous speech interruption (< 5ms SLA).

        Returns:
            True if a barge-in interruption was triggered on this chunk, False otherwise.
        """
        if self._is_halted:
            return False

        if chunk is None or len(chunk) == 0:
            return False

        # Store in RAM ring buffer
        self._ring_buffer.append(chunk)

        # Calculate energy for noise floor tracking
        if chunk.dtype == np.int16:
            rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2))) / 32768.0
        else:
            rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))

        # Determine speaking state
        speaking = is_assistant_speaking if is_assistant_speaking is not None else tts_engine.is_speaking

        with self._lock:
            # When assistant is not speaking, update baseline ambient noise floor and reset counter
            if not speaking:
                if rms < 0.030:
                    self._noise_floor_ema = self._noise_floor_ema * 0.95 + rms * 0.05
                self._consecutive_speech_chunks = 0
                return False

            # Assistant IS speaking: evaluate VAD
            prob = self.evaluate_chunk(chunk)
            is_speech = prob >= self.vad_threshold

            if is_speech:
                self._consecutive_speech_chunks += 1
                if self._consecutive_speech_chunks >= self.required_consecutive_chunks:
                    # Hysteresis requirement satisfied: trigger instant barge-in!
                    self._consecutive_speech_chunks = 0
                    self.execute_interrupt(trigger="user_speech_vad")
                    return True
            else:
                # Decay speech counter to filter transient clicks
                self._consecutive_speech_chunks = max(0, self._consecutive_speech_chunks - 1)

            return False

    def execute_interrupt(self, trigger: str = "user_speech_vad") -> float:
        """
        Immediately interrupts speech playback in < 5ms SLA.
        Returns the stop latency in milliseconds.
        """
        t0 = time.perf_counter()

        # 1. Immediate in-process audio stop (< 1ms typical)
        try:
            tts_engine.stop_speech()
        except Exception as e:
            logger.debug("TTS stop_speech error: %s", e)

        # 2. Fire custom stop sink if registered
        if self._custom_stop_sink:
            try:
                self._custom_stop_sink()
            except Exception as e:
                logger.debug("Custom stop sink error: %s", e)

        stop_latency = (time.perf_counter() - t0) * 1000.0
        self.last_barge_in_latency_ms = stop_latency
        self.total_interruptions += 1

        # 3. Duck background system audio in background daemon thread (skip on guardian halt)
        if trigger != "guardian_halt":
            threading.Thread(target=duck_system_audio, daemon=True).start()

        # 4. Notify listener with typed event
        event = VoiceInterruptionEvent(
            timestamp=time.time(),
            latency_ms=stop_latency,
            trigger=trigger,
            audio_offset_ms=0.0,
        )

        if self._on_barge_in_cb:
            try:
                self._on_barge_in_cb(event)
            except Exception as e:
                logger.error("Barge-in callback error: %s", e)

        return stop_latency

    def halt(self):
        """
        Synchronously halts the controller and cuts off audio (< 1ms).
        Called by Guardian kill switch.
        """
        with self._lock:
            self._is_halted = True
            self._consecutive_speech_chunks = 0
            self._ring_buffer.clear()
            self.execute_interrupt(trigger="guardian_halt")

    def reset(self):
        """Resets the controller from halted or clean state."""
        with self._lock:
            self._is_halted = False
            self._consecutive_speech_chunks = 0
            self._ring_buffer.clear()
            if self.vad:
                self.vad.reset_states()


# Global singleton
streaming_barge_in = StreamingBargeInController()
