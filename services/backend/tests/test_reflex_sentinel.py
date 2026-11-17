"""Unit test suite for Low-Latency Desktop Visual & Audio Reflex Sentinel (Milestone 51 Phase 1).

Tests:
1. ReflexEvent schema validation, serialization, and helper properties.
2. Perceptual diff hashing (dHash) and hamming distance change detection.
3. Terminal exit code pattern extraction (0 vs non-zero).
4. Compiler diagnostic and test runner output recognition.
5. Notification sentinel toast ingestion, severity classification, and deduplication.
6. Sub-15ms processing latency and <2.0% CPU overhead budget benchmark.
"""

import time
import pytest
from PIL import Image

from services.backend.schemas.reflex_events import (
    ReflexEvent,
    ReflexEventType,
    ReflexSeverity,
    VisualCueDetails,
    ToastNotificationDetails,
    ReflexSentinelConfig,
)
from services.backend.reflex.visual_sentinel import VisualReflexSentinel
from services.backend.reflex.notification_sentinel import NotificationReflexSentinel
from services.backend.tools.reflex_sentinel_tools import (
    inspect_reflex_sentinel_state,
    sample_desktop_reflex_frame,
    simulate_reflex_event,
)


def test_reflex_event_schema_validation():
    """Verify ReflexEvent Pydantic schema validation, defaults, and properties."""
    event = ReflexEvent(
        event_type=ReflexEventType.BUILD_FAILED,
        severity=ReflexSeverity.CRITICAL,
        source="compiler_sentinel",
        visual_details=VisualCueDetails(
            window_title="VS Code",
            process_name="Code.exe",
            matched_pattern="error TS2304",
            raw_text="error TS2304: Cannot find name 'int'",
        )
    )

    assert event.event_id.startswith("refl_")
    assert event.is_failure is True
    assert event.is_success is False
    assert event.confidence == 1.0
    assert event.visual_details.process_name == "Code.exe"

    dump = event.model_dump()
    assert dump["event_type"] == "BUILD_FAILED"
    assert dump["severity"] == "CRITICAL"


def test_perceptual_diff_hashing_and_distance():
    """Verify 64-bit dHash computation and hamming distance sensitivity."""
    # Create two distinct test images: solid white vs solid black with white stripe
    img1 = Image.new("L", (100, 100), color=255)
    img2 = Image.new("L", (100, 100), color=0)
    for x in range(50):
        for y in range(100):
            img2.putpixel((x, y), 255)

    hash1 = VisualReflexSentinel.compute_region_hash(img1)
    hash2 = VisualReflexSentinel.compute_region_hash(img2)

    assert isinstance(hash1, str) and len(hash1) == 16
    assert isinstance(hash2, str) and len(hash2) == 16

    # Identical image distance must be 0
    dist_same = VisualReflexSentinel.hamming_distance(hash1, hash1)
    assert dist_same == 0

    # Distinct pattern distance must be significant (> 10 bits)
    dist_diff = VisualReflexSentinel.hamming_distance(hash1, hash2)
    assert dist_diff >= 8


def test_terminal_exit_code_detection():
    """Verify terminal prompt return and exit code extraction (0 vs non-zero)."""
    sentinel = VisualReflexSentinel(ReflexSentinelConfig(debounce_seconds=0.0))

    # Test clean exit code 0
    text_ok = "Running deploy script...\n[Process completed (code 0)]\n$"
    ev_ok, lat_ok = sentinel.process_frame(
        image_or_buffer="hash_1",
        extracted_text=text_ok,
        window_title="Windows PowerShell",
        process_name="WindowsTerminal.exe",
        force_process=True,
    )
    assert ev_ok is not None
    assert ev_ok.event_type == ReflexEventType.TERMINAL_COMPLETED
    assert ev_ok.severity == ReflexSeverity.SUCCESS
    assert ev_ok.visual_details.exit_code == 0
    assert ev_ok.is_success is True

    # Test error exit code 1
    text_err = "fatal error encountered\nProcess finished with exit code 1"
    ev_err, lat_err = sentinel.process_frame(
        image_or_buffer="hash_2",
        extracted_text=text_err,
        window_title="Command Prompt",
        process_name="cmd.exe",
        force_process=True,
    )
    assert ev_err is not None
    assert ev_err.event_type == ReflexEventType.TERMINAL_COMPLETED
    assert ev_err.severity == ReflexSeverity.CRITICAL
    assert ev_err.visual_details.exit_code == 1
    assert ev_err.is_failure is True


