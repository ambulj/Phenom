"""
Safety & Risk Tier Verification Tests for Spatial Canvas Tools (SAF-01, SAF-02).
Verifies:
- All 6 spatial tools are registered in ToolRegistry
- Tier 0 read-only classification for spatial_get_focus
- Tier 1 reversible change classification for overlay activation, annotations, and toggling
- Tool parameter schemas reject invalid inputs
- Guardian kill switch locks down all Tier 1 tools with PermissionError
"""

import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.spatial_tools as spatial_tools
from services.backend.spatial.canvas_manager import spatial_canvas_manager


EXPECTED_SPATIAL_TOOLS = {
    "spatial_get_focus": 0,
    "spatial_show_overlay": 1,
    "spatial_hide_overlay": 1,
    "spatial_add_annotation": 1,
    "spatial_dismiss_annotation": 1,
    "spatial_toggle_click_through": 1,
}


def test_spatial_tools_registered_with_correct_tiers():
    """Verify all 6 spatial tools exist in ToolRegistry with their required risk tiers."""
    for tool_name, expected_tier in EXPECTED_SPATIAL_TOOLS.items():
        assert tool_name in registry._tools, f"Tool '{tool_name}' must be registered in ToolRegistry"
        tool_meta = registry._tools[tool_name]
        assert tool_meta.tier == expected_tier, (
            f"Tool '{tool_name}' must have Risk Tier {expected_tier}, but got {tool_meta.tier}"
        )
        assert tool_meta.args_schema is not None, f"Tool '{tool_name}' must have an args_schema"
        assert tool_meta.preview_fn is not None, f"Tool '{tool_name}' must have a preview_fn"


def test_spatial_get_focus_tier_0_execution():
    """Verify Tier 0 spatial_get_focus executes and returns valid structure."""
    result = spatial_tools.spatial_get_focus()
    assert result["status"] == "success"
    assert "spatial_state" in result
    state = result["spatial_state"]
    assert "is_active" in state
    assert "click_through" in state
    assert "annotations" in state


def test_spatial_tier_1_annotation_and_dismissal():
    """Verify adding and dismissing annotations via tool functions."""
    # Ensure fresh state
    spatial_canvas_manager.reset()

    add_res = spatial_tools.spatial_add_annotation(
        title="Coding Assistant Note",
        content="Refactor complete with 100% tests passing.",
        anchor="top-right",
        style_preset="cyber_cyan",
    )
    assert add_res["status"] == "success"
    annotation = add_res["annotation"]
    ann_id = annotation["id"]
    assert annotation["title"] == "Coding Assistant Note"
    assert annotation["screen_x"] >= 0

    # Dismiss annotation
    dismiss_res = spatial_tools.spatial_dismiss_annotation(annotation_id=ann_id)
    assert dismiss_res["status"] == "success"
    assert dismiss_res["dismissed"] is True

    # Dismiss non-existent annotation
    miss_res = spatial_tools.spatial_dismiss_annotation(annotation_id="non_existent")
    assert miss_res["status"] == "not_found"
    assert miss_res["dismissed"] is False


def test_spatial_tier_1_overlay_controls():
    """Verify showing, hiding, and click-through controls via tool functions."""
    spatial_canvas_manager.reset()

    # Show
    show_res = spatial_tools.spatial_show_overlay(click_through=True)
    assert show_res["status"] == "success"
    assert show_res["spatial_state"]["is_active"] is True

    # Toggle click-through
    toggle_res = spatial_tools.spatial_toggle_click_through(enabled=False)
    assert toggle_res["status"] == "success"
    assert toggle_res["click_through"] is False

    # Hide
    hide_res = spatial_tools.spatial_hide_overlay()
    assert hide_res["status"] == "success"
    assert hide_res["spatial_state"]["is_active"] is False


def test_spatial_tools_guardian_lockdown():
    """Verify all Tier 1 spatial tools are immediately rejected under Guardian lockdown."""
    try:
        # Trip Guardian kill switch
        guardian.trigger("Spatial tools safety test")
        assert guardian.is_halted is True

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            spatial_tools.spatial_show_overlay()

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            spatial_tools.spatial_hide_overlay()

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            spatial_tools.spatial_add_annotation(title="Test", content="Fail")

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            spatial_tools.spatial_dismiss_annotation(annotation_id="any")

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            spatial_tools.spatial_toggle_click_through(enabled=True)

    finally:
        # Restore Guardian state
        guardian.resume()
        spatial_canvas_manager.reset()
        assert guardian.is_halted is False
