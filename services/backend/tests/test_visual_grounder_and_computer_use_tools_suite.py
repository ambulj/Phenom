"""Unit tests for Dual-Layer Vision Grounding & Computer-Use Tools (Milestone 45 Phase 3)."""

import time
import pytest
from services.backend.actions.synthetic_input import synthetic_input
from services.backend.actions.visual_grounder import (
    VisualGrounder,
    Rule8ViolationError,
    PrivacyShieldError,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.vision.screen_classifier import OCRBoundingBox
from services.backend.tools.computer_use_tools import (
    handle_execute_desktop_click,
    handle_execute_desktop_keystrokes,
    handle_execute_desktop_action_sequence,
    handle_resolve_visual_target_coordinates,
    handle_get_computer_use_status,
)


@pytest.fixture(autouse=True)
def clean_guardian_and_grounder():
    """Reset guardian and synthetic input before and after each test."""
    guardian.resume()
    synthetic_input.dry_run = True
    synthetic_input.recorded_events.clear()
    yield
    guardian.resume()
    synthetic_input.dry_run = False


def create_sample_ocr_boxes() -> list[OCRBoundingBox]:
    return [
        OCRBoundingBox(text="Run Python File", x=1100, y=120, width=100, height=30, confidence=0.98),
        OCRBoundingBox(text="Terminal: bash", x=200, y=800, width=300, height=40, confidence=0.95),
        OCRBoundingBox(text="Save All Files", x=50, y=60, width=80, height=25, confidence=0.92),
    ]


def test_local_ocr_coordinate_grounding_latency_under_20ms():
    """Validates sub-20ms local OCR text-target coordinate grounding on RTX 3050."""
    grounder = VisualGrounder(dry_run=True)
    grounder.set_mock_ocr_boxes(create_sample_ocr_boxes())

    t0 = time.perf_counter()
    pt, layer, meta = grounder.resolve_target("Run Python")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert layer == "LOCAL_OCR"
    assert pt.x == 1150  # 1100 + 100 // 2
    assert pt.y == 135   # 120 + 30 // 2
    assert meta["matched_text"] == "Run Python File"
    assert elapsed_ms < 20.0, f"Local OCR grounding latency too high: {elapsed_ms}ms >= 20.0ms"


def test_cloud_vision_escalation_for_spatial_icons():
    """Tests that non-text spatial icons escalate to Cloud Vision with privacy preview and PII check."""
    grounder = VisualGrounder(dry_run=True)
    grounder.set_mock_ocr_boxes(create_sample_ocr_boxes())

    pt, layer, meta = grounder.resolve_target("settings gear icon", allow_cloud_escalation=True)

    assert layer == "CLOUD_VISION"
    assert pt.x == 1880
    assert pt.y == 45
    assert meta["spatial_target"] == "settings gear icon"
    assert "pii_redacted_count" in meta


def test_sensitive_window_blocks_visual_grounding_rule_4():
    """Tests that active password managers or banking portals immediately block visual grounding."""
    grounder = VisualGrounder(dry_run=True)
    grounder.set_mock_ocr_boxes(create_sample_ocr_boxes())

    with pytest.raises(PrivacyShieldError) as exc_info:
        grounder.resolve_target(
            query="Login",
            active_window_title="KeePassXC - Passwords.kdbx",
            active_window_process="keepassxc.exe",
        )
    assert "Rule 4 Violation" in str(exc_info.value)
    assert "is blinded" in str(exc_info.value)


def test_anti_checkout_rule_8_hard_wall():
    """Tests that queries targeting checkout, purchasing, or credit cards are strictly blocked by Rule 8."""
    grounder = VisualGrounder(dry_run=True)
    grounder.set_mock_ocr_boxes(create_sample_ocr_boxes())

    forbidden_queries = [
        "click checkout button",
        "place order now",
        "pay now with credit card",
        "submit order and CVV",
    ]

    for q in forbidden_queries:
        with pytest.raises(Rule8ViolationError) as exc_info:
            grounder.resolve_target(q)
        assert "Rule 8 Violation" in str(exc_info.value)


def test_computer_use_tools_registration_and_execution():
    """Verifies that all 5 computer-use tools are registered in Safety registry and execute cleanly."""
    expected_tools = [
        "execute_desktop_click",
        "execute_desktop_keystrokes",
        "execute_desktop_action_sequence",
        "resolve_visual_target_coordinates",
        "get_computer_use_status",
    ]

    for tool_name in expected_tools:
        tool_entry = registry.get(tool_name)
        assert tool_entry is not None, f"Tool '{tool_name}' not registered in Safety registry"

    # Test coordinate click
    click_res = handle_execute_desktop_click(target_x=500, target_y=300, click_type="left")
    assert click_res["success"] is True
    assert click_res["clicked_point"] == {"x": 500, "y": 300}

    # Test keystrokes
    type_res = handle_execute_desktop_keystrokes(text="nmap -sS 127.0.0.1", press_enter=True)
    assert type_res["success"] is True
    assert type_res["characters_typed"] == len("nmap -sS 127.0.0.1")

    # Test status
    status_res = handle_get_computer_use_status()
    assert status_res["is_halted"] is False
    assert status_res["dry_run"] is True


def test_guardian_halt_blocks_computer_use_tools():
    """Tests that Guardian Kill Switch immediately blocks tool execution."""
    guardian.trigger("Emergency halt triggered during desktop action")

    click_res = handle_execute_desktop_click(target_x=100, target_y=100)
    assert click_res["success"] is False
    assert click_res["guardian_halted"] is True

    type_res = handle_execute_desktop_keystrokes(text="should not type")
    assert type_res["success"] is False
    assert type_res["guardian_halted"] is True

    coord_res = handle_resolve_visual_target_coordinates(query="Run")
    assert coord_res["success"] is False
    assert coord_res["guardian_halted"] is True
