"""
Tests for Multi-Display Spatial Holographic Canvas & Dynamic Window Layout Choreography.
Part of Phenom 22.0 Sovereign Swarm Intelligence (DSP-01, WIN-03, SAF-01, SAF-02).
"""

import time
import pytest
from typing import Dict, Any

from services.backend.spatial.multi_display_manager import (
    MultiDisplayManager,
    DisplayGeometry,
    multi_display_manager,
)
from services.backend.spatial.layout_choreographer import (
    LayoutChoreographer,
    LayoutPreset,
    WindowPlacement,
    layout_choreographer,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.spatial_layout_tools as layout_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_multi_display_monitor_detection():
    """Verify monitor enumeration returns valid display geometries."""
    manager = MultiDisplayManager()
    displays = manager.detect_monitors(force_refresh=True)

    assert len(displays) >= 1
    primary = manager.get_primary_monitor()
    assert primary.is_primary is True
    assert primary.width > 0
    assert primary.height > 0

    vx, vy, vw, vh = manager.get_virtual_desktop_bounds()
    assert vw >= primary.width
    assert vh >= primary.height


def test_built_in_layout_presets_registration():
    """Verify standard task-driven layout presets are available."""
    choreographer = LayoutChoreographer()
    presets = choreographer.list_presets()
    preset_ids = [p.preset_id for p in presets]

    assert "coding_focus" in preset_ids
    assert "debugging_split" in preset_ids
    assert "research_reading" in preset_ids
    assert "monitoring_grid" in preset_ids


def test_dynamic_coordinate_scaling():
    """Verify window coordinates are proportionally scaled to target display resolution."""
    choreographer = LayoutChoreographer()
    placements = choreographer.calculate_preset_coordinates("coding_focus")

    assert len(placements) == 3
    for p in placements:
        assert p.width >= 400
        assert p.height >= 300
        assert p.app_identifier in ["code", "terminal", "chrome"]


def test_apply_layout_preset_and_reversible_rollback():
    """Verify Rule 7: applying a layout creates a snapshot and rollback restores previous state."""
    choreographer = LayoutChoreographer()

    # Step 1: Apply coding_focus
    res1 = choreographer.apply_layout_preset("coding_focus")
    assert res1["status"] == "applied"
    assert res1["preset_id"] == "coding_focus"
    assert choreographer._active_preset == "coding_focus"

    # Step 2: Apply debugging_split
    res2 = choreographer.apply_layout_preset("debugging_split")
    assert res2["status"] == "applied"
    assert res2["preset_id"] == "debugging_split"
    assert choreographer._active_preset == "debugging_split"

    # Step 3: Rollback (Rule 7)
    rb = choreographer.rollback_last_layout()
    assert rb["status"] == "rolled_back"
    assert rb["preset_id"] == "coding_focus"
    assert choreographer._active_preset == "coding_focus"


def test_custom_layout_preset_creation():
    """Verify saving a new customized multi-display layout preset."""
    res = layout_tools.save_custom_layout_preset(
        preset_id="custom_cinema",
        name="Cinema Streaming View",
        description="Full-screen video player with side chat",
        target_task="media",
        placements=[
            {"app_identifier": "mpv", "display_id": "DISPLAY_1", "x": 0, "y": 0, "width": 2000, "height": 1440},
            {"app_identifier": "browser", "display_id": "DISPLAY_1", "x": 2000, "y": 0, "width": 560, "height": 1440},
        ]
    )

    assert res["status"] == "saved"
    assert res["preset_id"] == "custom_cinema"
    assert res["window_count"] == 2

    # Verify preset exists in choreographer
    saved = layout_choreographer.get_preset("custom_cinema")
    assert saved is not None
    assert saved.name == "Cinema Streaming View"


def test_guardian_kill_switch_sla_halt():
    """Guardian trigger must synchronously interrupt window layout choreography in < 25.0ms SLA."""
    guardian.trigger()
    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        layout_choreographer.apply_layout_preset("coding_focus")
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Guardian SLA exceeded: {latency_ms:.4f}ms >= 25.0ms"


def test_tool_registry_and_previews():
    """Verify tool registration and preview generator functions in ToolRegistry."""
    tool_names = [
        "detect_display_topology",
        "apply_window_layout_preset",
        "save_custom_layout_preset",
        "get_active_layout_state",
    ]
    for name in tool_names:
        tool = registry.get(name)
        assert tool is not None, f"Tool {name} is not registered in ToolRegistry"
        assert callable(tool.handler_fn)

    # Preview generators
    preview_detect = registry.get("detect_display_topology").generate_preview({})
    assert "monitor geometry" in preview_detect.lower()

    preview_apply = registry.get("apply_window_layout_preset").generate_preview({"preset_id": "coding_focus"})
    assert "coding_focus" in preview_apply
    assert "reversible" in preview_apply.lower()
