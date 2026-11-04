"""Safety registry and execution tests for Milestone 13 Phase 2: Volumetric 3D Tools (SAF-01, SAF-02)."""

import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.volumetric.canvas_manager import volumetric_canvas_manager
import services.backend.tools.volumetric_tools as vol_tools


EXPECTED_VOLUMETRIC_TOOLS = {
    "volumetric_get_status": 0,
    "volumetric_set_projection": 1,
    "volumetric_spawn_node": 1,
    "volumetric_clear_canvas": 1,
    "volumetric_ingest_gesture": 1,
}


@pytest.fixture(autouse=True)
def clean_volumetric_state():
    guardian.resume()
    volumetric_canvas_manager.reset()
    volumetric_canvas_manager.clear_canvas()
    yield
    guardian.resume()
    volumetric_canvas_manager.reset()
    volumetric_canvas_manager.clear_canvas()


def test_volumetric_tools_registered_in_registry():
    """Verify all 5 volumetric tools are registered in ToolRegistry with their required risk tiers."""
    for tool_name, expected_tier in EXPECTED_VOLUMETRIC_TOOLS.items():
        assert tool_name in registry._tools, f"Tool '{tool_name}' must be in ToolRegistry"
        meta = registry._tools[tool_name]
        assert meta.tier == expected_tier, (
            f"Tool '{tool_name}' must have Risk Tier {expected_tier}, but got {meta.tier}"
        )
        assert meta.args_schema is not None
        assert meta.preview_fn is not None


def test_volumetric_get_status_tier_0():
    """Verify Tier 0 query executes cleanly."""
    res = vol_tools.volumetric_get_status()
    assert res["status"] == "success"
    assert "workspace_state" in res
    assert res["workspace_state"]["total_nodes"] == 0


def test_volumetric_spawn_and_set_projection_tier_1():
    """Verify Tier 1 operations with previews and node spawning."""
    spawn_meta = registry._tools["volumetric_spawn_node"]
    preview = spawn_meta.preview_fn({"label": "Orbital Graph", "x": 1.0, "y": 0.5, "z": 2.0, "depth_layer": 2})
    assert "Orbital Graph" in preview
    assert "(1.0, 0.5, 2.0)" in preview

    # Execute spawn
    spawn_res = vol_tools.volumetric_spawn_node(
        label="Orbital Graph",
        x=1.0,
        y=0.5,
        z=2.0,
        depth_layer=2,
        is_pinned=True,
    )
    assert spawn_res["status"] == "success"
    assert spawn_res["node"]["label"] == "Orbital Graph"

    # Set projection
    proj_res = vol_tools.volumetric_set_projection(mode="spherical")
    assert proj_res["status"] == "success"
    assert proj_res["projection_mode"] == "spherical"

    # Ingest gesture
    gest_res = vol_tools.volumetric_ingest_gesture(
        gesture_type="POINT",
        confidence=0.96,
        x=1.05,
        y=0.52,
        z=1.98,
    )
    assert gest_res["status"] == "success"
    assert gest_res["gesture"]["gesture_type"] == "POINT"

    # Clear canvas
    clear_res = vol_tools.volumetric_clear_canvas()
    assert clear_res["status"] == "success"
    assert clear_res["cleared_count"] == 1


def test_volumetric_tools_fail_closed_under_guardian_halt():
    """Verify fail-closed behavior under Guardian kill switch lockdown."""
    vol_tools.volumetric_spawn_node(label="Test Card", x=0.0, y=0.0, z=1.5)
    assert volumetric_canvas_manager.get_state().total_nodes == 1

    try:
        guardian.trigger("Emergency test halt")
        volumetric_canvas_manager.halt()

        assert volumetric_canvas_manager.is_halted() is True
        assert volumetric_canvas_manager.get_state().total_nodes == 0  # purged on halt

        # Tier 1 tools must raise PermissionError
        with pytest.raises(PermissionError, match="halted by Guardian"):
            vol_tools.volumetric_spawn_node(label="Blocked Card")

        with pytest.raises(PermissionError, match="halted by Guardian"):
            vol_tools.volumetric_set_projection(mode="planar")

        with pytest.raises(PermissionError, match="halted by Guardian"):
            vol_tools.volumetric_clear_canvas()

        with pytest.raises(PermissionError, match="halted by Guardian"):
            vol_tools.volumetric_ingest_gesture(gesture_type="POINT")

    finally:
        guardian.resume()
        volumetric_canvas_manager.reset()
