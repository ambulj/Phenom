"""
Ambient Feedback Synthesizer (FBK-01, SAF-01, SAF-02).
Generates subtle procedural spatial audio cues and synthesized in-memory waveforms
for desktop notifications, milestone celebrations, and safety gates.
"""

import io
import math
import struct
import time
import uuid
import wave
import logging
from typing import Callable, Dict, List, Optional

from services.backend.schemas.proactive_bus import AudioCuePayload, AudioCueType

logger = logging.getLogger(__name__)

# Frequency and duration profiles per cue type
CUE_PROFILES: Dict[AudioCueType, Dict[str, float]] = {
    AudioCueType.SUBTLE_CHIME: {"freq": 587.33, "duration_ms": 200, "vol": 0.4},
    AudioCueType.MILESTONE_FANFARE: {"freq": 659.25, "duration_ms": 350, "vol": 0.6},
    AudioCueType.RISK_GATE_WARNING: {"freq": 349.23, "duration_ms": 300, "vol": 0.7},
    AudioCueType.GUARDIAN_HALT_BUZZ: {"freq": 180.00, "duration_ms": 150, "vol": 0.8},
    AudioCueType.DREAM_CYCLE_START: {"freq": 440.00, "duration_ms": 250, "vol": 0.35},
    AudioCueType.DREAM_CYCLE_COMPLETE: {"freq": 523.25, "duration_ms": 300, "vol": 0.45},
}


class AmbientFeedbackSynthesizer:
    """Procedural audio synthesizer producing spatial stereo cues."""

    def __init__(self) -> None:
        self._halted: bool = False
        self._cue_history: List[AudioCuePayload] = []
        self._broadcaster: Optional[Callable[[dict], None]] = None

    def register_broadcaster(self, broadcaster: Callable[[dict], None]) -> None:
        self._broadcaster = broadcaster

    def halt(self) -> None:
        """Immediate synchronous halt for Guardian kill switch (< 10ms SLA)."""
        self._halted = True
        logger.info("[FeedbackSynth] AmbientFeedbackSynthesizer halted synchronously by Guardian.")

    def reset(self) -> None:
        self._halted = False

    def is_halted(self) -> bool:
        return self._halted

    def synthesize_wav_bytes(
        self,
        frequency_hz: float,
        duration_ms: int,
        volume: float = 0.5,
        spatial_pan: float = 0.0,
    ) -> bytes:
        """
        Synthesize in-memory stereo 16-bit PCM WAV bytes with smooth cosine fade envelope.
        spatial_pan: -1.0 (left), 0.0 (center), 1.0 (right)
        """
        sample_rate = 22050
        num_samples = int(sample_rate * (duration_ms / 1000.0))
        max_amplitude = 32767.0 * max(0.0, min(1.0, volume))

        # Pan calculations (constant power panning)
        pan = max(-1.0, min(1.0, spatial_pan))
        left_gain = math.cos((pan + 1.0) * math.pi / 4.0)
        right_gain = math.sin((pan + 1.0) * math.pi / 4.0)

        raw_frames = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Sine wave
            sample = math.sin(2.0 * math.pi * frequency_hz * t)
            # Envelope: smooth fade-in and fade-out to prevent clicks
            envelope = math.sin(math.pi * (float(i) / num_samples))
            val = sample * envelope * max_amplitude

            left_val = int(max(-32768, min(32767, val * left_gain)))
            right_val = int(max(-32768, min(32767, val * right_gain)))

            raw_frames.extend(struct.pack("<hh", left_val, right_val))

        # Write WAV header into BytesIO
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(2)      # Stereo
            wf.setsampwidth(2)      # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(raw_frames)

        return wav_buf.getvalue()

    def trigger_cue(
        self,
        cue_type: AudioCueType | str,
        spatial_pan: float = 0.0,
        volume: Optional[float] = None,
    ) -> AudioCuePayload:
        """Trigger an ambient audio cue and broadcast to UI clients."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Audio feedback halted.")

        if isinstance(cue_type, str):
            try:
                c_type = AudioCueType(cue_type)
            except ValueError:
                c_type = AudioCueType.SUBTLE_CHIME
        else:
            c_type = cue_type

        profile = CUE_PROFILES.get(c_type, CUE_PROFILES[AudioCueType.SUBTLE_CHIME])
        vol = volume if volume is not None else profile["vol"]
        dur = int(profile["duration_ms"])
        freq = profile["freq"]

        payload = AudioCuePayload(
            cue_id=f"cue_{uuid.uuid4().hex[:8]}",
            cue_type=c_type,
            frequency_hz=freq,
            duration_ms=dur,
            volume=vol,
            spatial_pan=max(-1.0, min(1.0, spatial_pan)),
            timestamp=time.time(),
        )

        self._cue_history.append(payload)
        if len(self._cue_history) > 50:
            self._cue_history.pop(0)

        if self._broadcaster:
            try:
                self._broadcaster({
                    "type": "ambient_audio_cue",
                    "payload": payload.model_dump(),
                })
            except Exception as e:
                logger.debug(f"[FeedbackSynth] Broadcast error: {e}")

        return payload

    def get_recent_cues(self) -> List[AudioCuePayload]:
        return list(self._cue_history)


# Global singleton instance
ambient_feedback_synthesizer = AmbientFeedbackSynthesizer()
