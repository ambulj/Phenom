"""
Safety-Wrapped Multi-Display & Window Layout Choreography Tools.
Registers tools with ToolRegistry for display topology inspection, dynamic window layout
choreography, and reversible layout rollbacks (Phase 22-03 DSP-01 / WIN-03).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.spatial.multi_display_manager import multi_display_manager
from services.backend.spatial.layout_choreographer import (
    layout_choreographer,
    LayoutPreset,
    WindowPlacement,
)


# ==========================================
# 1. Detect Display Topology (Tier 0)
# ==========================================

class DetectDisplayTopologyArgs(BaseModel):
    force_refresh: bool = Field(default=False, description="Whether to query physical display APIs afresh")

def detect_display_topology_preview(args: Dict[str, Any]) -> str:
    return "Inspect connected monitor geometry, resolutions, coordinates, and DPI scaling factors."

@registry.register(
    name="detect_display_topology",
    tier=0,
    description="Detects all physical and virtual desktop monitors, screen boundaries, and DPI scales.",
    args_schema=DetectDisplayTopologyArgs,
    preview_fn=detect_display_topology_preview,
    can_remember_per_folder=False
)
def handle_detect_display_topology(force_refresh: bool = False) -> Dict[str, Any]:
    monitors = multi_display_manager.detect_monitors(force_refresh=force_refresh)
    primary = multi_display_manager.get_primary_monitor()
    vx, vy, vw, vh = multi_display_manager.get_virtual_desktop_bounds()

    return {
        "monitor_count": len(monitors),
        "primary_display": primary.display_id,
        "virtual_desktop_bounds": {"x": vx, "y": vy, "width": vw, "height": vh},
        "monitors": [m.model_dump() for m in monitors],
    }


# ==========================================
# 2. Apply Window Layout Preset (Tier 1)
# ==========================================

class ApplyWindowLayoutPresetArgs(BaseModel):
    preset_id: str = Field(..., description="Layout preset name: coding_focus, debugging_split, research_reading, monitoring_grid")

def apply_window_layout_preset_preview(args: Dict[str, Any]) -> str:
    pid = args.get("preset_id", "preset")
    return f"Choreograph desktop windows into '{pid}' spatial layout across displays (reversible snapshot)."

@registry.register(
    name="apply_window_layout_preset",
    tier=1,
    description="Reorganizes and positions active desktop windows according to a task-oriented spatial preset.",
    args_schema=ApplyWindowLayoutPresetArgs,
    preview_fn=apply_window_layout_preset_preview,
    can_remember_per_folder=False
)
def handle_apply_window_layout_preset(preset_id: str) -> Dict[str, Any]:
    return layout_choreographer.apply_layout_preset(preset_id=preset_id)


# ==========================================
# 3. Save Custom Layout Preset (Tier 1)
# ==========================================

class SaveCustomLayoutPresetArgs(BaseModel):
    preset_id: str = Field(..., description="Unique slug for the custom preset")
    name: str = Field(..., description="Human-readable preset name")
    description: str = Field(default="", description="Description of the preset")
    target_task: str = Field(default="custom", description="Associated task type")
    placements: List[Dict[str, Any]] = Field(..., description="List of WindowPlacement dictionaries")

def save_custom_layout_preset_preview(args: Dict[str, Any]) -> str:
    n = args.get("name", "custom preset")
    return f"Save custom spatial window layout preset '{n}'."

@registry.register(
    name="save_custom_layout_preset",
    tier=1,
    description="Saves a new custom multi-display window layout preset.",
    args_schema=SaveCustomLayoutPresetArgs,
    preview_fn=save_custom_layout_preset_preview,
    can_remember_per_folder=False
)
def handle_save_custom_layout_preset(
    preset_id: str,
    name: str,
    description: str,
    target_task: str,
    placements: List[Dict[str, Any]],
) -> Dict[str, Any]:
    pl_objs = [WindowPlacement(**p) for p in placements]
    preset = LayoutPreset(
        preset_id=preset_id,
        name=name,
        description=description,
        target_task=target_task,
        placements=pl_objs,
    )
    layout_choreographer._presets[preset_id] = preset
    return {"status": "saved", "preset_id": preset_id, "name": name, "window_count": len(pl_objs)}


# ==========================================
# 4. Get Active Layout State (Tier 0)
# ==========================================

class GetActiveLayoutStateArgs(BaseModel):
    pass

def get_active_layout_state_preview(args: Dict[str, Any]) -> str:
    return "Query active spatial layout preset and multi-display arrangement."

@registry.register(
    name="get_active_layout_state",
    tier=0,
    description="Returns the active window layout preset and monitor arrangement state.",
    args_schema=GetActiveLayoutStateArgs,
    preview_fn=get_active_layout_state_preview,
    can_remember_per_folder=False
)
def handle_get_active_layout_state() -> Dict[str, Any]:
    return layout_choreographer.get_active_state()


# Programmatic aliases
detect_display_topology = handle_detect_display_topology
apply_window_layout_preset = handle_apply_window_layout_preset
save_custom_layout_preset = handle_save_custom_layout_preset
get_active_layout_state = handle_get_active_layout_state
