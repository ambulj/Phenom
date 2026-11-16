"""Desktop Choreography Tools Registration for Phenom (Milestone 49 Phase 4, CHOREO-01, CHOREO-02, CHOREO-03).

Exposes:
1. `execute_choreographed_action` (Tier 1) - Executes choreographed cross-app desktop action step with focus validation.
2. `preview_target_halo` (Tier 0) - Renders CyberHUD visual target halo over target screen element.
3. `generate_bezier_trajectory` (Tier 0) - Generates humanized cubic Bezier trajectory with micro-jitter.
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.schemas.desktop_choreography import (
    BezierTrajectory,
    DesktopActionStep,
    DesktopActionType,
    TargetHaloSpec,
)
from services.backend.desktop.bezier_trajectory_generator import BezierTrajectoryGenerator
from services.backend.desktop.visual_target_halo import VisualTargetHaloEmitter
from services.backend.desktop.desktop_choreographer import DesktopChoreographer

# Singletons
trajectory_generator = BezierTrajectoryGenerator()
halo_emitter = VisualTargetHaloEmitter()
desktop_choreographer = DesktopChoreographer(
    trajectory_gen=trajectory_generator,
    halo_emitter=halo_emitter,
)


# ============================================================================
# 1. execute_choreographed_action (Tier 1)
# ============================================================================

class ExecuteChoreographedActionArgs(BaseModel):
    action_type: str = Field(default="CLICK", description="CLICK, MOVE, TYPE_TEXT, KEY_COMBO, SCROLL")
    target_window_title: Optional[str] = Field(default=None, description="Expected window title substring")
    target_x: Optional[int] = Field(default=None, description="Target X coordinate")
    target_y: Optional[int] = Field(default=None, description="Target Y coordinate")
    target_element_name: Optional[str] = Field(default=None, description="Name or label of target UI element")
    text_payload: Optional[str] = Field(default=None, description="Text string to type")
    duration_ms: int = Field(default=300, description="Action duration in ms")


def execute_choreographed_action_preview(args: Dict[str, Any]) -> str:
    act = args.get("action_type", "CLICK")
    elem = args.get("target_element_name") or f"coordinates ({args.get('target_x')}, {args.get('target_y')})"
    win = args.get("target_window_title") or "active window"
    return f"Execute choreographed {act} on '{elem}' within '{win}'."


@registry.register(
    name="execute_choreographed_action",
    tier=1,
    description="Executes a choreographed desktop action with Bezier mouse motion, visual HUD halo, and focus verification.",
    args_schema=ExecuteChoreographedActionArgs,
    preview_fn=execute_choreographed_action_preview,
    can_remember_per_folder=False,
)
def handle_execute_choreographed_action(
    action_type: str = "CLICK",
    target_window_title: Optional[str] = None,
    target_x: Optional[int] = None,
    target_y: Optional[int] = None,
    target_element_name: Optional[str] = None,
    text_payload: Optional[str] = None,
    duration_ms: int = 300,
) -> Dict[str, Any]:
    try:
        act_enum = DesktopActionType(action_type.upper())
    except Exception:
        act_enum = DesktopActionType.CLICK

    coords = (target_x, target_y) if (target_x is not None and target_y is not None) else None
    step = DesktopActionStep(
        step_id=f"step_{int(time.time() * 1000)}",
        action_type=act_enum,
        target_window_title=target_window_title,
        target_coordinates=coords,
        target_element_name=target_element_name,
        text_payload=text_payload,
        duration_ms=duration_ms,
    )
    return desktop_choreographer.execute_step(step)


# ============================================================================
# 2. preview_target_halo (Tier 0)
# ============================================================================

class PreviewTargetHaloArgs(BaseModel):
    target_name: str = Field(..., description="Name or label of target control")
    x: int = Field(..., description="Target center X coordinate")
    y: int = Field(..., description="Target center Y coordinate")
    width: int = Field(default=60, description="Bounding width in px")
    height: int = Field(default=30, description="Bounding height in px")
    color_hex: str = Field(default="#00FFCC", description="HUD halo stroke color")


def preview_target_halo_preview(args: Dict[str, Any]) -> str:
    name = args.get("target_name", "element")
    return f"Render visual HUD target halo over '{name}'."


@registry.register(
    name="preview_target_halo",
    tier=0,
    description="Renders a visual HUD target halo bounding box over a screen element prior to interaction.",
    args_schema=PreviewTargetHaloArgs,
    preview_fn=preview_target_halo_preview,
    can_remember_per_folder=False,
)
def handle_preview_target_halo(
    target_name: str,
    x: int,
    y: int,
    width: int = 60,
    height: int = 30,
    color_hex: str = "#00FFCC",
) -> Dict[str, Any]:
    bounding_box = (max(0, x - width // 2), max(0, y - height // 2), width, height)
    halo = halo_emitter.create_halo(
        target_name=target_name,
        bounding_box=bounding_box,
        color_hex=color_hex,
    )
    return {
        "status": "success",
        "halo_id": halo.halo_id,
        "bounding_box": halo.bounding_box,
        "color_hex": halo.color_hex,
    }


# ============================================================================
# 3. generate_bezier_trajectory (Tier 0)
# ============================================================================

class GenerateBezierTrajectoryArgs(BaseModel):
    start_x: int = Field(..., description="Start X coordinate")
    start_y: int = Field(..., description="Start Y coordinate")
    target_x: int = Field(..., description="Target X coordinate")
    target_y: int = Field(..., description="Target Y coordinate")
    duration_ms: Optional[float] = Field(default=None, description="Trajectory duration in ms")


def generate_bezier_trajectory_preview(args: Dict[str, Any]) -> str:
    sx, sy = args.get("start_x", 0), args.get("start_y", 0)
    tx, ty = args.get("target_x", 0), args.get("target_y", 0)
    return f"Calculate humanized cubic Bezier trajectory from ({sx},{sy}) to ({tx},{ty})."


@registry.register(
    name="generate_bezier_trajectory",
    tier=0,
    description="Calculates humanized cubic Bezier mouse waypoints with ease-in-out velocity and micro-jitter.",
    args_schema=GenerateBezierTrajectoryArgs,
    preview_fn=generate_bezier_trajectory_preview,
    can_remember_per_folder=False,
)
def handle_generate_bezier_trajectory(
    start_x: int,
    start_y: int,
    target_x: int,
    target_y: int,
    duration_ms: Optional[float] = None,
) -> Dict[str, Any]:
    traj = trajectory_generator.generate(
        start_pos=(start_x, start_y),
        target_pos=(target_x, target_y),
        duration_ms=duration_ms,
        add_jitter=True,
    )
    return {
        "status": "success",
        "total_distance_px": traj.total_distance_px,
        "duration_ms": traj.duration_ms,
        "points_count": len(traj.points),
        "waypoints": [p.model_dump() for p in traj.points],
    }
