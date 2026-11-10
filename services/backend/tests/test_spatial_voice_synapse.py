"""Unit and Safety Integration Tests for Adaptive Spatial Cursor-Voice Intent Interactor.

Validates cursor telemetry sampling, deictic spatial intent resolution, sub-35ms resolution SLA,
Rule 8 anti-checkout enforcement, and Guardian kill switch SLA.
Phase 24-03 (VOX-07, GES-01, SAF-01, SAF-02).
"""

import time
import pytest

from services.backend.spatial.cursor_telemetry_tracker import (
    CursorTelemetryTracker,
    CursorSpatialContext,
)
from services.backend.spatial.spatial_intent_resolver import (
    SpatialIntentResolver,
    Rule8ViolationError as SpatialRule8Error,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.spatial_voice_tools  # Ensure tools are loaded


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_cursor_telemetry_sampling_and_updates():
    """Verify cursor telemetry tracker accurately reports coordinates and window context."""
    tracker = CursorTelemetryTracker()

    ctx = tracker.get_cursor_context()
    assert isinstance(ctx, CursorSpatialContext)
    assert ctx.x >= 0 and ctx.y >= 0
    assert len(ctx.window_title) > 0

    updated = tracker.update_cursor_telemetry(
        x=1024,
        y=768,
        window_title="Phenom Editor - main.py",
        target_symbol="execute_pipeline",
        target_element="CodeEditor.EditorLine",
    )
    assert updated.x == 1024
    assert updated.y == 768
    assert updated.target_symbol == "execute_pipeline"
    assert updated.target_element == "CodeEditor.EditorLine"


def test_deictic_spatial_intent_resolution_and_latency_sla():
    """Verify spoken deictic directives map to target symbols in < 35ms SLA."""
    tracker = CursorTelemetryTracker()
    resolver = SpatialIntentResolver()

    ctx = tracker.update_cursor_telemetry(
        x=800,
        y=500,
        window_title="IDE",
        target_symbol="calculate_revenue_matrix",
    )

    t0 = time.perf_counter()
    intent = resolver.resolve_spatial_intent("refactor this function please", cursor_context=ctx)
    duration_ms = (time.perf_counter() - t0) * 1000.0

    assert intent.action_verb == "refactor"
    assert intent.resolved_target == "calculate_revenue_matrix"
    assert intent.is_deictic is True
    assert intent.confidence >= 0.90
    assert intent.bounding_box["width"] > 0
    assert duration_ms < 35.0, f"Resolution latency {duration_ms:.4f}ms exceeded 35.0ms SLA"

    # Non-deictic query
    intent_non_deictic = resolver.resolve_spatial_intent("run test suite", cursor_context=ctx)
    assert intent_non_deictic.action_verb == "test"
    assert intent_non_deictic.is_deictic is False


def test_spatial_target_highlight_beacon():
    """Verify target highlight broadcasts beacon coordinates (GES-01.1)."""
    resolver = SpatialIntentResolver()
    res = resolver.highlight_target("calculate_revenue_matrix")
    assert res["status"] == "highlighted"
    assert res["target_name"] == "calculate_revenue_matrix"
    assert "x" in res["beacon_coords"] and "y" in res["beacon_coords"]


def test_rule_8_anti_checkout_enforcement():
    """Verify Rule 8 payment / checkout rejection in spatial-voice commands and targets."""
    tracker = CursorTelemetryTracker()
    resolver = SpatialIntentResolver()

    with pytest.raises(SpatialRule8Error, match="Rule 8 violation"):
        resolver.resolve_spatial_intent("click buy now and complete checkout")

    ctx_bad = tracker.update_cursor_telemetry(
        x=400,
        y=300,
        target_symbol="process_credit_card_payment",
    )
    with pytest.raises(SpatialRule8Error, match="Rule 8 violation"):
        resolver.resolve_spatial_intent("refactor this", cursor_context=ctx_bad)


def test_guardian_kill_switch_sla_halt():
    """Verify Guardian kill switch halts spatial tracker and resolver in < 25.0ms SLA."""
    guardian.trigger("Emergency test halt")
    assert guardian.is_halted

    tracker = CursorTelemetryTracker()
    resolver = SpatialIntentResolver()

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        tracker.get_cursor_context()
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0
    assert latency_ms < 25.0, f"Halt latency {latency_ms:.4f}ms exceeded 25.0ms SLA"

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        resolver.resolve_spatial_intent("explain this")
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0
    assert latency_ms < 25.0, f"Halt latency {latency_ms:.4f}ms exceeded 25.0ms SLA"

    guardian.resume()


def test_tool_registry_and_previews():
    """Verify tool registration, tier classifications, and preview generations."""
    res_tool = registry.get("resolve_spatial_intent")
    assert res_tool is not None
    assert res_tool.tier == 0
    preview_res = res_tool.generate_preview({"spoken_command": "refactor this"})
    assert "refactor this" in preview_res

    ctx_tool = registry.get("get_cursor_spatial_context")
    assert ctx_tool is not None
    assert ctx_tool.tier == 0
    preview_ctx = ctx_tool.generate_preview({})
    assert "cursor" in preview_ctx

    hl_tool = registry.get("highlight_spatial_target")
    assert hl_tool is not None
    assert hl_tool.tier == 0
    preview_hl = hl_tool.generate_preview({"target_name": "target_btn"})
    assert "target_btn" in preview_hl
