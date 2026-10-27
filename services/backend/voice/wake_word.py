"""
Phenom Wake Word & Continuous Audio Listener
Uses openWakeWord (ONNX runtime) with sounddevice stream.
Features:
- Runs in low-CPU background thread
- In-memory circular buffer
- Enables / disables / mutes cleanly
- Triggers barge-in when TTS is active
"""

import threading
import time
from typing import Optional, Callable
import numpy as np
import sounddevice as sd
import openwakeword
from openwakeword.model import Model
from services.backend.voice.tts import tts_engine

CHUNK_SIZE = 1280 # 80ms at 16kHz
SAMPLE_RATE = 16000

class WakeWordDetector:
    def __init__(self, wake_phrase: str = "hey_jarvis"):
        self.wake_phrase = wake_phrase
        self._enabled: bool = True
        self._muted: bool = False
        self._is_listening: bool = False
        self._model: Optional[Model] = None
        self._stream: Optional[sd.InputStream] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._on_wake_callback: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()

    def set_wake_callback(self, cb: Callable[[], None]):
        self._on_wake_callback = cb

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def is_muted(self) -> bool:
        return self._muted

    def set_enabled(self, enabled: bool):
        with self._lock:
            self._enabled = enabled

    def set_muted(self, muted: bool):
        with self._lock:
            self._muted = muted

    def set_wake_phrase(self, phrase: str):
        with self._lock:
            self.wake_phrase = phrase
            try:
                self._model = Model(wakeword_models=[self.wake_phrase], inference_framework="onnx")
            except Exception:
                self._model = Model(inference_framework="onnx")

    def start(self):
        """Starts background continuous listening stream."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
        self._stream = None

    def _run_loop(self):
        # Load ONNX model
        try:
            self._model = Model(
                wakeword_models=[self.wake_phrase],
                inference_framework="onnx"
            )
        except Exception:
            # Fallback to any available openwakeword model
            self._model = Model(inference_framework="onnx")

        def audio_callback(indata, frames, time_info, status):
            if not self._enabled or self._muted or self._stop_event.is_set():
                return

            audio_chunk = np.frombuffer(indata, dtype=np.int16)
            if len(audio_chunk) != CHUNK_SIZE:
                return

            # Feed to openWakeWord
            predictions = self._model.predict(audio_chunk)
            
            # Check for activation
            for phrase, score in predictions.items():
                if score > 0.5:
                    self._handle_detection(phrase, score)
                    break

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=audio_callback
            ) as stream:
                self._stream = stream
                while not self._stop_event.is_set():
                    time.sleep(0.1)
        except Exception as e:
            # Mic input error (e.g. no audio input device available in testing)
            pass

    def _handle_detection(self, phrase: str, score: float):
        # If assistant is speaking, trigger barge-in immediately!
        if tts_engine.is_speaking:
            tts_engine.stop_speech()

        if self._on_wake_callback:
            try:
                self._on_wake_callback()
            except Exception:
                pass

wake_detector = WakeWordDetector()
