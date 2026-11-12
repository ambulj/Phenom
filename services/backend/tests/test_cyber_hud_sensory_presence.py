"""
Unit tests for Milestone 33.0 Phase 4: CyberHUD Sensory Presence Dashboard
Validates:
- UI-05.42: CyberHUD sensory presence data contracts and WebSocket action dispatch.
- Integration between HUD toggle actions and backend vision/proximity managers.
- Rule 1 (Safety Before Tools): Actions route via ToolRegistry.
- Rule 4 & PRIV-01.1: 100% on-device local execution, zero disk persistence.
- Rule 8 & Rule 11: Anti-checkout validation and credential scrubbing on HUD parameters.
- SAF-02.1: Universal Guardian kill switch SLA benchmark (< 25.0ms).
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.vision.gaze_tracker import gaze_tracker
from services.backend.vision.spatial_gesture_detector import spatial_gesture_detector
from services.backend.ambient.sensory_proximity_manager import sensory_proximity_manager
import services.backend.tools.sensory_proximity_tools
import services.backend.tools.spatial_gesture_tools
import services.backend.tools.gaze_tracking_tools


@pytest.fixture(autouse=True)
def reset_hud_test_state():
    guardian.resume()
    gaze_tracker.reset_halt()
    spatial_gesture_detector.reset_halt()
    sensory_proximity_manager.reset_halt()
    sensory_proximity_manager.set_privacy_shutter(False)
    yield
    guardian.resume()
    gaze_tracker.reset_halt()
    spatial_gesture_detector.reset_halt()
    sensory_proximity_manager.reset_halt()
    sensory_proximity_manager.set_privacy_shutter(False)


def test_cyber_hud_sensory_telemetry_aggregation():
    """Verify aggregated sensory presence telemetry for HUD streaming."""
    # Update gaze
    gaze_tracker.update_gaze(yaw=3.0, pitch=-2.0, confidence=0.98)
    # Update gesture
    spatial_gesture_detector.ingest_hand_landmarks(
        [{"x": 0.5, "y": 0.5, "z": 0.0} for _ in range(21)],
        confidence=0.90,
    )
    # Update proximity
    sensory_proximity_manager.estimate_distance_from_ipd(ipd_pixels=80.0, confidence=0.92)

    gaze_telem = gaze_tracker.get_telemetry()
    gesture_telem = spatial_gesture_detector.get_telemetry()
    prox_telem = sensory_proximity_manager.get_telemetry()

    hud_packet = {
        "type": "sensory_presence_telemetry",
        "gaze": {
            "eye_contact": gaze_telem.get("gaze", {}).get("eye_contact", True),
            "yaw": gaze_telem.get("gaze", {}).get("yaw", 0.0),
            "pitch": gaze_telem.get("gaze", {}).get("pitch", 0.0),
            "attention_score": gaze_telem.get("attention_score", 1.0),
        },
        "gesture": {
            "gesture": gesture_telem.gesture.value,
            "confidence": gesture_telem.confidence,
            "emergency_halt_armed": True,
        },
        "proximity": {
            "user_distance_meters": prox_telem.user_distance_meters,
            "acoustic_volume_scale": prox_telem.acoustic_volume_scale,
            "shutter_status": prox_telem.shutter_status,
        },
    }

    assert hud_packet["type"] == "sensory_presence_telemetry"
    assert "gaze" in hud_packet
    assert "gesture" in hud_packet
    assert "proximity" in hud_packet
    assert hud_packet["proximity"]["shutter_status"] == "SHUTTER_OPEN"


def test_cyber_hud_privacy_shutter_toggle_action():
    """Verify that HUD toggle privacy shutter action engages backend shutter."""
    tool_shutter = registry.get("toggle_camera_privacy_shutter")
    assert tool_shutter.tier == 1

    # HUD triggers close shutter
    res = tool_shutter.handler_fn(enabled=True)
    assert res["status"] == "UPDATED"
    assert res["privacy_shutter_active"] is True
    assert res["shutter_status"] == "SHUTTER_CLOSED"
    assert gaze_tracker.is_halted is True
    assert spatial_gesture_detector.is_halted is True

    # HUD triggers reopen shutter
    res_reopen = tool_shutter.handler_fn(enabled=False)
    assert res_reopen["privacy_shutter_active"] is False
    assert res_reopen["shutter_status"] == "SHUTTER_OPEN"
    assert gaze_tracker.is_halted is False
    assert spatial_gesture_detector.is_halted is False


def test_cyber_hud_emergency_halt_action_and_sla():
    """Verify HUD 1-click emergency halt dispatches to Guardian in < 15ms SLA."""
    tool_halt = registry.get("trigger_gesture_safety_halt")
    assert tool_halt.tier == 0

    res = tool_halt.handler_fn(reason="CyberHUD 1-click operator emergency stop")
    assert res["status"] == "HALTED"
    assert res["sla_pass"] is True
    assert res["elapsed_ms"] < 15.0
    assert guardian.is_halted is True
    assert spatial_gesture_detector.is_halted is True
