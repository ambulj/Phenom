"""
Procedural In-Memory Acoustic Earcon Synthesizer.
Generates non-verbal auditory cues and earcon PCM byte buffers strictly in RAM
without writing any audio files to disk.

Part of Phenom 23.0 Sovereign Neural Evolution (VOX-06.1).
"""

import math
import struct
from typing import Dict, Any, Optional

from services.backend.safety.guardian import guardian


class AcousticEarconManager:
    """
    Synthesizes and delivers non-verbal procedural acoustic cues in RAM.
    Strictly Rule 4 compliant: zero .wav or audio files persisted to disk.
    """

    SAMPLE_RATE = 24000

    def __init__(self):
        self._last_played_earcon: Optional[str] = None

    def generate_earcon_pcm(self, cue_type: str) -> bytes:
        """
        Synthesizes raw 16-bit mono PCM bytes for the specified acoustic earcon.
        Strictly verifies Guardian kill switch (< 25.0ms SLA).
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Earcon synthesis halted.")

        self._last_played_earcon = cue_type
        frames: bytearray = bytearray()

        if cue_type == "ast_success":
            # Ascending two-tone chime: 523Hz (C5) for 60ms, then 659Hz (E5) for 60ms
            dur1 = int(self.SAMPLE_RATE * 0.06)
            dur2 = int(self.SAMPLE_RATE * 0.06)
            for i in range(dur1):
                val = int(16000 * math.sin(2.0 * math.pi * 523.25 * i / self.SAMPLE_RATE))
                frames.extend(struct.pack("<h", val))
            for i in range(dur2):
                val = int(16000 * math.sin(2.0 * math.pi * 659.25 * i / self.SAMPLE_RATE))
                frames.extend(struct.pack("<h", val))

        elif cue_type == "syntax_error":
            # Low double pulse buzz: 220Hz (A3) with pause
            dur = int(self.SAMPLE_RATE * 0.08)
            for i in range(dur):
                val = int(14000 * math.sin(2.0 * math.pi * 220.0 * i / self.SAMPLE_RATE))
                frames.extend(struct.pack("<h", val))
            for _ in range(int(self.SAMPLE_RATE * 0.02)):
                frames.extend(struct.pack("<h", 0))
            for i in range(dur):
                val = int(14000 * math.sin(2.0 * math.pi * 220.0 * i / self.SAMPLE_RATE))
                frames.extend(struct.pack("<h", val))

        elif cue_type == "test_passed":
            # Harmonious major triad chord (523Hz, 659Hz, 784Hz) for 150ms with decay
            dur = int(self.SAMPLE_RATE * 0.15)
            for i in range(dur):
                envelope = 1.0 - (i / dur)
                s1 = math.sin(2.0 * math.pi * 523.25 * i / self.SAMPLE_RATE)
                s2 = math.sin(2.0 * math.pi * 659.25 * i / self.SAMPLE_RATE)
                s3 = math.sin(2.0 * math.pi * 784.00 * i / self.SAMPLE_RATE)
                sample_val = int(5000 * (s1 + s2 + s3) * envelope)
                frames.extend(struct.pack("<h", sample_val))

        elif cue_type == "guardian_halt":
            # Rapid descending sweep alarm (880Hz down to 220Hz in 60ms)
            dur = int(self.SAMPLE_RATE * 0.06)
            for i in range(dur):
                freq = 880.0 - (660.0 * (i / dur))
                val = int(18000 * math.sin(2.0 * math.pi * freq * i / self.SAMPLE_RATE))
                frames.extend(struct.pack("<h", val))

        else:
            # Subtle neutral pip
            dur = int(self.SAMPLE_RATE * 0.03)
            for i in range(dur):
                val = int(10000 * math.sin(2.0 * math.pi * 440.0 * i / self.SAMPLE_RATE))
                frames.extend(struct.pack("<h", val))

        return bytes(frames)

    def get_last_earcon(self) -> Optional[str]:
        return self._last_played_earcon


# Global singleton
acoustic_earcon_manager = AcousticEarconManager()
