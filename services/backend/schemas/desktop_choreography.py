"""Pydantic schemas for Cross-Application Visual Desktop Choreography (Milestone 49 Phase 4).

Models:
- Cubic Bezier trajectories, control points, and micro-jitter (CHOREO-01).
- Cross-application desktop action steps and choreography plans (CHOREO-02).
- Visual HUD target halos and bounding box highlights (CHOREO-03).
"""

from __future__ import annotations

from enum import Enum
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class DesktopActionType(str, Enum):
    MOVE = "MOVE"
    CLICK = "CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    RIGHT_CLICK = "RIGHT_CLICK"
    TYPE_TEXT = "TYPE_TEXT"
    KEY_COMBO = "KEY_COMBO"
    SCROLL = "SCROLL"
    WAIT = "WAIT"


class BezierPoint(BaseModel):
    """A sampled coordinate along a humanized Bezier trajectory."""
    x: float = Field(description="X screen coordinate")
    y: float = Field(description="Y screen coordinate")
    t: float = Field(description="Normalized trajectory progress [0.0, 1.0]")
    timestamp_ms: float = Field(default=0.0, description="Elapsed time from trajectory onset in ms")


class BezierTrajectory(BaseModel):
    """Calculated smooth humanized cubic Bezier curve."""
    start_pos: Tuple[int, int] = Field(description="(x, y) start coordinate")
    target_pos: Tuple[int, int] = Field(description="(x, y) target coordinate")
    duration_ms: float = Field(description="Calculated or requested duration in ms")
    total_distance_px: float = Field(description="Euclidean distance in pixels")
    points: List[BezierPoint] = Field(default_factory=list, description="Ordered sampled trajectory waypoints")
    has_micro_jitter: bool = Field(default=True, description="Whether physiological tremor micro-jitter was added")


class TargetHaloSpec(BaseModel):
    """Visual bounding halo highlighted on CyberHUD overlay prior to interaction."""
    halo_id: str = Field(description="Unique halo identifier")
    target_name: str = Field(description="Label of target control")
    bounding_box: Tuple[int, int, int, int] = Field(description="(left, top, width, height) in screen pixels")
    color_hex: str = Field(default="#00FFCC", description="Hex stroke color for HUD bounding halo")
    duration_ms: int = Field(default=300, description="Halo display duration before click in ms")
    action_type: str = Field(default="CLICK", description="Associated action label")
    timestamp: float = Field(default_factory=time.time, description="Creation timestamp")


class DesktopActionStep(BaseModel):
    """A single atomic action in a choreographed multi-step desktop workflow."""
    step_id: str = Field(description="Unique step identifier")
    action_type: DesktopActionType = Field(description="Type of action (CLICK, TYPE, MOVE, etc.)")
    target_window_title: Optional[str] = Field(default=None, description="Expected window title substring for focus guard")
    target_coordinates: Optional[Tuple[int, int]] = Field(default=None, description="Target screen coordinates (x, y)")
    target_element_name: Optional[str] = Field(default=None, description="Target UIA or vision element label")
    text_payload: Optional[str] = Field(default=None, description="Text to type if action_type is TYPE_TEXT")
    key_combo: Optional[List[str]] = Field(default=None, description="Key combinations if action_type is KEY_COMBO")
    duration_ms: int = Field(default=300, description="Step execution duration in ms")
    halo_spec: Optional[TargetHaloSpec] = Field(default=None, description="Visual target halo configuration")


class ChoreographyPlan(BaseModel):
    """An ordered workflow plan orchestrating desktop actions across applications."""
    plan_id: str = Field(description="Unique choreography plan ID")
    title: str = Field(description="Plan descriptive title")
    steps: List[DesktopActionStep] = Field(default_factory=list, description="Ordered sequence of action steps")
    created_at: float = Field(default_factory=time.time, description="Plan creation timestamp")


class ChoreographyResult(BaseModel):
    """Outcome report of choreographed desktop action execution."""
    plan_id: str = Field(description="Associated plan ID")
    status: str = Field(description="SUCCESS, ABORTED_TAKEOVER, ABORTED_FOCUS_MISMATCH, ABORTED_CHECKOUT, or FAILED")
    completed_steps: int = Field(default=0, description="Number of successfully executed steps")
    total_steps: int = Field(default=0, description="Total steps in plan")
    error_message: Optional[str] = Field(default=None, description="Error or abort description")
    total_duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
