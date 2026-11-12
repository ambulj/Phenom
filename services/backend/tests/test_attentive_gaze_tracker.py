"""Test Suite for Attentive Gaze & Engagement Tracker (Milestone 33 Phase 1).

Validates:
- On-device gaze angle and direct eye contact calculation (SENSE-01.1).
- Sustained direct eye-contact touchless listening trigger (> 400ms) (SENSE-01.2).
- Look-away conversational pause trigger (> 500ms) and eye-contact resumption (SENSE-01.3).
- Volatile in-RAM frame buffer lifecycle (PRIV-01.1).
- Rule 8 Anti-Checkout defense rejecting payment/billing directives with Rule8ViolationError.
- Rule 11 Credential scrubbing masking secrets to [REDACTED].
- Universal Guardian kill switch SLA benchmark (< 25.0ms hard SLA, typical < 0.1ms).
- Tool registry integration and schema previews for all 4 tools.
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.vision.gaze_tracker import (
    GazeTracker,
    EngagementState,
    Rule8ViolationError,
)
import services.backend.tools.gaze_tracking_tools  # Ensure tools are registered


@pytest.fixture
def tracker():
    t = GazeTracker(
        yaw_threshold_deg=25.0,
        pitch_threshold_deg=20.0,
        sustained_trigger_ms=400.0,
        look_away_pause_ms=500.0,
    )
    guardian.resume()
    t.reset_halt()
    yield t
    guardian.resume()
    t.reset_halt()


def test_gaze_vector_direct_eye_contact_computation(tracker):
    """SENSE-01.1: Verify eye-contact computation based on yaw/pitch tolerances."""
    # 1. Direct eye contact (yaw=5°, pitch=-4°)
    tel_direct = tracker.update_gaze(yaw=5.0, pitch=-4.0, confidence=0.98)
    assert tel_direct.gaze.eye_contact is True
    assert tel_direct.gaze.yaw == 5.0
    assert tel_direct.gaze.pitch == -4.0

    # 2. Looking sideways (yaw=45°, pitch=0°) -> Outside 25° threshold
    tel_side = tracker.update_gaze(yaw=45.0, pitch=0.0, confidence=0.95)
    assert tel_side.gaze.eye_contact is False

    # 3. Looking down at desk (yaw=0°, pitch=-35°) -> Outside 20° threshold
    tel_down = tracker.update_gaze(yaw=0.0, pitch=-35.0, confidence=0.95)
    assert tel_down.gaze.eye_contact is False


def test_sustained_eye_contact_touchless_listening_trigger(tracker):
    """SENSE-01.2: Verify touchless listening activates after > 400ms sustained gaze."""
    triggered = False

    def on_touchless_listen():
        nonlocal triggered
        triggered = True

    tracker.add_touchless_listen_callback(on_touchless_listen)

    base_time = 1000.0

    # 1. First glance (0ms sustained)
    t1 = tracker.update_gaze(yaw=2.0, pitch=1.0, timestamp=base_time)
    assert t1.state == EngagementState.DISENGAGED
    assert t1.touchless_listening_active is False
    assert triggered is False

    # 2. After 200ms of sustained gaze (below 400ms)
    t2 = tracker.update_gaze(yaw=3.0, pitch=2.0, timestamp=base_time + 0.20)
    assert t2.touchless_listening_active is False
    assert triggered is False

    # 3. After 450ms of sustained gaze (exceeds 400ms threshold)
    t3 = tracker.update_gaze(yaw=1.0, pitch=0.0, timestamp=base_time + 0.45)
    assert t3.state == EngagementState.ATTENTIVE
    assert t3.touchless_listening_active is True
    assert triggered is True


def test_look_away_conversational_pause_and_resume_trigger(tracker):
    """SENSE-01.3: Verify speech pauses on looking away > 500ms and resumes on return."""
    paused = False
    resumed = False

    def on_pause():
        nonlocal paused
        paused = True

    def on_resume():
        nonlocal resumed
        resumed = True

    tracker.add_pause_callback(on_pause)
    tracker.add_resume_callback(on_resume)

    base_time = 2000.0

    # 1. Establish attentive engagement
    tracker.update_gaze(yaw=0.0, pitch=0.0, timestamp=base_time)
    tracker.update_gaze(yaw=0.0, pitch=0.0, timestamp=base_time + 0.45)
    assert tracker.get_telemetry()["state"] == "ATTENTIVE"

    # 2. Look away for 200ms (below 500ms pause threshold)
    t_away1 = tracker.update_gaze(yaw=50.0, pitch=0.0, timestamp=base_time + 0.70)
    assert t_away1.conversational_paused is False
    assert paused is False

    # 3. Look away for 600ms (exceeds 500ms pause threshold)
    t_away2 = tracker.update_gaze(yaw=50.0, pitch=0.0, timestamp=base_time + 1.35)
    assert t_away2.state == EngagementState.LOOKING_AWAY
    assert t_away2.conversational_paused is True
    assert paused is True

    # 4. Return eye contact -> triggers resume
    t_return = tracker.update_gaze(yaw=0.0, pitch=0.0, timestamp=base_time + 1.80)
    assert t_return.conversational_paused is False
    assert resumed is True


def test_in_ram_volatile_frame_wipe(tracker):
    """PRIV-01.1: Verify raw frames are cleared in-memory with zero disk persistence."""
    t1 = tracker.update_gaze(yaw=0.0, pitch=0.0)
    assert t1.volatile_frames_cleared == 1

    t2 = tracker.update_gaze(yaw=5.0, pitch=5.0)
    assert t2.volatile_frames_cleared == 2


def test_rule_8_anti_checkout_defense(tracker):
    """Rule 8: Verify rejection of any gaze parameter or intent targeting payment."""
    with pytest.raises(Rule8ViolationError):
        tracker.check_safety("proceed with credit card payment checkout")


def test_rule_11_credential_protection(tracker):
    """Rule 11: Verify sensitive credentials and tokens are scrubbed."""
    clean_dict = tracker.scrub_dict({
        "gaze_session": "active",
        "api_key": "sk-proj-secretkey9981",
        "password": "Password123!",
    })
    assert clean_dict["api_key"] == "[REDACTED]"
    assert clean_dict["password"] == "[REDACTED]"
    assert clean_dict["gaze_session"] == "active"


def test_universal_guardian_kill_switch_sla(tracker):
    """Rule 3: Verify Guardian kill switch halts gaze tracker within < 25.0ms SLA."""
    guardian.resume()
    tracker.reset_halt()

    # Warmup 1 cycle
    tracker.halt()
    tracker.reset_halt()

    latencies_ms = []
    for _ in range(50):
        t0 = time.perf_counter()
        tracker.halt()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)
        assert dt_ms < 25.0, f"Guardian SLA breached: {dt_ms}ms >= 25.0ms"

        # Verify execution is blocked
        with pytest.raises(RuntimeError) as exc_info:
            tracker.check_safety()
        assert "Guardian kill switch" in str(exc_info.value)

        tracker.reset_halt()

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    max_latency = max(latencies_ms)
    assert avg_latency < 1.0, f"Average halt latency {avg_latency:.4f}ms exceeds 1.0ms target"
    assert max_latency < 25.0, f"Max halt latency {max_latency:.4f}ms exceeds 25.0ms SLA"


def test_gaze_tracking_tools_registry_audit():
    """SAF-01: Verify all 4 gaze tracking tools are registered in ToolRegistry."""
    expected_tools = [
        "get_gaze_engagement_telemetry",
        "simulate_gaze_observation",
        "configure_gaze_thresholds",
        "reset_gaze_tracker_state",
    ]

    for tool_name in expected_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' not registered in ToolRegistry"
        assert tool_def.args_schema is not None
        assert callable(tool_def.preview_fn)

    # Verify Tiers
    assert registry.get("get_gaze_engagement_telemetry").tier == 0
    assert registry.get("simulate_gaze_observation").tier == 0
    assert registry.get("configure_gaze_thresholds").tier == 1
    assert registry.get("reset_gaze_tracker_state").tier == 0

    # Verify preview generation
    preview_telemetry = registry.get("get_gaze_engagement_telemetry").preview_fn({})
    assert "telemetry" in preview_telemetry

    preview_sim = registry.get("simulate_gaze_observation").preview_fn({"yaw": 10.0, "pitch": -5.0})
    assert "10.0" in preview_sim
