"""Unit test suite for Autonomous Vision-Action GUI Grounding & OS-World Windows 11 Automation (Milestone 31 Phase 1).

Tests:
- Visual coordinate predictor center computation (ACT-01.1).
- Safe Windows GUI action execution primitives (ACT-01.2).
- Immediate human takeover interrupt with < 5.0ms abort SLA (GUI-02.1).
- Human takeover latch reset and state recovery.
- Strict Rule 8 anti-checkout enforcement (GUI-02.2).
- Rule 11 credential protection and password field block.
- Guardian kill switch SLA < 25.0ms (Rule 3).
- Safety ToolRegistry registration and risk tiers (Tier 1 & Tier 0).
"""

from __future__ import annotations

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.vision.gui_action_grounder import (
    GUIActionGrounder,
    GUIAction,
    GUIActionType,
    BoundingBox,
    Rule8ViolationError,
)
import services.backend.tools.gui_action_tools  # noqa: F401


@pytest.fixture(autouse=True)
def clean_guardian_and_grounder():
    """Ensures guardian is resumed and grounder latch is cleared before and after each test."""
    guardian.resume()
    grounder = GUIActionGrounder()
    grounder.reset_takeover_latch(cursor_pos=(500, 500))
    grounder._last_mouse_pos = (500, 500)
    yield grounder
    guardian.resume()


def test_coordinate_prediction(clean_guardian_and_grounder):
    """ACT-01.1: Verify visual coordinate predictor calculates centered coordinates."""
    grounder = clean_guardian_and_grounder
    box = BoundingBox(
        x=200,
        y=300,
        width=100,
        height=60,
        label="Submit Button",
        control_type="Button",
    )
    center_x, center_y = grounder.predict_coordinates(box)
    assert center_x == 250
    assert center_y == 330


def test_grounded_action_execution(clean_guardian_and_grounder):
    """ACT-01.2: Verify execution of grounded desktop action primitives."""
    grounder = clean_guardian_and_grounder
    grounder._last_mouse_pos = (500, 500)

    # Click
    click_act = GUIAction(
        action_type=GUIActionType.CLICK,
        target_x=400,
        target_y=300,
        target_label="File Menu",
    )
    res_click = grounder.execute_action(click_act, simulated_cursor_pos=(500, 500))
    assert res_click.success is True
    assert res_click.status == "EXECUTED"
    assert res_click.coordinates == (400, 300)

    # Type text
    type_act = GUIAction(
        action_type=GUIActionType.TYPE_TEXT,
        target_x=400,
        target_y=300,
        text="Phenom Project Notes",
        target_label="Notes Title Input",
    )
    res_type = grounder.execute_action(type_act, simulated_cursor_pos=(400, 300))
    assert res_type.success is True
    assert res_type.status == "EXECUTED"

    # Drag and drop
    drag_act = GUIAction(
        action_type=GUIActionType.DRAG_AND_DROP,
        target_x=100,
        target_y=100,
        drag_to_x=300,
        drag_to_y=300,
        target_label="Canvas Node",
    )
    res_drag = grounder.execute_action(drag_act, simulated_cursor_pos=(400, 300))
    assert res_drag.success is True
    assert res_drag.status == "EXECUTED"


def test_human_takeover_interruption(clean_guardian_and_grounder):
    """GUI-02.1: Verify physical operator mouse movement halts automation in < 5.0ms."""
    grounder = clean_guardian_and_grounder
    grounder._last_mouse_pos = (500, 500)

    # Operator physically moves mouse from (500, 500) to (530, 540) (distance 50px > 15px)
    t0 = time.perf_counter()
    takeover_detected = grounder.detect_human_takeover(simulated_cursor_pos=(530, 540))
    detect_latency_ms = (time.perf_counter() - t0) * 1000.0

    assert takeover_detected is True
    assert detect_latency_ms < 5.0, f"Takeover detection latency {detect_latency_ms:.3f}ms exceeded 5.0ms SLA"

    # Subsequent action must immediately abort with ABORTED_BY_HUMAN
    act = GUIAction(
        action_type=GUIActionType.CLICK,
        target_x=800,
        target_y=600,
        target_label="Settings Tab",
    )
    t1 = time.perf_counter()
    res = grounder.execute_action(act, simulated_cursor_pos=(530, 540))
    abort_latency_ms = (time.perf_counter() - t1) * 1000.0

    assert res.success is False
    assert res.human_takeover is True
    assert res.status == "ABORTED_BY_HUMAN"
    assert abort_latency_ms < 5.0, f"Takeover abort latency {abort_latency_ms:.3f}ms exceeded 5.0ms SLA"


