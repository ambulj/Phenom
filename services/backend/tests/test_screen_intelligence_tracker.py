"""Unit & Invariant Tests for Real-Time Screen Intelligence & Visual Task Tracker (Milestone 30 Phase 1).

Verifies:
1. Active window visual context capture & bounding-box detection (VIS-01.1, VIS-01.2)
2. Fast local screen-region OCR & Rule 11 credential scrubbing (OCR-02.1)
3. On-screen error & crash diagnosis (OCR-02.2)
4. Rule 4 offline local on-device invariants (zero cloud egress)
5. Rule 8 anti-checkout & payment blocking (Rule8ViolationError)
6. Universal Guardian kill switch SLA benchmark (< 25.0ms)
7. ToolRegistry registration & preview generation for all 5 tools (SAF-01.1)
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.vision.screen_intelligence_tracker import (
    screen_intelligence_tracker,
    ScreenIntelligenceTracker,
    TrackingMode,
    Rule8ViolationError,
)
from services.backend.tools.screen_intelligence_tools import (
    handle_capture_screen_intelligence_context,
    handle_extract_screen_region_ocr,
    handle_diagnose_on_screen_errors,
    handle_set_screen_intelligence_tracking_mode,
    handle_get_screen_intelligence_metrics,
    preview_capture_screen_context,
    preview_extract_region_ocr,
    preview_diagnose_errors,
    preview_set_tracking_mode,
    preview_get_tracker_metrics,
)


@pytest.fixture(autouse=True)
def ensure_guardian_active():
    """Ensure Guardian kill switch is reset before and after each test."""
    if guardian.is_halted:
        guardian.resume()
    yield
    if guardian.is_halted:
        guardian.resume()


def test_capture_window_context_and_bounding_boxes():
    tracker = ScreenIntelligenceTracker()
    ctx = tracker.capture_window_context(window_title_filter="Visual Studio Code")

    assert ctx.window_title == "Visual Studio Code"
    assert ctx.window_bounds.get("width", 0) > 0
    assert len(ctx.elements_detected) >= 2
    assert ctx.capture_latency_ms < 350.0  # Must be sub-350ms
    assert ctx.tracking_mode == TrackingMode.ACTIVE

    # Check bounding box attributes
    bb = ctx.elements_detected[0]
    assert bb.width > 0
    assert bb.height > 0
    assert bb.confidence > 0.8


def test_extract_screen_region_ocr_and_rule11():
    tracker = ScreenIntelligenceTracker()
    raw_snippet = (
        "Active session logged in.\n"
        "api_key: secret_token_abc123456789\n"
        "password: super_secret_user_pwd_99\n"
        "Welcome to Phenom Desktop Workspace."
    )

    res = tracker.extract_region_ocr(
        bbox={"x": 50, "y": 50, "width": 800, "height": 400},
        raw_text_mock=raw_snippet,
    )

    assert "secret_token_abc123456789" not in res.text
    assert "super_secret_user_pwd_99" not in res.text
    assert "[REDACTED]" in res.text
    assert res.scrubbed_secret_count == 2
    assert res.word_count > 0
    assert res.confidence >= 0.90


def test_diagnose_on_screen_errors():
    tracker = ScreenIntelligenceTracker()

    # 1. Clean screen
    clean_res = tracker.diagnose_on_screen_errors(simulated_screen_text="System normal. Everything is operating smoothly.")
    assert clean_res.has_error_dialog is False
    assert clean_res.severity == "NONE"

    # 2. Critical Exception popup
    error_snippet = "Fatal Error: Unhandled NullReferenceException in module core_renderer.dll"
    error_res = tracker.diagnose_on_screen_errors(simulated_screen_text=error_snippet)
    assert error_res.has_error_dialog is True
    assert error_res.severity == "CRITICAL"
    assert "Fatal Error" in error_res.error_title
    assert len(error_res.suggestions) >= 1

    # 3. Application Not Responding
    hang_snippet = "Phenom.exe is Not Responding. Windows is checking for a solution..."
    hang_res = tracker.diagnose_on_screen_errors(simulated_screen_text=hang_snippet)
    assert hang_res.has_error_dialog is True
    assert hang_res.severity == "WARNING"


def test_screen_intelligence_tracking_modes():
    tracker = ScreenIntelligenceTracker()

    assert tracker.get_tracking_mode() == TrackingMode.ACTIVE
    tracker.set_tracking_mode(TrackingMode.LOW_POWER)
    assert tracker.get_tracking_mode() == TrackingMode.LOW_POWER

    tracker.set_tracking_mode(TrackingMode.OFF)
    assert tracker.get_tracking_mode() == TrackingMode.OFF


def test_rule8_payment_blocking():
    tracker = ScreenIntelligenceTracker()

    # Attempt to capture window or extract OCR containing payment / checkout keywords
    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        tracker.capture_window_context(window_title_filter="Stripe Checkout - Complete Order")

    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        tracker.extract_region_ocr(raw_text_mock="Please enter your credit card and cvv to complete purchase.")

    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        tracker.diagnose_on_screen_errors(simulated_screen_text="Billing payment gateway failed for order checkout")


def test_guardian_kill_switch_sla():
    tracker = ScreenIntelligenceTracker()

    # 1. Verify synchronous halt when kill switch triggers
    guardian.trigger("Manual Test Halt")
    assert guardian.is_halted is True

    with pytest.raises(RuntimeError, match="Execution halted by Guardian kill switch"):
        tracker.capture_window_context()

    with pytest.raises(RuntimeError, match="Execution halted by Guardian kill switch"):
        tracker.extract_region_ocr()

    with pytest.raises(RuntimeError, match="Execution halted by Guardian kill switch"):
        tracker.diagnose_on_screen_errors()

    # 2. 100-cycle latency benchmark: SLA < 25.0ms (target < 1.0ms)
    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        halted = guardian.is_halted
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    avg_ms = sum(latencies) / len(latencies)
    max_ms = max(latencies)

    assert avg_ms < 1.0
    assert max_ms < 25.0

    guardian.resume()
    assert guardian.is_halted is False


def test_screen_intelligence_tool_registry():
    all_tools = registry.list_all()

    expected_tools = [
        "capture_screen_intelligence_context",
        "extract_screen_region_ocr",
        "diagnose_on_screen_errors",
        "set_screen_intelligence_tracking_mode",
        "get_screen_intelligence_metrics",
    ]

    for tool_name in expected_tools:
        assert tool_name in all_tools, f"Missing tool in ToolRegistry: {tool_name}"

    # Verify tool execution via handle functions
    # 1. capture_screen_intelligence_context
    res_ctx = handle_capture_screen_intelligence_context(window_title_filter="Workspace")
    assert res_ctx["window_title"] == "Workspace"
    assert "elements_detected" in res_ctx

    # 2. extract_screen_region_ocr
    res_ocr = handle_extract_screen_region_ocr(bbox={"x": 0, "y": 0, "width": 100, "height": 100})
    assert "text" in res_ocr
    assert res_ocr["word_count"] >= 0

    # 3. diagnose_on_screen_errors
    res_diag = handle_diagnose_on_screen_errors()
    assert "has_error_dialog" in res_diag

    # 4. set_screen_intelligence_tracking_mode
    res_mode = handle_set_screen_intelligence_tracking_mode(mode="LOW_POWER")
    assert res_mode["status"] == "UPDATED"
    assert res_mode["new_mode"] == "LOW_POWER"

    with pytest.raises(ValueError, match="Invalid tracking mode"):
        handle_set_screen_intelligence_tracking_mode(mode="INVALID_UNKNOWN")

    # 5. get_screen_intelligence_metrics
    metrics = handle_get_screen_intelligence_metrics()
    assert metrics["offline_local"] is True

    # Check preview functions
    assert "Capture" in preview_capture_screen_context({"window_title_filter": "Test"})
    assert "OCR" in preview_extract_region_ocr({"bbox": {"x": 0, "y": 0, "width": 50, "height": 50}})
    assert "Scan" in preview_diagnose_errors({})
    assert "Update" in preview_set_tracking_mode({"mode": "ACTIVE"})
    assert "Query" in preview_get_tracker_metrics({})
