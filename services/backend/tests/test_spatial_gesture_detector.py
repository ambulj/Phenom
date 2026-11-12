"""
Unit tests for Milestone 33.0 Phase 2: Touchless Spatial Gesture Control & Hand-Tracked Safety Halt
Validates:
- GEST-02.1: 21-point hand landmark recognition (Open Palm, Index Point, Swipes, Thumbs Up).
- GEST-02.2: Raised open-palm emergency stop triggering Guardian kill switch in < 15.0ms SLA.
- GEST-02.3: Spatial index pointing coordinate projection.
- SAF-01: ToolRegistry integration, risk tiers, and previews.
- SAF-02.1: Universal Guardian kill switch synchronous halt SLA (< 25.0ms).
- Rule 4 & PRIV-01.1: Volatile in-RAM frame buffer lifecycle, zero disk persistence.
- Rule 8 & Rule 11: Anti-checkout rejection and credential scrubbing.
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.vision.spatial_gesture_detector import (
    spatial_gesture_detector,
    GestureType,
    Rule8ViolationError,
)
import services.backend.tools.spatial_gesture_tools  # Registers tools


@pytest.fixture(autouse=True)
def reset_detector_state():
    guardian.resume()
    spatial_gesture_detector.reset_halt()
    # Reset action mappings
    spatial_gesture_detector.map_action(GestureType.SWIPE_LEFT, "switch_window_left")
    spatial_gesture_detector.map_action(GestureType.SWIPE_RIGHT, "switch_window_right")
    spatial_gesture_detector.map_action(GestureType.THUMBS_UP, "confirm_dialog")
    yield
    guardian.resume()
    spatial_gesture_detector.reset_halt()


def test_spatial_gesture_detector_idle_state_and_initialization():
    telemetry = spatial_gesture_detector.get_telemetry()
    assert telemetry.gesture in (GestureType.NONE, GestureType.OPEN_PALM, GestureType.RAISED_PALM)
    assert spatial_gesture_detector.is_halted is False


def test_raised_palm_emergency_halt_detection_and_sla():
    """Verify that raised open palm synchronously triggers Guardian halt in < 15ms SLA."""
    # Warmup
    spatial_gesture_detector.halt()
    spatial_gesture_detector.reset_halt()
    guardian.resume()

    sim_tool = registry.get("simulate_hand_gesture_observation")
    res = sim_tool.handler_fn(gesture_name="RAISED_PALM", confidence=0.95)
    assert res["status"] == "INGESTED"
    assert res["emergency_halt_triggered"] is True
    assert guardian.is_halted is True
    assert spatial_gesture_detector.is_halted is True

    # Benchmark emergency halt direct trigger SLA
    guardian.resume()
    spatial_gesture_detector.reset_halt()

    latencies = []
    for _ in range(20):
        guardian.resume()
        spatial_gesture_detector.reset_halt()
        elapsed_ms = spatial_gesture_detector.trigger_emergency_halt(reason="Test raised palm stop")
        latencies.append(elapsed_ms)

    avg_ms = sum(latencies) / len(latencies)
    max_ms = max(latencies)
    assert max_ms < 15.0, f"Max emergency stop latency {max_ms:.3f}ms exceeded 15.0ms hard SLA"
    assert avg_ms < 5.0, f"Average emergency stop latency {avg_ms:.3f}ms exceeded 5.0ms target"


def test_index_pointing_coordinate_resolution():
    """Verify spatial pointing target calculation from extended index finger."""
    spatial_gesture_detector.reset_halt()
    guardian.resume()

    sim_tool = registry.get("simulate_hand_gesture_observation")
    res = sim_tool.handler_fn(gesture_name="INDEX_POINT", confidence=0.92)
    assert res["status"] == "INGESTED"
    assert res["gesture"] == GestureType.INDEX_POINT.value
    assert res["emergency_halt_triggered"] is False
    assert res["pointing_target"] is not None
    assert 0.0 <= res["pointing_target"]["x"] <= 1.0
    assert 0.0 <= res["pointing_target"]["y"] <= 1.0


def test_dynamic_swipe_velocity_detection():
    """Verify horizontal wrist movement velocity classifies directional swipes."""
    spatial_gesture_detector.reset_halt()
    guardian.resume()

    # Frame 1: initial position at t0
    landmarks_t0 = [{"x": 0.8, "y": 0.5, "z": 0.0} for _ in range(21)]
    spatial_gesture_detector.ingest_hand_landmarks(landmarks_t0, confidence=0.9)

    time.sleep(0.05)  # 50ms interval

    # Frame 2: wrist moved left to 0.2
    landmarks_t1 = [{"x": 0.2, "y": 0.5, "z": 0.0} for _ in range(21)]
    telemetry = spatial_gesture_detector.ingest_hand_landmarks(landmarks_t1, confidence=0.9)

    assert telemetry.gesture == GestureType.SWIPE_LEFT
    assert telemetry.mapped_action == "switch_window_left"

    # Swipe right: wrist moves from 0.2 to 0.8 within 0.05s
    time.sleep(0.05)
    landmarks_t2 = [{"x": 0.85, "y": 0.5, "z": 0.0} for _ in range(21)]
    telemetry_right = spatial_gesture_detector.ingest_hand_landmarks(landmarks_t2, confidence=0.9)
    assert telemetry_right.gesture == GestureType.SWIPE_RIGHT
    assert telemetry_right.mapped_action == "switch_window_right"


def test_thumbs_up_gesture_and_confirmation_binding():
    """Verify thumbs up pose recognition and confirmation action binding."""
    spatial_gesture_detector.reset_halt()
    guardian.resume()

    sim_tool = registry.get("simulate_hand_gesture_observation")
    res = sim_tool.handler_fn(gesture_name="THUMBS_UP", confidence=0.94)
    assert res["status"] == "INGESTED"
    assert res["gesture"] == GestureType.THUMBS_UP.value
    assert res["mapped_action"] == "confirm_dialog"


def test_tool_registry_map_and_trigger_tools():
    """Verify tool registration, tier configuration, and execution."""
    tool_map = registry.get("map_spatial_gesture_action")
    assert tool_map.tier == 1

    tool_halt = registry.get("trigger_gesture_safety_halt")
    assert tool_halt.tier == 0

    tool_telem = registry.get("get_spatial_gesture_telemetry")
    assert tool_telem.tier == 0

    # Test mapping update
    map_res = tool_map.handler_fn(gesture="SWIPE_LEFT", action_name="navigate_history_back")
    assert map_res["status"] == "MAPPED"
    assert map_res["current_mappings"]["SWIPE_LEFT"] == "navigate_history_back"

    # Test direct trigger halt tool
    halt_res = tool_halt.handler_fn(reason="Manual operator palm stop test")
    assert halt_res["status"] == "HALTED"
    assert halt_res["sla_pass"] is True
    assert halt_res["elapsed_ms"] < 15.0


def test_rule_8_anti_checkout_and_rule_11_compliance():
    """Verify Rule 8 blocks payment directives and credentials in gesture actions."""
    tool_map = registry.get("map_spatial_gesture_action")
    tool_halt = registry.get("trigger_gesture_safety_halt")

    with pytest.raises(Rule8ViolationError):
        tool_map.handler_fn(gesture="SWIPE_RIGHT", action_name="checkout_cart_pay_now")

    with pytest.raises(Rule8ViolationError):
        tool_halt.handler_fn(reason="emergency purchase credit card payment")


def test_universal_guardian_killswitch_sla_and_in_ram_lifecycle():
    """Verify Guardian synchronous halt SLA < 25.0ms and in-RAM frame queue."""
    # Warmup
    spatial_gesture_detector.halt()
    spatial_gesture_detector.reset_halt()

    # Ingest 5 frames with mock bytes to verify in-RAM buffer capacity is capped at 3
    for i in range(5):
        spatial_gesture_detector.ingest_hand_landmarks(
            landmarks=[{"x": 0.5, "y": 0.5, "z": 0.0} for _ in range(21)],
            confidence=0.8,
            frame_bytes=f"mock_frame_{i}".encode("utf-8"),
        )

    assert len(spatial_gesture_detector._in_ram_frame_buffer) == 3

    # Benchmark halt SLA over 50 iterations
    latencies = []
    for _ in range(50):
        spatial_gesture_detector.reset_halt()
        t0 = time.perf_counter()
        spatial_gesture_detector.halt()
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    avg_halt_ms = sum(latencies) / len(latencies)
    max_halt_ms = max(latencies)

    assert max_halt_ms < 25.0, f"Max halt latency {max_halt_ms:.3f}ms exceeded 25.0ms hard SLA"
    assert avg_halt_ms < 1.0, f"Average halt latency {avg_halt_ms:.3f}ms exceeded 1.0ms target"
    # Ensure memory buffer is wiped clean after halt
    assert len(spatial_gesture_detector._in_ram_frame_buffer) == 0
