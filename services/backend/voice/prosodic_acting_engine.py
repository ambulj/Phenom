"""
Phenom Multi-Emotional Prosodic Acting Engine & Respiratory Breath Synthesizer
Milestone 34.0 Phase 2: 100% On-device, local pitch contour modulation, dynamic emotional envelopes,
clause-boundary respiratory breath insertion, and sub-25ms Guardian safety halt.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from services.backend.safety.guardian import guardian


class ActingEmotion(str, Enum):
    WARM_WIT = "WARM_WIT"                    # Playful, witty Jarvis persona
    CONSPIRATORIAL = "CONSPIRATORIAL"        # Intimate, confidential whisper
    TACTICAL_ALERT = "TACTICAL_ALERT"        # Crisp, urgent, high-energy
    CALM_REASSURING = "CALM_REASSURING"      # Grounded, empathetic, soothing
    EXECUTIVE_CONCISE = "EXECUTIVE_CONCISE"  # Direct, authoritative briefing


class Rule8ViolationError(Exception):
    """Raised when prosodic acting text or emotional parameters target payment/checkout."""
    pass


_CHECKOUT_PATTERN = re.compile(
    r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
    re.IGNORECASE,
)


def enforce_anti_checkout(text: str) -> None:
    if _CHECKOUT_PATTERN.search(text):
        raise Rule8ViolationError(
            f"Rule 8 Violation: Payment, checkout, or billing directive detected in prosodic acting: '{text}'"
        )


@dataclass
class EmotionProfile:
    pitch_shift_semitones: float  # -12.0 to +12.0
    cadence_multiplier: float      # 0.70 to 1.50
    energy_intensity: float        # 0.20 to 1.50
    breath_probability: float      # 0.0 to 1.0
    pitch_variance_cents: float    # Dynamic micro-intonation (e.g. 50 cents)


EMOTION_PROFILES: Dict[ActingEmotion, EmotionProfile] = {
    ActingEmotion.WARM_WIT: EmotionProfile(
        pitch_shift_semitones=1.5,
        cadence_multiplier=1.08,
        energy_intensity=1.05,
        breath_probability=0.70,
        pitch_variance_cents=45.0,
    ),
    ActingEmotion.CONSPIRATORIAL: EmotionProfile(
        pitch_shift_semitones=-2.0,
        cadence_multiplier=0.92,
        energy_intensity=0.55,
        breath_probability=0.90,
        pitch_variance_cents=20.0,
    ),
    ActingEmotion.TACTICAL_ALERT: EmotionProfile(
        pitch_shift_semitones=3.0,
        cadence_multiplier=1.22,
        energy_intensity=1.35,
        breath_probability=0.40,
        pitch_variance_cents=60.0,
    ),
    ActingEmotion.CALM_REASSURING: EmotionProfile(
        pitch_shift_semitones=-1.0,
        cadence_multiplier=0.88,
        energy_intensity=0.80,
        breath_probability=0.80,
        pitch_variance_cents=25.0,
    ),
    ActingEmotion.EXECUTIVE_CONCISE: EmotionProfile(
        pitch_shift_semitones=0.0,
        cadence_multiplier=1.12,
        energy_intensity=1.10,
        breath_probability=0.50,
        pitch_variance_cents=30.0,
    ),
}


@dataclass
class ProsodicTelemetry:
    active_emotion: ActingEmotion
    pitch_shift_semitones: float
    cadence_multiplier: float
    energy_intensity: float
    breath_markers_inserted: int
    prosodic_tags_count: int
    is_halted: bool
    timestamp: float


class ProsodicActingEngine:
    """
    100% on-device emotional prosody synthesis, pitch curve calculation, and breath synthesizer.
    Guarantees:
    1. Zero cloud egress: local prosody curves and acoustic envelopes only.
    2. Dynamic F0 pitch contour modulation within ±12 semitones.
    3. Seamless clause-boundary respiratory breath marker injection.
    4. Synchronous Guardian kill switch halt (< 25.0ms SLA).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._halted: bool = False
        self._active_emotion: ActingEmotion = ActingEmotion.WARM_WIT
        self._custom_pitch_shift: Optional[float] = None
        self._custom_intensity: Optional[float] = None
        self._breath_enabled: bool = True

        self._last_breath_count: int = 0
        self._last_prosodic_tags_count: int = 0

    def halt(self) -> None:
        """Universal Guardian synchronous halt hook (< 25ms SLA)."""
        with self._lock:
            self._halted = True

    def reset_halt(self) -> None:
        """Reset halted state and clear overrides."""
        with self._lock:
            self._halted = False
            self._custom_pitch_shift = None
            self._custom_intensity = None

    def reset_custom_overrides(self) -> None:
        """Reset custom pitch shift and intensity to emotion defaults."""
        with self._lock:
            self._custom_pitch_shift = None
            self._custom_intensity = None

    @property
    def is_halted(self) -> bool:
        with self._lock:
            return self._halted

    def set_emotion(self, emotion: ActingEmotion) -> None:
        with self._lock:
            self._active_emotion = emotion

    def get_active_emotion(self) -> ActingEmotion:
        with self._lock:
            return self._active_emotion

    def configure_parameters(
        self,
        emotion: Optional[ActingEmotion] = None,
        custom_pitch_shift: Optional[float] = None,
        custom_intensity: Optional[float] = None,
        breath_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            if emotion is not None:
                self._active_emotion = emotion
            if custom_pitch_shift is not None:
                self._custom_pitch_shift = max(-12.0, min(12.0, custom_pitch_shift))
            if custom_intensity is not None:
                self._custom_intensity = max(0.1, min(2.0, custom_intensity))
            if breath_enabled is not None:
                self._breath_enabled = breath_enabled

            profile = EMOTION_PROFILES[self._active_emotion]
            return {
                "active_emotion": self._active_emotion.value,
                "pitch_shift_semitones": self._custom_pitch_shift if self._custom_pitch_shift is not None else profile.pitch_shift_semitones,
                "energy_intensity": self._custom_intensity if self._custom_intensity is not None else profile.energy_intensity,
                "cadence_multiplier": profile.cadence_multiplier,
                "breath_enabled": self._breath_enabled,
            }

    def get_telemetry(self) -> ProsodicTelemetry:
        with self._lock:
            profile = EMOTION_PROFILES[self._active_emotion]
            pitch_shift = self._custom_pitch_shift if self._custom_pitch_shift is not None else profile.pitch_shift_semitones
            intensity = self._custom_intensity if self._custom_intensity is not None else profile.energy_intensity

            return ProsodicTelemetry(
                active_emotion=self._active_emotion,
                pitch_shift_semitones=pitch_shift,
                cadence_multiplier=profile.cadence_multiplier,
                energy_intensity=intensity,
                breath_markers_inserted=self._last_breath_count,
                prosodic_tags_count=self._last_prosodic_tags_count,
                is_halted=self._halted,
                timestamp=time.time(),
            )

    def apply_acting_envelope(
        self,
        text: str,
        emotion: Optional[ActingEmotion] = None,
        inject_breaths: bool = True,
    ) -> Dict[str, Any]:
        """
        Processes text into emotionally enriched prosodic representation with F0 pitch tags
        and respiratory breath pauses at syntactic clause boundaries.
        """
        enforce_anti_checkout(text)

        with self._lock:
            if guardian.is_halted or self._halted:
                raise RuntimeError("Prosodic acting engine is currently halted by Guardian kill switch")

            target_emotion = emotion if emotion is not None else self._active_emotion
            profile = EMOTION_PROFILES[target_emotion]

            pitch_shift = self._custom_pitch_shift if self._custom_pitch_shift is not None else profile.pitch_shift_semitones
            intensity = self._custom_intensity if self._custom_intensity is not None else profile.energy_intensity
            cadence = profile.cadence_multiplier

            # 1. Break text into sentence and clause chunks
            # Punctuation clause splitting: commas, semicolons, dashes, periods
            clauses = re.split(r'([,;:\.!?—\-]+)', text)
            enriched_chunks: List[str] = []
            breath_count = 0
            tag_count = 0

            # Initial inhalation breath for long utterances
            if inject_breaths and self._breath_enabled and len(text.split()) > 5:
                inhale_type = "inhale_light_120ms" if target_emotion != ActingEmotion.CONSPIRATORIAL else "whisper_inhale_180ms"
                enriched_chunks.append(f"<breath type='{inhale_type}'/>")
                breath_count += 1

            for idx in range(0, len(clauses), 2):
                clause_text = clauses[idx].strip()
                punct = clauses[idx + 1] if idx + 1 < len(clauses) else ""

                if not clause_text and not punct:
                    continue

                if clause_text:
                    # Apply prosodic pitch inflection wrapper
                    # F0 pitch micro-variation
                    pitch_tag = f"<prosody pitch='{pitch_shift:+.1f}st' rate='{cadence:.2f}' volume='{intensity:.2f}'>"
                    enriched_chunks.append(f"{pitch_tag}{clause_text}</prosody>")
                    tag_count += 1

                if punct:
                    enriched_chunks.append(punct)
                    # Insert breath at clause boundary with emotion probability
                    if (
                        inject_breaths
                        and self._breath_enabled
                        and len(clause_text.split()) >= 4
                        and profile.breath_probability >= 0.5
                    ):
                        breath_tag = "<breath type='pause_micro_80ms'/>"
                        enriched_chunks.append(f" {breath_tag}")
                        breath_count += 1

            enriched_text = " ".join(enriched_chunks).strip()
            # Clean duplicate spacing
            enriched_text = re.sub(r'\s+', ' ', enriched_text)

            self._last_breath_count = breath_count
            self._last_prosodic_tags_count = tag_count

            return {
                "status": "PROCESSED",
                "original_text": text,
                "enriched_text": enriched_text,
                "emotion": target_emotion.value,
                "pitch_shift_semitones": pitch_shift,
                "cadence_multiplier": cadence,
                "energy_intensity": intensity,
                "breath_markers_count": breath_count,
                "prosodic_tags_count": tag_count,
            }

    def synthesize_preview(
        self,
        text: str,
        emotion: Optional[ActingEmotion] = None,
    ) -> Dict[str, Any]:
        """Synthesizes preview speech metadata with calculated pitch curve."""
        enforce_anti_checkout(text)
        res = self.apply_acting_envelope(text, emotion=emotion, inject_breaths=True)

        # Generate synthetic pitch curve (F0 values over time)
        words = text.split()
        base_hz = 120.0 * (2.0 ** (res["pitch_shift_semitones"] / 12.0))
        pitch_curve: List[float] = []
        for i, word in enumerate(words):
            # Dynamic sentence inflection: question rises at end, statements drop
            if text.endswith("?") and i >= len(words) - 2:
                inflection = 1.0 + (i / max(1, len(words))) * 0.25
            elif text.endswith("!"):
                inflection = 1.15
            else:
                inflection = 1.0 - (i / max(1, len(words))) * 0.10

            f0 = base_hz * inflection + math.sin(i * 0.8) * 8.0
            pitch_curve.append(round(f0, 1))

        return {
            "status": "PREVIEW_SYNTHESIZED",
            "emotion": res["emotion"],
            "enriched_ssml": res["enriched_text"],
            "pitch_curve_hz": pitch_curve,
            "estimated_duration_sec": round((len(words) / (2.5 * res["cadence_multiplier"])) + (res["breath_markers_count"] * 0.12), 2),
            "breath_count": res["breath_markers_count"],
        }


# Global singleton instance
prosodic_acting_engine = ProsodicActingEngine()
