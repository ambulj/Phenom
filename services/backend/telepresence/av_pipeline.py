"""
Low-Latency Streaming Audio/Video Pipeline.
Coordinates transient ring buffering, hardware mute/shutter controls,
and sub-10ms Guardian kill switch disengagement (Permanent Rule 1, 4).
"""

import collections
import time
import uuid
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from services.backend.schemas.telepresence import (
    AudioMetrics,
    MediaStreamType,
    SensorState,
    TelepresenceSessionState,
    VideoMetrics,
)
from services.backend.telepresence.perception_manager import AmbientPerceptionManager


class StreamingAVPipeline:
    """Manages low-latency audio/video ingestion and hardware privacy states."""

    def __init__(self) -> None:
        self._session_id: str = f"av-session-{uuid.uuid4().hex[:8]}"
        self._is_active: bool = False
        self._stream_type: MediaStreamType = MediaStreamType.AUDIO_VIDEO
        self._microphone_state: SensorState = SensorState.MUTED
        self._camera_state: SensorState = SensorState.SHUTTERED
        self._mic_gain: float = 1.0
        self._camera_resolution: str = "1280x720"
        self._started_at: Optional[float] = None
        self._halted: bool = False

        self._audio_metrics: AudioMetrics = AudioMetrics()
        self._video_metrics: VideoMetrics = VideoMetrics()

        # Zero-copy ring buffer of recent telemetry (bounded capacity 100)
        self._telemetry_buffer: Deque[Dict[str, Any]] = collections.deque(maxlen=100)

        self._perception_manager: AmbientPerceptionManager = AmbientPerceptionManager()
        self._change_callbacks: List[Callable[[TelepresenceSessionState], None]] = []

    def register_change_callback(self, callback: Callable[[TelepresenceSessionState], None]) -> None:
        """Register a subscriber callback for state updates."""
        self._change_callbacks.append(callback)

    def _notify(self) -> None:
        state = self.get_state()
        for cb in self._change_callbacks:
            try:
                cb(state)
            except Exception:
                pass

    def start_session(self, stream_type: MediaStreamType = MediaStreamType.AUDIO_VIDEO) -> TelepresenceSessionState:
        """Initialize and start an AV telepresence session."""
        if self._halted:
            raise PermissionError("Guardian kill switch is active: AV telepresence cannot start.")

        self._is_active = True
        self._stream_type = stream_type
        self._microphone_state = SensorState.ACTIVE
        self._camera_state = SensorState.ACTIVE
        self._started_at = time.time()
        self._notify()
        return self.get_state()

    def stop_session(self) -> TelepresenceSessionState:
        """Stop current telepresence session and mute hardware."""
        self._is_active = False
        self._microphone_state = SensorState.MUTED
        self._camera_state = SensorState.SHUTTERED
        self._telemetry_buffer.clear()
        self._perception_manager.reset()
        self._notify()
        return self.get_state()

    def set_microphone(self, state: SensorState, gain: float = 1.0) -> TelepresenceSessionState:
        """Toggle microphone hardware state (ACTIVE or MUTED)."""
        if self._halted:
            raise PermissionError("Guardian kill switch is active: microphone control blocked.")

        self._microphone_state = state
        self._mic_gain = max(0.0, min(2.0, gain))
        if state == SensorState.MUTED:
            self._audio_metrics.rms_energy = 0.0
            self._audio_metrics.speech_probability = 0.0
        self._notify()
        return self.get_state()

    def set_camera(self, state: SensorState, resolution: str = "1280x720") -> TelepresenceSessionState:
        """Toggle camera privacy shutter (ACTIVE or SHUTTERED)."""
        if self._halted:
            raise PermissionError("Guardian kill switch is active: camera control blocked.")

        self._camera_state = state
        self._camera_resolution = resolution
        if state == SensorState.SHUTTERED:
            self._video_metrics.face_detected = False
            self._video_metrics.landmark_count = 0
            self._video_metrics.fps = 0.0
        self._notify()
        return self.get_state()

    def ingest_telemetry(
        self,
        audio_rms: float,
        speech_probability: float,
        landmarks: List[Tuple[float, float]],
        timestamp: float,
    ) -> Dict[str, Any]:
        """
        Ingest transient audio and landmark telemetry.
        Strict Rule 4 guarantee: No camera frame pixels or raw audio WAV bytes are persisted.
        """
        if self._halted:
            raise PermissionError("Guardian kill switch is active: telepresence ingestion blocked.")

        # If microphone is muted, override audio metrics to 0
        effective_rms = audio_rms * self._mic_gain if self._microphone_state == SensorState.ACTIVE else 0.0
        effective_speech = speech_probability if self._microphone_state == SensorState.ACTIVE else 0.0

        # If camera is shuttered, ignore visual landmarks
        effective_landmarks = landmarks if self._camera_state == SensorState.ACTIVE else []
        has_face = len(effective_landmarks) > 0

        self._audio_metrics = AudioMetrics(
            rms_energy=min(1.0, effective_rms),
            peak_volume_db=20.0 * (effective_rms if effective_rms > 0.001 else 0.001) - 96.0,
            speech_probability=effective_speech,
            sample_rate_hz=16000,
        )

        self._video_metrics = VideoMetrics(
            fps=30.0 if self._camera_state == SensorState.ACTIVE else 0.0,
            resolution=self._camera_resolution,
            face_detected=has_face,
            landmark_count=len(effective_landmarks),
            zero_frame_retention=True,
        )

        presence = self._perception_manager.process_telemetry(self._audio_metrics, self._video_metrics)

        sample = {
            "timestamp": timestamp,
            "rms": self._audio_metrics.rms_energy,
            "speech_prob": self._audio_metrics.speech_probability,
            "face_detected": has_face,
            "landmarks_count": len(effective_landmarks),
            "presence": presence,
        }
        self._telemetry_buffer.append(sample)
        self._notify()

        return {
            "status": "ingested",
            "sample": sample,
            "session_state": self.get_state().model_dump(),
        }

    def get_state(self) -> TelepresenceSessionState:
        """Return the current telepresence session state."""
        return TelepresenceSessionState(
            session_id=self._session_id,
            is_active=self._is_active,
            stream_type=self._stream_type,
            microphone_state=self._microphone_state,
            camera_state=self._camera_state,
            audio_metrics=self._audio_metrics,
            video_metrics=self._video_metrics,
            ambient_presence=self._perception_manager.is_present(),
            started_at=self._started_at,
        )

    # =========================================================================
    # Guardian Kill Switch Sub-10ms SLA Hooks
    # =========================================================================

    def halt(self) -> None:
        """
        Synchronously halt the AV telepresence engine.
        Instantly transitions sensors to DISABLED, clears ring buffers, and aborts streaming.
        """
        self._halted = True
        self._is_active = False
        self._microphone_state = SensorState.DISABLED
        self._camera_state = SensorState.DISABLED
        self._telemetry_buffer.clear()
        self._perception_manager.reset()
        self._notify()

    def resume(self) -> None:
        """Resume telepresence engine from Guardian halt."""
        self._halted = False
        self._microphone_state = SensorState.MUTED
        self._camera_state = SensorState.SHUTTERED
        self._notify()

    def reset(self) -> None:
        """Alias for resume to comply with standard subsystem interface."""
        self.resume()