def test_takeover_latch_reset(clean_guardian_and_grounder):
    """Verify takeover latch can be safely cleared once operator yields control."""
    grounder = clean_guardian_and_grounder
    grounder._last_mouse_pos = (500, 500)
    grounder.detect_human_takeover(simulated_cursor_pos=(600, 600))
    assert grounder.detect_human_takeover(simulated_cursor_pos=(600, 600)) is True

    # Reset latch with operator's resting position
    status = grounder.reset_takeover_latch(cursor_pos=(600, 600))
    assert status["status"] == "RESET"
    assert status["human_takeover"] is False

    # Execution resumes successfully
    act = GUIAction(
        action_type=GUIActionType.CLICK,
        target_x=200,
        target_y=200,
        target_label="Resume Button",
    )
    res = grounder.execute_action(act, simulated_cursor_pos=(600, 600))
    assert res.success is True
    assert res.status == "EXECUTED"


def test_rule_8_anti_checkout_rejection(clean_guardian_and_grounder):
    """GUI-02.2: Strict Rule 8 anti-checkout enforcement blocks payment/billing UI targets."""
    grounder = clean_guardian_and_grounder
    grounder._last_mouse_pos = (500, 500)

    checkout_labels = [
        "Checkout Now",
        "Place Order",
        "Complete Payment",
        "Enter Credit Card CVV",
        "Billing Details",
    ]

    for label in checkout_labels:
        # BoundingBox prediction blocked
        box = BoundingBox(x=10, y=10, width=50, height=20, label=label)
        with pytest.raises(Rule8ViolationError):
            grounder.predict_coordinates(box)

        # Action execution blocked
        act = GUIAction(
            action_type=GUIActionType.CLICK,
            target_x=500,
            target_y=500,
            target_label=label,
        )
        with pytest.raises(Rule8ViolationError):
            grounder.execute_action(act, simulated_cursor_pos=(500, 500))


def test_rule_11_credential_protection(clean_guardian_and_grounder):
    """Rule 11: Keystroke automation forbidden on password fields and credentials scrubbed."""
    grounder = clean_guardian_and_grounder
    grounder._last_mouse_pos = (500, 500)

    # Password field keystroke blocked
    pwd_act = GUIAction(
        action_type=GUIActionType.TYPE_TEXT,
        target_x=300,
        target_y=400,
        text="supersecretpassword",
        target_label="Account Password Input",
    )
    with pytest.raises(ValueError, match="Rule 11 Violation"):
        grounder.execute_action(pwd_act, simulated_cursor_pos=(500, 500))

    # Token/API key scrubbing
    normal_act = GUIAction(
        action_type=GUIActionType.TYPE_TEXT,
        target_x=300,
        target_y=400,
        text="Exporting with api_key: sk-proj-1234567890abcdef12345678",
        target_label="Command Prompt",
    )
    res = grounder.execute_action(normal_act, simulated_cursor_pos=(500, 500))
    assert res.success is True
    assert "sk-proj" not in normal_act.text
    assert "[REDACTED]" in normal_act.text


def test_guardian_kill_switch_sla(clean_guardian_and_grounder):
    """Rule 3: Guardian kill switch halts action grounder with SLA < 25.0ms."""
    grounder = clean_guardian_and_grounder
    grounder._last_mouse_pos = (500, 500)

    # Trip guardian
    t0 = time.perf_counter()
    guardian.trigger("Emergency stop operator trigger")
    trip_latency_ms = (time.perf_counter() - t0) * 1000.0
    assert trip_latency_ms < 25.0

    act = GUIAction(
        action_type=GUIActionType.CLICK,
        target_x=100,
        target_y=100,
        target_label="Close Window",
    )

    t1 = time.perf_counter()
    with pytest.raises(RuntimeError, match="Execution halted by Guardian kill switch"):
        grounder.execute_action(act, simulated_cursor_pos=(500, 500))
    halt_check_latency_ms = (time.perf_counter() - t1) * 1000.0

    assert halt_check_latency_ms < 25.0, f"Guardian SLA {halt_check_latency_ms:.3f}ms exceeded 25.0ms"


def test_tool_registry_and_tiers():
    """Verify all 4 GUI action tools are registered with correct Safety tiers."""
    execute_tool = registry.get("execute_grounded_gui_action")
    predict_tool = registry.get("predict_ui_element_coordinates")
    takeover_tool = registry.get("get_human_takeover_status")
    reset_tool = registry.get("reset_human_takeover_latch")

    assert execute_tool is not None
    assert execute_tool.tier == 1  # Tier 1 confirmation required

    assert predict_tool is not None
    assert predict_tool.tier == 0  # Tier 0 read-only

    assert takeover_tool is not None
    assert takeover_tool.tier == 0  # Tier 0 read-only

    assert reset_tool is not None
    assert reset_tool.tier == 0  # Tier 0 safe reset
