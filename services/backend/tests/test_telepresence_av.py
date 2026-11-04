"""
Tests for Omni-Modal Spatial Telepresence & Low-Latency AV Pipeline (AVP-01).
Verifies ring buffering, mute/shutter state overrides, ambient occupancy detection,
and Rule 4 zero-frame disk storage invariants.
"""

import time
import pytest
from services.backend.schemas.telepresence import MediaStreamType, SensorState
from services.backend.telepresence.av_pipeline import StreamingAVPipeline
from services.backend.telepresence.perception_manager import AmbientPerceptionManager


def test_telepresence_session_lifecycle():
    pipeline = StreamingAVPipeline()

    state = pipeline.get_state()
    assert state.is_active is False
    assert state.microphone_state == SensorState.MUTED
    assert state.camera_state == SensorState.SHUTTERED

    # Start session
    active_state = pipeline.start_session(MediaStreamType.AUDIO_VIDEO)
    assert active_state.is_active is True
    assert active_state.microphone_state == SensorState.ACTIVE
    assert active_state.camera_state == SensorState.ACTIVE
    assert active_state.started_at is not None

    # Stop session
    stopped_state = pipeline.stop_session()
    assert stopped_state.is_active is False
    assert stopped_state.microphone_state == SensorState.MUTED
    assert stopped_state.camera_state == SensorState.SHUTTERED


def test_telepresence_shutter_and_mute_controls():
    pipeline = StreamingAVPipeline()
    pipeline.start_session()

    # Mute microphone
    muted_state = pipeline.set_microphone(SensorState.MUTED, gain=1.5)
    assert muted_state.microphone_state == SensorState.MUTED
    assert muted_state.audio_metrics.rms_energy == 0.0

    # Ingest telemetry while muted: audio should remain 0
    res = pipeline.ingest_telemetry(
        audio_rms=0.75,
        speech_probability=0.90,
        landmarks=[(0.5, 0.5), (0.6, 0.6)],
        timestamp=time.time(),
    )
    assert res["sample"]["rms"] == 0.0
    assert res["sample"]["speech_prob"] == 0.0
    assert res["sample"]["face_detected"] is True

    # Shutter camera
    shuttered_state = pipeline.set_camera(SensorState.SHUTTERED)
    assert shuttered_state.camera_state == SensorState.SHUTTERED
    assert shuttered_state.video_metrics.fps == 0.0

    # Ingest telemetry while shuttered: landmarks should be suppressed
    res2 = pipeline.ingest_telemetry(
        audio_rms=0.50,
        speech_probability=0.80,
        landmarks=[(0.5, 0.5), (0.6, 0.6), (0.7, 0.7)],
        timestamp=time.time(),
    )
    assert res2["sample"]["face_detected"] is False
    assert res2["sample"]["landmarks_count"] == 0


def test_ambient_perception_occupancy():
    manager = AmbientPerceptionManager()

    # Initially empty room
    assert manager.is_present() is False
    assert manager.is_voice_active() is False

    # Simulate detected face landmarks
    from services.backend.schemas.telepresence import AudioMetrics, VideoMetrics
    audio = AudioMetrics(rms_energy=0.0, speech_probability=0.0)
    video = VideoMetrics(face_detected=True, landmark_count=10, fps=30.0)

    present = manager.process_telemetry(audio, video)
    assert present is True
    assert manager.is_present() is True

    # Reset
    manager.reset()
    assert manager.is_present() is False


def test_telepresence_zero_copy_ring_buffer_bounds():
    pipeline = StreamingAVPipeline()
    pipeline.start_session()

    # Ingest 150 frames into a maxlen=100 deque
    for i in range(150):
        pipeline.ingest_telemetry(
            audio_rms=0.10,
            speech_probability=0.20,
            landmarks=[(0.1, 0.2)],
            timestamp=float(i),
        )

    assert len(pipeline._telemetry_buffer) == 100
    assert pipeline._telemetry_buffer[-1]["timestamp"] == 149.0


def test_rule_4_zero_frame_persistence():
    """Verify that VideoMetrics and Session state enforce zero disk persistence."""
    pipeline = StreamingAVPipeline()
    state = pipeline.get_state()
    assert state.video_metrics.zero_frame_retention is True
    assert hasattr(pipeline, "_disk_writer") is False
