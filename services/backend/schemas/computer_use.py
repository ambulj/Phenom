"""Pydantic schemas for Phenom Computer-Use and Synthetic Input Execution."""

from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field


class Point2D(BaseModel):
    """2D screen coordinate."""
    x: int = Field(..., ge=0, description="X pixel coordinate")
    y: int = Field(..., ge=0, description="Y pixel coordinate")


class ClickType(str, Enum):
    """Types of mouse clicks."""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"
    DOUBLE = "double"
    TRIPLE = "triple"


class MouseButton(str, Enum):
    """Mouse buttons."""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class ClickAction(BaseModel):
    """Mouse click action at coordinate."""
    action_type: Literal["click"] = "click"
    target: Point2D
    click_type: ClickType = ClickType.LEFT
    button_down_duration_ms: float = Field(50.0, ge=1.0, le=2000.0)
    pre_delay_ms: float = Field(20.0, ge=0.0, le=5000.0)
    smooth_move: bool = True


class MoveAction(BaseModel):
    """Smooth mouse move without clicking."""
    action_type: Literal["move"] = "move"
    target: Point2D
    duration_ms: float = Field(200.0, ge=10.0, le=5000.0)


class DragAction(BaseModel):
    """Mouse drag-and-drop action."""
    action_type: Literal["drag"] = "drag"
    start: Point2D
    end: Point2D
    button: MouseButton = MouseButton.LEFT
    duration_ms: float = Field(350.0, ge=50.0, le=10000.0)


class TypeAction(BaseModel):
    """Keystroke typing action."""
    action_type: Literal["type"] = "type"
    text: str
    typing_speed_wpm: float = Field(120.0, ge=10.0, le=400.0)
    randomize_delay: bool = True
    press_enter: bool = False
    focus_target: Optional[Point2D] = None


class HotKeyAction(BaseModel):
    """Keyboard hotkey combination (e.g. ['ctrl', 'shift', 'p'])."""
    action_type: Literal["hotkey"] = "hotkey"
    keys: List[str]
    hold_duration_ms: float = Field(50.0, ge=10.0, le=1000.0)


class ScrollAction(BaseModel):
    """Mouse scroll action."""
    action_type: Literal["scroll"] = "scroll"
    clicks: int = Field(..., description="Number of wheel ticks; positive=up, negative=down")
    target: Optional[Point2D] = None


ActionItem = Union[ClickAction, MoveAction, DragAction, TypeAction, HotKeyAction, ScrollAction]


class ActionSequencePayload(BaseModel):
    """Sequential desktop actions payload."""
    actions: List[ActionItem]
    target_window_title: Optional[str] = None
    target_window_process: Optional[str] = None
    speed_multiplier: float = Field(1.0, ge=0.1, le=5.0)
    abort_on_guardian: bool = True


class TrajectoryPoint(BaseModel):
    """A point along a generated Bezier path."""
    x: int
    y: int
    timestamp_ms: float


class BezierPath(BaseModel):
    """Generated Bezier path."""
    start: Point2D
    end: Point2D
    points: List[TrajectoryPoint]
    total_duration_ms: float


class ExecutionResult(BaseModel):
    """Result of desktop action execution."""
    success: bool
    executed_actions: int
    total_actions: int
    duration_ms: float
    error: Optional[str] = None
    guardian_halted: bool = False
    final_cursor_position: Optional[Point2D] = None