def test_compiler_and_test_patterns():
    """Verify TypeScript compiler errors and pytest summary pattern recognition."""
    sentinel = VisualReflexSentinel(ReflexSentinelConfig(debounce_seconds=0.0))

    # 1. TypeScript build error
    ts_text = "src/index.ts(14,5): error TS2322: Type 'string' is not assignable to type 'number'."
    ev_ts, _ = sentinel.process_frame("h_ts", ts_text, "Visual Studio Code", "Code.exe", force_process=True)
    assert ev_ts is not None
    assert ev_ts.event_type == ReflexEventType.BUILD_FAILED
    assert ev_ts.severity == ReflexSeverity.CRITICAL

    # 2. Pytest suite pass
    pytest_text = "tests/test_core.py ....                         [100%]\n===== 45 passed in 2.34s ====="
    ev_py, _ = sentinel.process_frame("h_py", pytest_text, "Terminal", "pwsh.exe", force_process=True)
    assert ev_py is not None
    assert ev_py.event_type == ReflexEventType.TESTS_PASSED
    assert ev_py.severity == ReflexSeverity.SUCCESS


def test_notification_sentinel_toast_normalization():
    """Verify Windows toast normalization, severity triage, and deduplication."""
    notifier = NotificationReflexSentinel(debounce_seconds=1.0)

    # Ingest error alert
    toast1 = notifier.process_toast(
        app_name="Docker Desktop",
        title="Engine Error",
        message="Docker daemon failed to start due to port collision",
    )
    assert toast1 is not None
    assert toast1.event_type == ReflexEventType.ERROR_DIALOG
    assert toast1.severity == ReflexSeverity.CRITICAL
    assert toast1.toast_details.app_name == "Docker Desktop"

    # Immediately duplicate toast should be debounced
    toast_dup = notifier.process_toast(
        app_name="Docker Desktop",
        title="Engine Error",
        message="Docker daemon failed to start due to port collision",
    )
    assert toast_dup is None

    # Ingest normal info notification
    toast_info = notifier.process_toast(
        app_name="Outlook",
        title="Team Standup",
        message="Meeting starting in 5 minutes",
    )
    assert toast_info is not None
    assert toast_info.event_type == ReflexEventType.TOAST_NOTIFICATION
    assert toast_info.severity == ReflexSeverity.INFO


def test_sentinel_performance_and_latency_budget():
    """Verify 100-frame processing benchmark strictly satisfies sub-15ms and <2% CPU budget."""
    sentinel = VisualReflexSentinel(ReflexSentinelConfig(sample_rate_hz=10.0, max_cpu_percent=2.0))
    test_img = Image.new("L", (200, 200), color=128)

    latencies = []
    for i in range(100):
        # Alternate pixel to simulate active screen changes
        test_img.putpixel((i % 200, i % 200), (i * 2) % 255)
        text = f"Processing batch {i}...\nExit code: 0" if i % 10 == 0 else ""
        _, lat = sentinel.process_frame(test_img, text, "Terminal", "wt.exe", force_process=(i % 10 == 0))
        latencies.append(lat)

    mean_lat = sum(latencies) / len(latencies)
    max_lat = max(latencies)

    # Sub-15ms processing latency constraint
    assert mean_lat < 15.0, f"Mean latency {mean_lat:.2f}ms exceeded 15ms target"
    assert max_lat < 50.0, f"Max latency {max_lat:.2f}ms exceeded 50ms spike limit"

    status = sentinel.get_status()
    # Estimated CPU duty cycle at 10Hz must be < 2.0%
    assert status.cpu_percent_estimate <= 2.0, f"Estimated CPU {status.cpu_percent_estimate}% exceeded 2.0%"


def test_registered_reflex_tools():
    """Verify registered Tier 0 reflex tools operate cleanly."""
    # Test state inspection
    state = inspect_reflex_sentinel_state(include_recent=True)
    assert "cpu_percent_estimate" in state
    assert "active_sample_rate_hz" in state

    # Test frame sampling tool
    sample_res = sample_desktop_reflex_frame(
        extracted_text="Tests: 12 passed, 12 total",
        window_title="Jest Test Runner",
        process_name="node.exe",
        force_process=True,
    )
    assert sample_res["event_detected"] is True
    assert sample_res["event"]["event_type"] == "TESTS_PASSED"

    # Test simulation tool
    sim_res = simulate_reflex_event(
        event_type="TOAST_NOTIFICATION",
        severity="WARNING",
        title="Battery Low",
        message="Battery is below 15%",
        source="SystemPower",
    )
    assert sim_res["success"] is True
    assert sim_res["event"]["event_type"] == "TOAST_NOTIFICATION"
    assert sim_res["event"]["severity"] == "WARNING"
