"""
Phenom NEURAL-NEOCORTEX Schemas
Milestone 44.0: Project NEURAL-NEOCORTEX (Phase 1)

Pydantic schemas for in-RAM screen frames, window focus events, visual diff metrics,
and Neocortex visual telemetry.
"""

from __future__ import annotations

import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ScreenFramePayload(BaseModel):
    frame_id: int = Field(..., description="Monotonically increasing frame index")
    timestamp: float = Field(default_factory=time.time, description="Capture timestamp in epoch seconds")
    width: int = Field(..., description="Frame pixel width")
    height: int = Field(..., description="Frame pixel height")
    is_diff: bool = Field(..., description="True if visual content changed past sensitivity threshold")
    diff_ratio: float = Field(..., description="Percentage of pixels changed [0.0, 1.0]")
    active_window_title: str = Field(..., description="Active foreground window title")
    process_name: str = Field(..., description="Active foreground process executable name")
    is_blinded: bool = Field(default=False, description="True if capture was blinded due to sensitive window policy")


class WindowFocusEvent(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    window_title: str
    process_name: str
    is_sensitive: bool = False
    is_terminal: bool = False


class VisualDiffMetrics(BaseModel):
    frame_latency_ms: float = Field(..., description="Frame acquisition + diff calculation latency in ms")
    diff_percentage: float = Field(..., description="Percentage of visual change detected")
    fps: float = Field(..., description="Current effective frame capture rate")
    frames_captured: int = Field(..., description="Total frames processed since activation")
    frames_dropped: int = Field(..., description="Frames dropped due to identical content")


class NeocortexTelemetry(BaseModel):
    is_active: bool
    capture_mode: str  # "HYBRID_DIFF", "CONTINUOUS", "MANUAL", "HALTED"
    fps: float
    ring_buffer_frames: int
    is_blinded: bool
    active_window: str
    process_name: str
    guardian_halted: bool
    last_frame_latency_ms: float
    total_frames_captured: int
    total_diffs_detected: int
