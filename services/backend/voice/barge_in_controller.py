"""
Phenom Conversational Barge-In Controller
Detects user voice activity while the assistant is speaking and triggers
instantaneous audio cancellation (< 50ms stop latency) and state transition.
"""

import time
import threading
from typing import Optional, Callable
import numpy as np
from services.backend.voice.tts import tts_engine
from services.backend.tools.media_tools import duck_system_audio


class BargeInController:
    def __init__(self, energy_threshold: float = 0.040, required_chunks: int = 2):
        self.energy_threshold = energy_threshold
        self.required_chunks = required_chunks
        self._consecutive_speech_chunks = 0
        self._noise_floor_ema = 0.010
        self.last_interrupt_latency_ms: float = 0.0
        self.interrupt_count: int = 0
        self._on_barge_in_callback: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()

    def set_barge_in_callback(self, cb: Callable[[], None]):
        self._on_barge_in_callback = cb

    def process_audio_chunk(self, audio_chunk: np.ndarray) -> bool:
        """
        Processes an incoming microphone audio chunk (16kHz).
        If TTS is currently speaking and user voice energy is detected,
        immediately interrupts speech playback (< 50ms).
        Returns True if a barge-in interruption was triggered, False otherwise.
        """
        if audio_chunk is None or len(audio_chunk) == 0:
            return False

        if audio_chunk.dtype == np.int16:
            rms = float(np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))) / 32768.0
        else:
            rms = float(np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2)))

        with self._lock:
            if not tts_engine.is_speaking:
                # Update baseline ambient noise floor when quiet
                if rms < 0.030:
                    self._noise_floor_ema = self._noise_floor_ema * 0.95 + rms * 0.05
                self._consecutive_speech_chunks = 0
                return False

            # Assistant IS speaking: check for user voice interruption
            is_speech = (rms > self.energy_threshold) and (rms > self._noise_floor_ema * 2.2)

            if is_speech:
                self._consecutive_speech_chunks += 1
                if self._consecutive_speech_chunks >= self.required_chunks:
                    # Trigger instant barge-in
                    return self._execute_interrupt()
            else:
                self._consecutive_speech_chunks = max(0, self._consecutive_speech_chunks - 1)

            return False

    def interrupt_now(self) -> float:
        """
        Forces an immediate barge-in interruption.
        Returns the stop latency in milliseconds.
        """
        with self._lock:
            self._execute_interrupt()
            return self.last_interrupt_latency_ms

    def _execute_interrupt(self) -> bool:
        start_time = time.perf_counter()
        
        # 1. Stop TTS speech immediately (< 5ms)
        tts_engine.stop_speech()
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        self.last_interrupt_latency_ms = elapsed_ms
        self.interrupt_count += 1
        self._consecutive_speech_chunks = 0

        # 2. Duck background system audio asynchronously so it doesn't block interrupt SLA
        threading.Thread(target=duck_system_audio, daemon=True).start()

        # 3. Fire callback (e.g. notify UI and switch state to listening)
        if self._on_barge_in_callback:
            try:
                self._on_barge_in_callback()
            except Exception:
                pass

        return True


barge_in_controller = BargeInController()
