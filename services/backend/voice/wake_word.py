"""
Phenom Wake Word & Continuous Audio Listener
Uses openWakeWord (ONNX runtime) with sounddevice stream.
Features:
- Runs in low-CPU background thread
- In-memory circular buffer
- Enables / disables / mutes cleanly
- Triggers barge-in when TTS is active
- Records post-wake command audio in RAM and delivers to STT pipeline
- Integrates procedural wake chime and background music audio ducking
- Duplex follow-up listening mode for natural multi-turn conversations
"""

import threading
import time
from typing import Optional, Callable
import numpy as np
import sounddevice as sd
import openwakeword
from openwakeword.model import Model
from services.backend.voice.tts import tts_engine
from services.backend.voice.sound_fx import sound_fx
from services.backend.tools.media_tools import duck_system_audio, unduck_system_audio

CHUNK_SIZE = 1280  # 80ms at 16kHz
SAMPLE_RATE = 16000

class WakeWordDetector:
    def __init__(self, wake_phrase: str = "hey_jarvis", threshold: float = 0.20):
        self.wake_phrase = wake_phrase
        self.threshold = threshold
        self._enabled: bool = True
        self._muted: bool = False
        self._is_listening: bool = False
        self._model: Optional[Model] = None
        self._stream: Optional[sd.InputStream] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._on_wake_callback: Optional[Callable[[], None]] = None
        self._on_command_callback: Optional[Callable[[np.ndarray], None]] = None
        self._on_amplitude_callback: Optional[Callable[[float], None]] = None
        self._recording_command: bool = False
        self._command_chunks: list[np.ndarray] = []
        self._max_command_chunks: int = int(4.5 * SAMPLE_RATE / CHUNK_SIZE)  # ~4.5 seconds
        
        # Duplex Conversation State
        self._duplex_active: bool = False
        self._duplex_expiry_time: float = 0.0
        self._on_duplex_timeout_callback: Optional[Callable[[], None]] = None
        
        self._lock = threading.Lock()

    def set_wake_callback(self, cb: Callable[[], None]):
        self._on_wake_callback = cb

    def set_command_callback(self, cb: Callable[[np.ndarray], None]):
        self._on_command_callback = cb

    def set_amplitude_callback(self, cb: Callable[[float], None]):
        self._on_amplitude_callback = cb

    def set_duplex_timeout_callback(self, cb: Callable[[], None]):
        self._on_duplex_timeout_callback = cb

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

    def trigger_manual_listen(self, duration_seconds: float = 4.0):
        """Allows UI button or Push-to-Talk hotkey to trigger listening without wake word."""
        with self._lock:
            self._duplex_active = False
            self._recording_command = True
            self._command_chunks = []
            self._max_command_chunks = int(duration_seconds * SAMPLE_RATE / CHUNK_SIZE)
            
            sound_fx.play_wake_chime()
            duck_system_audio()

            if self._on_wake_callback:
                try:
                    self._on_wake_callback()
                except Exception:
                    pass

    def enter_duplex_followup_window(self, timeout_seconds: float = 5.0):
        """Enters duplex mode where follow-up speech triggers recording without the wake word."""
        with self._lock:
            self._duplex_active = True
            self._duplex_expiry_time = time.time() + timeout_seconds

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
            self._model = Model(inference_framework="onnx")

        def audio_callback(indata, frames, time_info, status):
            if not self._enabled or self._muted or self._stop_event.is_set():
                return

            audio_chunk = np.frombuffer(indata, dtype=np.int16)
            if len(audio_chunk) != CHUNK_SIZE:
                return

            # Compute audio RMS amplitude
            rms = float(np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))) / 32768.0
            if self._on_amplitude_callback:
                try:
                    self._on_amplitude_callback(min(1.0, rms * 8.0))
                except Exception:
                    pass

            # If actively recording user command audio after wake trigger
            if self._recording_command:
                self._command_chunks.append(audio_chunk.copy())
                if len(self._command_chunks) >= self._max_command_chunks:
                    self._recording_command = False
                    unduck_system_audio()
                    full_audio = np.concatenate(self._command_chunks)
                    self._command_chunks = []
                    if self._on_command_callback:
                        cb = self._on_command_callback
                        threading.Thread(target=cb, args=(full_audio,), daemon=True).start()
                return

            # If in Duplex Follow-up Window
            if self._duplex_active:
                if time.time() > self._duplex_expiry_time:
                    self._duplex_active = False
                    if self._on_duplex_timeout_callback:
                        try:
                            self._on_duplex_timeout_callback()
                        except Exception:
                            pass
                elif rms > 0.05:  # User started speaking during follow-up window!
                    self._duplex_active = False
                    self.trigger_manual_listen(4.5)
                    return

            # Predict wake word activation
            predictions = self._model.predict(audio_chunk)
            for phrase, score in predictions.items():
                if score >= self.threshold:
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
            print(f"[Phenom Wake Detector] Microphone stream notice: {e}")

    def _handle_detection(self, phrase: str, score: float):
        # Barge-in if speaking
        if tts_engine.is_speaking:
            tts_engine.stop_speech()

        print(f"[Phenom Wake Detector] Wake phrase '{phrase}' detected (score={score:.3f}). Recording command...")
        sound_fx.play_wake_chime()
        duck_system_audio()

        self._duplex_active = False
        self._recording_command = True
        self._command_chunks = []
        self._max_command_chunks = int(4.5 * SAMPLE_RATE / CHUNK_SIZE)

        if self._on_wake_callback:
            try:
                self._on_wake_callback()
            except Exception:
                pass

wake_detector = WakeWordDetector()
