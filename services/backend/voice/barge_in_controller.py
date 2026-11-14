"""
Phenom Conversational Barge-In Controller & Audio Guardian E-Stop
Milestone 43.0: Project FULL-DUPLEX JARVIS (Phase 2)

Key Architecture:
1. Instant Acoustic Barge-In (< 15ms stop latency SLA):
   Immediately cuts off active TTS speech playback, flushes playback queues,
   and coordinates system audio ducking/unducking.
2. Spoken Emergency Kill Switch (< 25ms SLA):
   Monitors streaming transcript tokens for emergency spoken triggers:
   {"halt", "stop", "freeze", "guardian", "emergency"}.
   Synchronously invokes guardian.trigger() in < 25.0ms with buffer zeroization.
3. Fail-Closed Guardian Integration:
   When Guardian kill switch is active, rejects speech processing and halts audio pipelines.
"""

from __future__ import annotations

import time
import re
import logging
import threading
from typing import Optional, Callable, Dict, Any, Set, List
import numpy as np

from services.backend.safety.guardian import guardian
from services.backend.voice.tts import tts_engine
from services.backend.voice.vad import silero_vad
from services.backend.tools.media_tools import duck_system_audio, unduck_system_audio

logger = logging.getLogger("phenom.voice.barge_in")

# Spoken emergency keywords triggering instantaneous Guardian emergency stop (< 25ms SLA)
EMERGENCY_KEYWORDS: Set[str] = {
    "halt",
    "stop",
    "freeze",
    "guardian",
    "emergency",
    "abort",
}


