"""Sub-100ms Barge-In Soft-Mute Handler for Phenom Voice.

Phase 48-03: VOICE-02.
Instantly attenuates/halts Jarvis TTS playback upon detecting user speech without
terminating running background swarm agents, unless explicit emergency kill-words are spoken.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Callable, Optional

from services.backend.schemas.voice_duplex import BargeInEvent, BargeInType

logger = logging.getLogger("phenom.voice.barge_in_handler")


class BargeInSoftMuteHandler:
    """Acoustic barge-in handler with non-destructive swarm execution and emergency kill switch."""

    SOFT_MUTE_SLA_MS: float = 100.0  # Hard SLA < 100ms for audio attenuation
    GUARDIAN_SLA_MS: float = 25.0    # Hard SLA < 25ms for emergency kill switch

    EMERGENCY_KILL_PATTERNS = [
        r"\bphenom\s+stop\b",
        r"\bemergency\s+halt\b",
        r"\bfreeze\b",
        r"\bkill\s+switch\b",
        r"\bemergency\s+stop\b",
    ]

    def __init__(
        self,
        tts_attenuator_fn: Optional[Callable[[], None]] = None,
        guardian_halt_fn: Optional[Callable[[], None]] = None,
    ) -> None:
        self._tts_attenuator_fn = tts_attenuator_fn or self._default_tts_attenuate
        self._guardian_halt_fn = guardian_halt_fn or self._default_guardian_halt
        self.is_tts_playing: bool = False
        self.output_gain: float = 1.0
        self.total_barge_ins: int = 0
        self.last_latency_ms: float = 0.0

    @staticmethod
    def _default_tts_attenuate() -> None:
        """Default TTS attenuation hook."""
        try:
            from services.backend.voice.tts import tts_engine
            if hasattr(tts_engine, "stop"):
                tts_engine.stop()
        except Exception:
            pass

    @staticmethod
    def _default_guardian_halt() -> None:
        """Default Universal Guardian kill switch invocation."""
        try:
            from services.backend.safety.guardian import guardian
            guardian.trigger()
        except Exception:
            pass

    def check_is_emergency_kill(self, utterance: str) -> bool:
        """Check if spoken utterance contains any registered emergency kill words."""
        cleaned = utterance.strip().lower()
        return any(re.search(pat, cleaned) for pat in self.EMERGENCY_KILL_PATTERNS)

    def trigger_soft_mute(
        self,
        transcript: Optional[str] = None,
        on_emergency_callback: Optional[Callable[[], None]] = None,
    ) -> BargeInEvent:
        """Execute instant audio soft-mute and evaluate emergency vs conversational speech."""
        t_start = time.perf_counter()

        # 1. Attenuate audio gain to 0.0 immediately (< 100ms SLA, typically < 1ms in RAM)
        self.output_gain = 0.0
        self.is_tts_playing = False
        try:
            self._tts_attenuator_fn()
        except Exception as exc:
            logger.warning("Error in TTS attenuator callback: %s", exc)

        latency_ms = (time.perf_counter() - t_start) * 1000.0
        self.last_latency_ms = round(latency_ms, 2)
        self.total_barge_ins += 1

        # 2. Check Emergency Kill Phrase (Rule 3)
        is_emergency = False
        if transcript and self.check_is_emergency_kill(transcript):
            is_emergency = True
            t_guard_start = time.perf_counter()
            try:
                self._guardian_halt_fn()
                if on_emergency_callback:
                    on_emergency_callback()
            except Exception as exc:
                logger.error("Error triggering Guardian kill switch: %s", exc)
            guard_latency_ms = (time.perf_counter() - t_guard_start) * 1000.0
            logger.critical("Emergency kill word spoken! Guardian triggered in %.3f ms", guard_latency_ms)

        # 3. Classify Barge-In Type
        if is_emergency:
            b_type = BargeInType.EMERGENCY_HALT
            swarm_continued = False
        elif transcript and any(w in transcript.lower() for w in ["don't", "stop", "cancel", "no", "wrong"]):
            b_type = BargeInType.CORRECTION
            swarm_continued = True  # Non-destructive! Swarm continues
        elif transcript and any(w in transcript.lower() for w in ["focus", "prioritize", "first", "also", "make sure"]):
            b_type = BargeInType.STEERING_GUIDANCE
            swarm_continued = True  # Non-destructive! Swarm continues
        else:
            b_type = BargeInType.CONVERSATIONAL
            swarm_continued = True  # Non-destructive! Swarm continues

        event = BargeInEvent(
            event_id=f"barge_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}",
            detected_at=time.time(),
            latency_ms=self.last_latency_ms,
            tts_attenuated=True,
            transcript=transcript,
            barge_in_type=b_type,
            injected_guidance=transcript if swarm_continued else None,
            swarm_continued=swarm_continued,
        )

        logger.info(
            "Barge-in soft-mute executed: latency=%.2f ms, type=%s, swarm_continued=%s",
            latency_ms,
            b_type.value,
            swarm_continued,
        )
        return event

    def reset_output_gain(self) -> None:
        """Restore normal audio gain after turn finishes."""
        self.output_gain = 1.0
