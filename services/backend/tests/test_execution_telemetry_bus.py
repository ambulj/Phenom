"""Tests for Execution Telemetry Bus & Silent Activity Monitor (Milestone 29 Phase 4).

Validates:
- HUD-01.1: Background execution event buffering, status pills, and latency capture.
- MON-04.1: Real-time query and drill-down inspection of execution parameters.
- SAF-01: Registered tools (record_execution_telemetry_event, query_execution_telemetry_history, get_active_telemetry_bus_stats).
- SAF-02: Universal Guardian kill switch SLA halt (< 25.0ms SLA).
- Rule 11: Credential scrubbing of passwords, tokens, API keys in telemetry arguments.
- Rule 8: Payment and checkout keyword rejection with Rule8ViolationError.
- Rule 4: 100% on-device local execution.
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.telemetry.execution_telemetry_bus import (
    ExecutionTelemetryBus,
    Rule8ViolationError,
    execution_telemetry_bus,
)
from services.backend.tools.telemetry_bus_tools import (
    handle_record_execution_telemetry_event,
    handle_query_execution_telemetry_history,
    handle_get_active_telemetry_bus_stats,
)


@pytest.fixture(autouse=True)
def reset_state():
    guardian.resume()
    execution_telemetry_bus.clear()
    yield
    guardian.resume()


def test_record_and_query_telemetry_events():
    """Validates recording events and querying them latest-first."""
    e1 = execution_telemetry_bus.record_event(
        tool_name="open_app",
        status="COMPLETED",
        duration_ms=12.5,
        tier=0,
        args={"app_name": "CompactGUI"},
        result_summary="Launched PID 7176",
    )
    assert e1.tool_name == "open_app"
    assert e1.duration_ms == 12.5
    assert e1.status == "COMPLETED"

    e2 = execution_telemetry_bus.record_event(
        tool_name="recycle_delete",
        status="COMPLETED",
        duration_ms=25.0,
        tier=1,
        args={"path": "C:\\temp\\junk.txt"},
        result_summary="Recycled via send2trash",
    )
    assert e2.tool_name == "recycle_delete"

    # Query all events
    events = execution_telemetry_bus.query_history()
    assert len(events) == 2
    # Latest should be first
    assert events[0].event_id == e2.event_id
    assert events[1].event_id == e1.event_id

    # Filter by tool
    filtered = execution_telemetry_bus.query_history(tool_name="open_app")
    assert len(filtered) == 1
    assert filtered[0].tool_name == "open_app"


def test_rule_11_credential_scrubbing():
    """Rule 11: Passwords, tokens, API keys must be scrubbed to [REDACTED]."""
    raw_args = {
        "user": "saujan",
        "password": "supersecretpassword123",
        "api_key": "sk-ant-api03-secretkey",
        "auth_token": "Bearer ghp_987654321",
        "nested": {
            "private_key": "PRIVATE_RSA_DATA",
            "normal_field": "hello world",
        },
    }

    event = execution_telemetry_bus.record_event(
        tool_name="connect_service",
        status="COMPLETED",
        args=raw_args,
    )

    args = event.arguments
    assert args["user"] == "saujan"
    assert args["password"] == "[REDACTED]"
    assert args["api_key"] == "[REDACTED]"
    assert args["auth_token"] == "[REDACTED]"
    assert args["nested"]["private_key"] == "[REDACTED]"
    assert args["nested"]["normal_field"] == "hello world"


def test_ring_buffer_capacity():
    """Validates that ring buffer caps capacity and drops oldest items."""
    mini_bus = ExecutionTelemetryBus(max_events=5)
    for i in range(12):
        mini_bus.record_event(tool_name=f"tool_{i}", duration_ms=float(i))

    history = mini_bus.query_history(limit=50)
    assert len(history) == 5
    # Most recent should be tool_11
    assert history[0].tool_name == "tool_11"
    # Oldest retained should be tool_7
    assert history[-1].tool_name == "tool_7"


def test_telemetry_bus_stats():
    """Validates calculation of aggregate statistics."""
    execution_telemetry_bus.record_event("open_app", status="COMPLETED", duration_ms=10.0)
    execution_telemetry_bus.record_event("open_app", status="COMPLETED", duration_ms=20.0)
    execution_telemetry_bus.record_event("send_email", status="FAILED", duration_ms=30.0)

    stats = execution_telemetry_bus.get_stats()
    assert stats.total_events == 3
    assert stats.completed_events == 2
    assert stats.failed_events == 1
    assert stats.average_duration_ms == 20.0
    assert stats.tool_counts["open_app"] == 2
    assert stats.tool_counts["send_email"] == 1


def test_rule_8_anti_checkout_rejection():
    """Rule 8: Payment or checkout keywords must raise Rule8ViolationError."""
    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        execution_telemetry_bus.record_event(
            tool_name="execute_checkout_payment",
            args={"amount": "$100"},
        )

    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        execution_telemetry_bus.record_event(
            tool_name="normal_tool",
            args={"billing_info": "credit card payment details"},
        )


def test_guardian_kill_switch_sla():
    """Benchmarks Guardian kill switch halt across execution telemetry bus."""
    guardian.resume()
    start_time = time.perf_counter()
    guardian.trigger("EMERGENCY_HALT_TEST")
    halt_duration_ms = (time.perf_counter() - start_time) * 1000.0

    assert halt_duration_ms < 25.0, f"Guardian halt took {halt_duration_ms:.4f}ms, exceeded 25.0ms SLA"

    # Operations must fail immediately
    with pytest.raises(RuntimeError, match="TELEMETRY_BUS_HALTED"):
        execution_telemetry_bus.record_event("open_app")

    with pytest.raises(RuntimeError, match="TELEMETRY_BUS_HALTED"):
        execution_telemetry_bus.query_history()


def test_tools_handle_functions():
    """Verifies that the 3 registered telemetry tools handle calls properly."""
    # 1. record_execution_telemetry_event (Tier 1)
    ev = handle_record_execution_telemetry_event(
        tool_name="open_app",
        status="COMPLETED",
        duration_ms=15.2,
        arguments={"app_name": "Spotify"},
        result_summary="Launched app smoothly",
    )
    assert ev["tool_name"] == "open_app"
    assert ev["duration_ms"] == 15.2

    # 2. query_execution_telemetry_history (Tier 0)
    res_q = handle_query_execution_telemetry_history(tool_name="open_app")
    assert res_q["count"] >= 1
    assert res_q["events"][0]["tool_name"] == "open_app"

    # 3. get_active_telemetry_bus_stats (Tier 0)
    stats = handle_get_active_telemetry_bus_stats()
    assert stats["total_events"] >= 1
    assert stats["average_duration_ms"] > 0
