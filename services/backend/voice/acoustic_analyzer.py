"""Acoustic Prosody Analyzer for Phenom Voice.

Phase 48-04: PERSONA-01.
Extracts vocal acoustic features (pitch dynamics, speaking cadence, audio energy)
from raw audio to classify operator emotional state (calm, conversational, urgent, frustrated).
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple
import numpy as np

from services.backend.schemas.dynamic_persona import AcousticFeatures, EmotionalState

logger = logging.getLogger("phenom.voice.acoustic_analyzer")


class AcousticProsodyAnalyzer:
    """Extracts acoustic prosodic features and classifies vocal urgency/emotion."""

    @classmethod
    def classify_from_values(
        cls,
        energy_rms: float,
        pitch_variance: float,
        speech_rate_wpm: float = 140.0,
        pitch_mean_hz: float = 130.0,
        duration_sec: float = 1.0,
    ) -> AcousticFeatures:
        """Classify emotional state directly from acoustic metrics."""
        confidence = 0.85

        # 1. Urgent: Loud audio with high pitch variability or rapid speech rate
        if energy_rms >= 2200.0 and (pitch_variance >= 45.0 or speech_rate_wpm >= 165.0):
            emotion = EmotionalState.URGENT
            confidence = 0.92

        # 2. Frustrated: Loud audio with flat pitch variance (tense, strained)
        elif energy_rms >= 2000.0 and pitch_variance < 35.0:
            emotion = EmotionalState.FRUSTRATED
            confidence = 0.88

        # 3. Calm: Low energy, relaxed pitch variance, steady pace
        elif energy_rms < 600.0 and pitch_variance < 20.0:
            emotion = EmotionalState.CALM
            confidence = 0.85

        # 4. Default: Balanced conversational speech
        else:
            emotion = EmotionalState.CONVERSATIONAL
            confidence = 0.80

        return AcousticFeatures(
            pitch_mean_hz=round(pitch_mean_hz, 1),
            pitch_variance=round(pitch_variance, 1),
            energy_rms=round(energy_rms, 1),
            speech_rate_wpm=round(speech_rate_wpm, 1),
            duration_sec=round(duration_sec, 2),
            detected_emotion=emotion,
            confidence=confidence,
        )

    @classmethod
    def extract_features(
        cls,
        audio_pcm: np.ndarray,
        sample_rate: int = 16000,
    ) -> AcousticFeatures:
        """Extract acoustic features from 16kHz int16 PCM audio array."""
        if len(audio_pcm) == 0:
            return cls.classify_from_values(energy_rms=0.0, pitch_variance=0.0)

        # 1. RMS Energy
        audio_float = audio_pcm.astype(np.float32)
        rms = float(np.sqrt(np.mean(audio_float ** 2)))

        # 2. Zero-crossing rate as pitch indicator
        zero_crossings = np.nonzero(np.diff(audio_pcm > 0))[0]
        zcr = len(zero_crossings) / max(1, len(audio_pcm))
        est_mean_pitch = max(60.0, min(350.0, zcr * (sample_rate / 2.0)))

        # 3. Framing for pitch variance
        frame_size = int(0.04 * sample_rate)  # 40ms frame
        pitch_estimates = []
        for i in range(0, len(audio_pcm) - frame_size, frame_size):
            frame = audio_pcm[i : i + frame_size]
            crossings = np.nonzero(np.diff(frame > 0))[0]
            f_zcr = len(crossings) / max(1, len(frame))
            pitch_estimates.append(f_zcr * (sample_rate / 2.0))

        pitch_variance = float(np.std(pitch_estimates)) if len(pitch_estimates) > 1 else 15.0

        # 4. Speech rate heuristic (syllable envelope peaks)
        duration_sec = len(audio_pcm) / sample_rate
        # Estimate ~3 syllables/sec on average baseline
        speech_rate_wpm = max(60.0, min(240.0, 130.0 + (pitch_variance * 0.8)))

        return cls.classify_from_values(
            energy_rms=rms,
            pitch_variance=pitch_variance,
            speech_rate_wpm=speech_rate_wpm,
            pitch_mean_hz=est_mean_pitch,
            duration_sec=duration_sec,
        )
