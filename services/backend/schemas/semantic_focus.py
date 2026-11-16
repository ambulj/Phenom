"""Pydantic schemas for Multi-App Semantic Focus & Human Takeover (Milestone 49 Phase 3).

Models:
- Window context and bounding coordinates (GUI-01).
- Pre-action semantic focus verification request and result (GUI-02).
- Low-level human takeover event detection and anti-checkout barriers (GUI-03).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class BoundingRect(BaseModel):
    """Screen coordinate bounding box."""
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)

    def contains(self, x: int, y: int) -> bool:
        """Returns True if point (x, y) is within bounds."""
        return self.left <= x <= self.right and self.top <= y <= self.bottom


class UIAElementDescriptor(BaseModel):
    """UI Automation element representation."""
    automation_id: str = Field(default="", description="AutomationId property")
    name: str = Field(default="", description="Name or label of control")
    control_type: str = Field(default="Unknown", description="UIA ControlType (Button, Edit, etc.)")
    class_name: str = Field(default="", description="Window or element class name")
    bounding_rect: Optional[BoundingRect] = Field(default=None, description="Screen coordinates bounding box")
    is_enabled: bool = Field(default=True, description="Whether control is enabled")
    is_visible: bool = Field(default=True, description="Whether control is rendered and visible")


class WindowContext(BaseModel):
    """Active desktop window snapshot."""
    hwnd: int = Field(description="Window handle integer")
    title: str = Field(description="Window title text")
    process_name: str = Field(description="Executable process name (e.g. Code.exe)")
    pid: int = Field(description="Process ID")
    bounding_rect: BoundingRect = Field(description="Window screen coordinates")
    is_minimized: bool = Field(default=False, description="Whether window is currently minimized")
    uia_root: Optional[UIAElementDescriptor] = Field(default=None, description="Root UIA element descriptor")
    timestamp: float = Field(default_factory=time.time, description="Capture timestamp")


class FocusVerificationRequest(BaseModel):
    """Pre-action semantic focus assertion request."""
    expected_title_contains: Optional[str] = Field(default=None, description="Substring expected in window title")
    expected_pid: Optional[int] = Field(default=None, description="Expected process ID")
    expected_process_name: Optional[str] = Field(default=None, description="Expected executable name")
    target_coordinates: Optional[Tuple[int, int]] = Field(default=None, description="Target (x, y) screen coordinates")
    action_type: str = Field(default="CLICK", description="CLICK, TYPE, HOVER, or DRAG")


class FocusVerificationResult(BaseModel):
    """Outcome of pre-action semantic verification."""
    is_valid: bool = Field(description="True if all focus assertions pass")
    active_window: Optional[WindowContext] = Field(default=None, description="Snapshot of observed window")
    error_reason: Optional[str] = Field(default=None, description="Explanation if verification failed")
    latency_ms: float = Field(default=0.0, description="Verification latency in milliseconds")


class TakeoverEvent(BaseModel):
    """Operator physical takeover detection event."""
    event_id: str = Field(description="Unique takeover event ID")
    initial_position: Tuple[int, int] = Field(description="(x, y) before displacement")
    detected_position: Tuple[int, int] = Field(description="(x, y) after human movement")
    displacement_px: float = Field(description="Euclidean displacement in pixels")
    detection_latency_ms: float = Field(description="Time to detect and yield in milliseconds")
    timestamp: float = Field(default_factory=time.time, description="Event timestamp")