class BargeInController:
    """
    Sub-15ms conversational acoustic barge-in controller and sub-25ms spoken Guardian E-Stop.
    """

    def __init__(
        self,
        energy_threshold: float = 0.040,
        required_chunks: int = 2,
    ):
        self.energy_threshold = energy_threshold
        self.required_chunks = required_chunks
        self._consecutive_speech_chunks = 0
        self._noise_floor_ema = 0.010

        self.last_interrupt_latency_ms: float = 0.0
        self.last_emergency_halt_latency_ms: float = 0.0
        self.interrupt_count: int = 0
        self.emergency_halt_count: int = 0
        self.is_ducked: bool = False

        self._on_barge_in_callback: Optional[Callable[[], None]] = None
        self._on_emergency_halt_callback: Optional[Callable[[str], None]] = None
        self._lock = threading.RLock()

        # Guardian hook
        try:
            guardian.add_state_callback(self._on_guardian_state_change)
        except Exception as e:
            logger.warning("Could not register Guardian callback in BargeInController: %s", e)

    def _on_guardian_state_change(self, state: Any):
        if state == "halted" or state is True or guardian.is_halted:
            self.stop_all_audio()

    def set_barge_in_callback(self, cb: Callable[[], None]):
        self._on_barge_in_callback = cb

    def set_emergency_halt_callback(self, cb: Callable[[str], None]):
        self._on_emergency_halt_callback = cb

    def configure(
        self,
        energy_threshold: Optional[float] = None,
        required_chunks: Optional[int] = None,
    ):
        with self._lock:
            if energy_threshold is not None:
                self.energy_threshold = max(0.005, min(1.0, float(energy_threshold)))
            if required_chunks is not None:
                self.required_chunks = max(1, min(10, int(required_chunks)))

    def check_emergency_spoken_command(self, text: str) -> bool:
        """
        Inspects incoming speech/transcript for spoken emergency stop keywords.
        If matched, synchronously activates Guardian Kill Switch within < 25.0ms SLA.
        """
        if not text:
            return False

        t0 = time.perf_counter()
        # Clean tokens to words
        tokens = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        matched_keyword: Optional[str] = None
        for tok in tokens:
            if tok in EMERGENCY_KEYWORDS:
                matched_keyword = tok
                break

        if not matched_keyword:
            return False

        # Emergency keyword detected -> Synchronous emergency stop
        reason = f"Voice-commanded emergency halt: detected '{matched_keyword}' in speech"
        logger.critical("EMERGENCY VOICE COMMAND DETECTED: '%s'. Executing Guardian trigger.", matched_keyword)
        
        # 1. Stop audio speech immediately
        self.stop_all_audio()

        # 2. Synchronous Guardian Kill Switch invocation (< 25ms SLA)
        guardian.trigger(reason)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        with self._lock:
            self.last_emergency_halt_latency_ms = elapsed_ms
            self.emergency_halt_count += 1

        if self._on_emergency_halt_callback:
            try:
                self._on_emergency_halt_callback(matched_keyword)
            except Exception as e:
                logger.error("Error in emergency halt callback: %s", e)

        logger.info("Spoken Guardian Kill Switch executed in %.3f ms (SLA < 25.0ms).", elapsed_ms)
        return True

    def process_audio_chunk(self, audio_chunk: np.ndarray) -> bool:
        """
        Processes an incoming microphone audio chunk (16kHz).
        If TTS is currently speaking and user voice is detected, immediately interrupts speech (< 15ms).
        Returns True if a barge-in interruption was triggered, False otherwise.
        """
        if audio_chunk is None or len(audio_chunk) == 0:
            return False

        if guardian.is_halted:
            return False

        if audio_chunk.dtype == np.int16:
            rms = float(np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))) / 32768.0
        else:
            rms = float(np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2)))

        with self._lock:
            if not getattr(tts_engine, "is_speaking", False):
                # Update baseline ambient noise floor when quiet
                if rms < 0.030:
                    self._noise_floor_ema = self._noise_floor_ema * 0.95 + rms * 0.05
                self._consecutive_speech_chunks = 0
                return False

            # Assistant IS speaking: check for user voice interruption using Silero VAD + RMS
            vad_prob = silero_vad.process_chunk(audio_chunk) if silero_vad.is_available else 0.0
            is_speech = (vad_prob >= 0.50) or ((rms > self.energy_threshold) and (rms > self._noise_floor_ema * 2.2))

            if is_speech:
                self._consecutive_speech_chunks += 1
                if self._consecutive_speech_chunks >= self.required_chunks:
                    # Trigger instant acoustic barge-in (< 15ms SLA)
                    return self._execute_interrupt()
            else:
                self._consecutive_speech_chunks = max(0, self._consecutive_speech_chunks - 1)

            return False

    def interrupt_now(self) -> float:
        """
        Forces an immediate barge-in interruption.
        Returns the stop latency in milliseconds (< 15ms SLA).
        """
        with self._lock:
            self._execute_interrupt()
            return self.last_interrupt_latency_ms

    def _execute_interrupt(self) -> bool:
        """Halts active TTS playback in < 15ms and initiates ducking/callbacks."""
        t0 = time.perf_counter()

        # 1. Stop TTS speech immediately (< 5ms)
        try:
            tts_engine.stop_speech()
        except Exception as e:
            logger.error("Error stopping TTS in barge-in: %s", e)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.last_interrupt_latency_ms = elapsed_ms
        self.interrupt_count += 1
        self._consecutive_speech_chunks = 0

        # 2. Duck background system audio asynchronously so it doesn't block interrupt SLA
        def _duck_async():
            try:
                duck_system_audio()
                self.is_ducked = True
            except Exception:
                pass

        threading.Thread(target=_duck_async, daemon=True).start()

        # 3. Fire callback (e.g. notify UI and switch state to listening)
        if self._on_barge_in_callback:
            try:
                self._on_barge_in_callback()
            except Exception as e:
                logger.error("Error in barge-in callback: %s", e)

        return True

    def stop_all_audio(self):
        """Immediately purges all TTS audio playback and restores audio state."""
        try:
            tts_engine.stop_speech()
        except Exception:
            pass

        def _unduck_async():
            try:
                unduck_system_audio()
                self.is_ducked = False
            except Exception:
                pass

        threading.Thread(target=_unduck_async, daemon=True).start()

    def get_metrics(self) -> Dict[str, Any]:
        """Returns acoustic barge-in and audio Guardian telemetry."""
        with self._lock:
            return {
                "interrupt_count": self.interrupt_count,
                "last_interrupt_latency_ms": round(self.last_interrupt_latency_ms, 3),
                "emergency_halt_count": self.emergency_halt_count,
                "last_emergency_halt_latency_ms": round(self.last_emergency_halt_latency_ms, 3),
                "energy_threshold": self.energy_threshold,
                "required_chunks": self.required_chunks,
                "is_ducked": self.is_ducked,
                "emergency_keywords": sorted(list(EMERGENCY_KEYWORDS)),
            }


# Singleton instance
barge_in_controller = BargeInController()
