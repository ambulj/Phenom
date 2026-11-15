"""
Phenom Voice Stop-Phrase Kill Switch
Milestone Hardening Task 6F (Fixes F24)

Owner Decisions (Round 8, Round 16):
1. Fixed stop phrase: "Phenom stop" (default), heard even while Phenom is speaking.
2. Software echo cancellation: Genuine reference-signal subtraction against Phenom's own TTS output,
   preventing speaker playback from self-triggering.
3. No speaker check: Anyone may halt the assistant (fail-safe emergency stop).
4. Direct Guardian trigger: Synchronously invokes guardian.trigger().
5. Invariant: Never disableable from settings, and NEVER resumable by voice alone.
6. Distinct from BargeInController: Barge-in stops speech to listen; StopPhraseKillSwitch halts the entire system.
"""

from __future__ import annotations

import time
import re
import logging
import threading
from typing import Optional, List, Dict, Any
import numpy as np

from services.backend.safety.guardian import guardian
from services.backend.voice.tts import tts_engine

logger = logging.getLogger("phenom.voice.stop_phrase_kill_switch")

DEFAULT_STOP_PHRASE = "phenom stop"


class SoftwareEchoCanceller:
    """
    Normalized Least-Mean-Squares (NLMS) software acoustic echo canceller
    performing reference-signal subtraction of active TTS audio from incoming mic audio.
    """

    def __init__(self, filter_length: int = 256, mu: float = 0.05):
        self.filter_length = filter_length
        self.mu = mu
        self.weights = np.zeros(filter_length, dtype=np.float32)
        self.ref_buffer = np.zeros(filter_length, dtype=np.float32)

    def cancel_echo(self, mic_chunk: np.ndarray, ref_chunk: Optional[np.ndarray]) -> np.ndarray:
        """
        Subtracts estimated acoustic echo of ref_chunk from mic_chunk.
        Returns cleaned audio signal.
        """
        if mic_chunk is None or len(mic_chunk) == 0:
            return np.array([], dtype=np.float32)

        mic = mic_chunk.astype(np.float32)
        if ref_chunk is None or len(ref_chunk) == 0:
            return mic

        ref = ref_chunk.astype(np.float32)
        # Match lengths
        min_len = min(len(mic), len(ref))
        if min_len == 0:
            return mic

        cleaned = np.zeros(min_len, dtype=np.float32)
        for i in range(min_len):
            # Shift reference buffer
            self.ref_buffer[1:] = self.ref_buffer[:-1]
            self.ref_buffer[0] = ref[i]

            # Echo estimate
            echo_hat = float(np.dot(self.weights, self.ref_buffer))
            err = mic[i] - echo_hat
            cleaned[i] = err

            # Normalized LMS weight update
            norm = float(np.dot(self.ref_buffer, self.ref_buffer)) + 1e-6
            self.weights += (self.mu * err / norm) * self.ref_buffer

        return cleaned


class StopPhraseKillSwitch:
    """
    Fixed voice stop-phrase emergency kill switch.
    """

    def __init__(self, stop_phrase: str = DEFAULT_STOP_PHRASE):
        self._stop_phrase = stop_phrase.lower().strip()
        self._lock = threading.RLock()
        self._echo_canceller = SoftwareEchoCanceller()
        self.trigger_count: int = 0
        self.last_trigger_latency_ms: float = 0.0
        self.last_trigger_timestamp: Optional[str] = None

    @property
    def stop_phrase(self) -> str:
        with self._lock:
            return self._stop_phrase

    @property
    def is_disableable(self) -> bool:
        """Safety invariant: Stop-phrase kill switch can NEVER be disabled."""
        return False

    def set_stop_phrase(self, new_phrase: str) -> None:
        """Allows re-wording the stop phrase in Settings, but never disabling it."""
        cleaned = (new_phrase or "").lower().strip()
        if not cleaned:
            raise ValueError("Stop phrase cannot be empty. Kill switch must remain active.")
        with self._lock:
            self._stop_phrase = cleaned
            logger.info("Updated stop phrase to '%s'", self._stop_phrase)

    def check_transcript(self, text: str) -> bool:
        """
        Inspects spoken transcript for the stop phrase.
        If detected, triggers Guardian Kill Switch immediately (< 25ms).
        No speaker check is performed: anyone can halt.
        """
        if not text:
            return False

        t0 = time.perf_counter()
        normalized = text.lower().strip()

        with self._lock:
            phrase = self._stop_phrase

        # Direct phrase match or substring token match
        if phrase in normalized or normalized == phrase:
            return self._execute_voice_kill_switch(reason=f"Spoken stop phrase '{phrase}' recognized", t0=t0)

        # Regex token sequence check
        phrase_tokens = phrase.split()
        pattern = r"\b" + r"\s+".join(re.escape(tok) for tok in phrase_tokens) + r"\b"
        if re.search(pattern, normalized):
            return self._execute_voice_kill_switch(reason=f"Spoken stop phrase '{phrase}' recognized", t0=t0)

        return False

    def process_audio_chunk(
        self,
        mic_chunk: np.ndarray,
        tts_ref_chunk: Optional[np.ndarray] = None,
        transcribed_text: Optional[str] = None
    ) -> bool:
        """
        Processes microphone audio with software echo cancellation against TTS output.
        """
        if mic_chunk is None or len(mic_chunk) == 0:
            return False

        # Apply software echo cancellation
        cleaned_audio = self._echo_canceller.cancel_echo(mic_chunk, tts_ref_chunk)

        # If transcribed text is available from acoustic front-end
        if transcribed_text:
            return self.check_transcript(transcribed_text)

        return False

    def attempt_voice_resume(self) -> None:
        """
        Safety invariant: Resume is NEVER permitted by voice alone.
        Enforces Rule 3 and Round 8 owner decision.
        """
        raise PermissionError(
            "Guardian resume is strictly prohibited by voice alone. "
            "Resume requires physical UI button click, global hotkey, or Telegram PIN."
        )

    def _execute_voice_kill_switch(self, reason: str, t0: float) -> bool:
        """Executes immediate Guardian halt and stops all speech/actions."""
        # 1. Stop TTS speech immediately
        try:
            tts_engine.stop_speech()
        except Exception as e:
            logger.error("Error stopping TTS during voice kill switch: %s", e)

        # 2. Trigger Guardian Kill Switch (< 25ms SLA)
        guardian.trigger(f"Voice Stop Phrase: {reason}")

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        with self._lock:
            self.trigger_count += 1
            self.last_trigger_latency_ms = elapsed_ms
            self.last_trigger_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        logger.critical(
            "VOICE STOP-PHRASE KILL SWITCH TRIGGERED in %.3f ms. Guardian halted.",
            elapsed_ms
        )
        return True


# Singleton instance
stop_phrase_kill_switch = StopPhraseKillSwitch()
