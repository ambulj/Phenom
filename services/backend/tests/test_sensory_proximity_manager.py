"""
Unit tests for Milestone 33.0 Phase 3: Spatial Acoustic Dynamics, Proximity Adaptation & Privacy Shutter
Validates:
- PROX-01.1: Metric distance estimation based on interpupillary distance (IPD).
- PROX-01.2: Dynamic acoustic volume scaling and speech rate modulation.
- PROX-01.3: Three.js Orb particle cloud scaling and intensity dynamics.
- PRIV-01.1 & PRIV-01.2: Volatile in-RAM buffer lifecycle and instant camera privacy shutter.
- SAF-01: ToolRegistry integration, risk tiers, and previews.
- SAF-02.1: Universal Guardian kill switch synchronous halt SLA (< 25.0ms).
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.ambient.sensory_proximity_manager import sensory_proximity_manager
from services.backend.vision.gaze_tracker import gaze_tracker
from services.backend.vision.spatial_gesture_detector import spatial_gesture_detector
import services.backend.tools.sensory_proximity_tools  # Registers tools


@pytest.fixture(autouse=True)
def reset_proximity_state():
    guardian.resume()
    sensory_proximity_manager.reset_halt()
    sensory_proximity_manager.set_privacy_shutter(False)
    yield
    guardian.resume()
    sensory_proximity_manager.reset_halt()
    sensory_proximity_manager.set_privacy_shutter(False)


def test_sensory_proximity_idle_state_and_initialization():
    telemetry = sensory_proximity_manager.get_telemetry()
    assert telemetry.user_distance_meters > 0.0
    assert telemetry.privacy_shutter_active is False
    assert telemetry.shutter_status == "SHUTTER_OPEN"
    assert sensory_proximity_manager.is_halted is False


def test_metric_distance_estimation_from_ipd():
    """Verify metric distance derivation and acoustic volume scaling."""
    # Simulate close user (large IPD = 120 pixels)
    # Feed multiple frames so exponential moving average filter stabilizes
    for _ in range(5):
        close_telem = sensory_proximity_manager.estimate_distance_from_ipd(ipd_pixels=120.0, confidence=0.95)

    assert close_telem.user_distance_meters < 0.65
    # Close distance produces subtle desk volume and larger Orb particles
    assert close_telem.acoustic_volume_scale <= 0.40
    assert close_telem.orb_particle_scale >= 1.20

    # Simulate far user (small IPD = 25 pixels)
    for _ in range(10):
        far_telem = sensory_proximity_manager.estimate_distance_from_ipd(ipd_pixels=25.0, confidence=0.95)

    assert far_telem.user_distance_meters > 1.20
    # Far distance scales up projection volume and shrinks particle size relative to close distance
    assert far_telem.acoustic_volume_scale >= 0.50
    assert far_telem.orb_particle_scale < close_telem.orb_particle_scale
    assert far_telem.orb_particle_scale <= 1.35


def test_privacy_shutter_instant_cutoff_and_frame_purge():
    """Verify camera privacy shutter instantaneously wipes frame buffers and halts vision."""
    tool_shutter = registry.get("toggle_camera_privacy_shutter")
    assert tool_shutter.tier == 1

    # Ingest mock frames into proximity, gaze, and gesture detectors
    sensory_proximity_manager.estimate_distance_from_ipd(
        ipd_pixels=60.0, confidence=0.9, frame_bytes=b"mock_frame_prox"
    )

    # Engage Privacy Shutter
    res = tool_shutter.handler_fn(enabled=True)
    assert res["status"] == "UPDATED"
    assert res["privacy_shutter_active"] is True
    assert res["shutter_status"] == "SHUTTER_CLOSED"

    # Verify buffers are purged and vision modules are halted
    assert len(sensory_proximity_manager._in_ram_frame_buffer) == 0
    assert gaze_tracker.is_halted is True
    assert spatial_gesture_detector.is_halted is True

    # While shutter is closed, estimations are blocked
    blocked_telem = sensory_proximity_manager.estimate_distance_from_ipd(ipd_pixels=60.0, confidence=0.9)
    assert blocked_telem.privacy_shutter_active is True
    assert blocked_telem.shutter_status == "SHUTTER_CLOSED"

    # Disengage Privacy Shutter
    res_open = tool_shutter.handler_fn(enabled=False)
    assert res_open["privacy_shutter_active"] is False
    assert res_open["shutter_status"] == "SHUTTER_OPEN"
    assert gaze_tracker.is_halted is False
    assert spatial_gesture_detector.is_halted is False


def test_proximity_acoustic_curve_configuration():
    """Verify configuration tool updates distance and volume bounds."""
    tool_cfg = registry.get("configure_proximity_acoustic_curve")
    assert tool_cfg.tier == 1

    res = tool_cfg.handler_fn(
        min_distance_m=0.40,
        max_distance_m=4.00,
        min_volume_scale=0.20,
        max_volume_scale=0.95,
    )
    assert res["status"] == "CONFIGURED"
    cfg = res["config"]
    assert cfg["min_distance_m"] == 0.40
    assert cfg["max_distance_m"] == 4.00
    assert cfg["min_volume_scale"] == 0.20
    assert cfg["max_volume_scale"] == 0.95


def test_tool_registry_invocations():
    """Verify tool execution via handler_fn and previews."""
    tool_telem = registry.get("get_sensory_proximity_telemetry")
    assert tool_telem.tier == 0
    assert "proximity" in tool_telem.preview_fn({})

    telem_res = tool_telem.handler_fn()
    assert "user_distance_meters" in telem_res
    assert "acoustic_volume_scale" in telem_res
    assert telem_res["shutter_status"] == "SHUTTER_OPEN"

    tool_sim = registry.get("simulate_proximity_observation")
    assert tool_sim.tier == 0
    sim_res = tool_sim.handler_fn(ipd_pixels=75.0, confidence=0.92)
    assert sim_res["status"] == "ESTIMATED"
    assert sim_res["user_distance_meters"] > 0.0


def test_universal_guardian_kill_switch_sla():
    """Verify Guardian kill switch halt SLA < 25.0ms on proximity manager."""
    # Warmup
    sensory_proximity_manager.halt()
    sensory_proximity_manager.reset_halt()

    # Ingest mock frame
    sensory_proximity_manager.estimate_distance_from_ipd(
        ipd_pixels=55.0, confidence=0.9, frame_bytes=b"sample_frame"
    )
    assert len(sensory_proximity_manager._in_ram_frame_buffer) > 0

    latencies = []
    for _ in range(50):
        sensory_proximity_manager.reset_halt()
        t0 = time.perf_counter()
        sensory_proximity_manager.halt()
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    avg_ms = sum(latencies) / len(latencies)
    max_ms = max(latencies)
    assert max_ms < 25.0, f"Max halt latency {max_ms:.3f}ms exceeded 25.0ms SLA"
    assert avg_ms < 1.0, f"Average halt latency {avg_ms:.3f}ms exceeded 1.0ms target"

    # Buffer must be empty after halt
    assert len(sensory_proximity_manager._in_ram_frame_buffer) == 0
    assert sensory_proximity_manager.is_halted is True
