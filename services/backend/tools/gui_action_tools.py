"""Autonomous Vision-Action GUI Grounding Tools for Phenom (Milestone 31 Phase 1).

Registers 4 specialized tools in ToolRegistry:
1. execute_grounded_gui_action (Tier 1)
2. predict_ui_element_coordinates (Tier 0)
3. get_human_takeover_status (Tier 0)
4. reset_human_takeover_latch (Tier 0)
"""

from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.vision.gui_action_grounder import (
    gui_action_grounder,
    GUIAction,
    GUIActionType,
    BoundingBox,
)


# ==========================================
# 1. Execute Grounded GUI Action (Tier 1)
# ==========================================

class ExecuteGroundedGUIActionArgs(BaseModel):
    action_type: str = Field(
        ..., description="Action primitive: 'CLICK', 'DOUBLE_CLICK', 'RIGHT_CLICK', 'TYPE_TEXT', 'KEY_PRESS', 'SCROLL', 'DRAG_AND_DROP'."
    )
    target_x: int = Field(..., description="Target screen X coordinate.")
    target_y: int = Field(..., description="Target screen Y coordinate.")
    text: Optional[str] = Field(None, description="Text string to type if action is TYPE_TEXT.")
    key: Optional[str] = Field(None, description="Key name to press if action is KEY_PRESS (e.g. 'enter', 'tab').")
    drag_to_x: Optional[int] = Field(None, description="Destination X coordinate if action is DRAG_AND_DROP.")
    drag_to_y: Optional[int] = Field(None, description="Destination Y coordinate if action is DRAG_AND_DROP.")
    target_label: Optional[str] = Field(None, description="Human-readable label of target UI element.")


def preview_execute_grounded_gui_action(args: Dict[str, Any]) -> str:
    act = args.get("action_type", "CLICK")
    x = args.get("target_x", 0)
    y = args.get("target_y", 0)
    lbl = args.get("target_label") or "element"
    return f"Execute grounded GUI action [{act}] on '{lbl}' at ({x}, {y})"


@registry.register(
    name="execute_grounded_gui_action",
    tier=1,
    description="Executes a grounded GUI action (click, double click, right click, type, scroll, drag) on target coordinates with human takeover interrupt (Tier 1 action).",
    args_schema=ExecuteGroundedGUIActionArgs,
    preview_fn=preview_execute_grounded_gui_action,
    can_remember_per_folder=False,
)
def handle_execute_grounded_gui_action(
    action_type: str,
    target_x: int,
    target_y: int,
    text: Optional[str] = None,
    key: Optional[str] = None,
    drag_to_x: Optional[int] = None,
    drag_to_y: Optional[int] = None,
    target_label: Optional[str] = None,
) -> Dict[str, Any]:
    action_enum = GUIActionType(action_type.upper())
    action = GUIAction(
        action_type=action_enum,
        target_x=target_x,
        target_y=target_y,
        text=text,
        key=key,
        drag_to_x=drag_to_x,
        drag_to_y=drag_to_y,
        target_label=target_label,
    )
    result = gui_action_grounder.execute_action(action)
    return result.model_dump()


# ==========================================
# 2. Predict UI Element Coordinates (Tier 0)
# ==========================================

class PredictUIElementCoordinatesArgs(BaseModel):
    x: int = Field(..., description="Top-left X of bounding box.")
    y: int = Field(..., description="Top-left Y of bounding box.")
    width: int = Field(..., description="Width of bounding box.")
    height: int = Field(..., description="Height of bounding box.")
    label: str = Field(..., description="Element label or semantic description.")
    control_type: Optional[str] = Field("Button", description="Windows control type.")


def preview_predict_ui_element_coordinates(args: Dict[str, Any]) -> str:
    lbl = args.get("label", "element")
    return f"Calculate grounded center coordinates for UI element '{lbl}'"


@registry.register(
    name="predict_ui_element_coordinates",
    tier=0,
    description="Translates a visual bounding box into screen click target coordinates (Tier 0 read-only).",
    args_schema=PredictUIElementCoordinatesArgs,
    preview_fn=preview_predict_ui_element_coordinates,
    can_remember_per_folder=False,
)
def handle_predict_ui_element_coordinates(
    x: int,
    y: int,
    width: int,
    height: int,
    label: str,
    control_type: str = "Button",
) -> Dict[str, Any]:
    box = BoundingBox(
        x=x,
        y=y,
        width=width,
        height=height,
        label=label,
        control_type=control_type,
    )
    coords = gui_action_grounder.predict_coordinates(box)
    return {
        "target_coordinates": coords,
        "center_x": coords[0],
        "center_y": coords[1],
        "label": label,
    }


# ==========================================
# 3. Get Human Takeover Status (Tier 0)
# ==========================================

class GetHumanTakeoverStatusArgs(BaseModel):
    pass


def preview_get_human_takeover_status(args: Dict[str, Any]) -> str:
    return "Query whether operator physical human takeover is actively latching GUI automation"


@registry.register(
    name="get_human_takeover_status",
    tier=0,
    description="Returns real-time status of the human takeover watchdog, active cursor position, and recent actions (Tier 0 read-only).",
    args_schema=GetHumanTakeoverStatusArgs,
    preview_fn=preview_get_human_takeover_status,
    can_remember_per_folder=False,
)
def handle_get_human_takeover_status() -> Dict[str, Any]:
    return gui_action_grounder.get_status()


# ==========================================
# 4. Reset Human Takeover Latch (Tier 0)
# ==========================================

class ResetHumanTakeoverLatchArgs(BaseModel):
    pass


def preview_reset_human_takeover_latch(args: Dict[str, Any]) -> str:
    return "Reset human takeover latch and resume automated GUI execution capability"


@registry.register(
    name="reset_human_takeover_latch",
    tier=0,
    description="Resets the human takeover latch after operator yields physical control (Tier 0 safe reset).",
    args_schema=ResetHumanTakeoverLatchArgs,
    preview_fn=preview_reset_human_takeover_latch,
    can_remember_per_folder=False,
)
def handle_reset_human_takeover_latch() -> Dict[str, Any]:
    return gui_action_grounder.reset_takeover_latch()
