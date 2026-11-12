"""
Ambient Perception Manager.
Computes ambient room occupancy, user presence duration, and voice activity
transitions strictly on-device without persisting raw media (Permanent Rule 4).
"""

import time
from typing import Optional
from services.backend.schemas.telepresence import AudioMetrics, VideoMetrics


class AmbientPerceptionManager:
    """Tracks room presence and voice activity transitions purely in transient memory."""

    def __init__(self) -> None:
        self._presence_detected: bool = False
        self._last_presence_timestamp: float = 0.0
        self._presence_timeout_seconds: float = 10.0  # Reset after 10s of no landmarks/audio
        self._voice_active: bool = False
        self._total_presence_duration_seconds: float = 0.0
        self._session_start_time: float = time.time()

    def process_telemetry(self, audio: AudioMetrics, video: VideoMetrics) -> bool:
        """
        Evaluate user presence from normalized metrics without raw video/audio frames.
        Returns True if presence is actively confirmed.
        """
        now = time.time()
        
        # Presence detected if face landmark exists or substantial speech detected
        has_face = video.face_detected or video.landmark_count >= 5
        has_speech = audio.speech_probability >= 0.65 or audio.rms_energy >= 0.20

        if has_face or has_speech:
            if not self._presence_detected:
                self._presence_detected = True
            self._last_presence_timestamp = now
            self._voice_active = has_speech
        else:
            # Check timeout
            if self._presence_detected and (now - self._last_presence_timestamp > self._presence_timeout_seconds):
                self._presence_detected = False
                self._voice_active = False

        return self._presence_detected

    def is_present(self) -> bool:
        """Return current presence state."""
        return self._presence_detected

    def is_voice_active(self) -> bool:
        """Return whether speech is actively detected."""
        return self._voice_active

    def reset(self) -> None:
        """Reset perception state."""
        self._presence_detected = False
        self._voice_active = False
        self._last_presence_timestamp = 0.0
