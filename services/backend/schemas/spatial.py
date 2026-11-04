"""
Transparent Holographic Spatial Canvas & Ghost Annotations Schemas (OVR-01, SAF-01, SAF-02).
Defines Pydantic v2 models for:
- Window bounds and foreground active window targets
- Floating ghost annotations anchored to active windows or screen coordinates
- Spatial overlay state, direct composition configurations, and click-through flags
- Safety tool argument schemas for spatial canvas manipulation
"""

import time
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class AnchorPoint(str, Enum):
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    CENTER = "center"
    CUSTOM = "custom"


class AnnotationStylePreset(str, Enum):
    CYBER_CYAN = "cyber_cyan"
    NEON_AMBER = "neon_amber"
    MATRIX_GREEN = "matrix_green"
    CRIMSON_ALERT = "crimson_alert"


class WindowRect(BaseModel):
    """Screen bounding coordinates for a desktop window."""
    model_config = ConfigDict(use_enum_values=True)

    left: int = Field(default=0, description="X coordinate of left edge")
    top: int = Field(default=0, description="Y coordinate of top edge")
    right: int = Field(default=0, description="X coordinate of right edge")
    bottom: int = Field(default=0, description="Y coordinate of bottom edge")
    width: int = Field(default=0, description="Window width in pixels")
    height: int = Field(default=0, description="Window height in pixels")


class ActiveWindowTarget(BaseModel):
    """Metadata describing the currently active or targeted foreground window."""
    model_config = ConfigDict(use_enum_values=True)

    hwnd: int = Field(default=0, description="Win32 Window Handle")
    title: str = Field(default="", description="Sanitized window title")
    process_name: str = Field(default="", description="Executable name (e.g. code.exe, chrome.exe)")
    pid: int = Field(default=0, description="Process ID")
    bounds: WindowRect = Field(default_factory=WindowRect, description="Current window rect on screen")
    is_minimized: bool = Field(default=False, description="Whether target window is minimized")
    is_focused: bool = Field(default=True, description="Whether target window currently has foreground focus")
    captured_at: float = Field(default_factory=time.time, description="Timestamp window target was inspected")


class GhostAnnotation(BaseModel):
    """A floating holographic annotation anchored to a target window or screen position."""
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(..., description="Unique annotation identifier")
    title: str = Field(..., description="Short annotation header")
    content: str = Field(..., description="Annotation body text or contextual prompt")
    target_window_title: Optional[str] = Field(default=None, description="Title of target window to track/anchor to")
    anchor_point: AnchorPoint = Field(default=AnchorPoint.TOP_RIGHT, description="Anchor point on target window")
    offset_x: int = Field(default=20, description="Horizontal pixel offset from anchor point")
    offset_y: int = Field(default=20, description="Vertical pixel offset from anchor point")
    screen_x: int = Field(default=0, description="Computed absolute screen X position")
    screen_y: int = Field(default=0, description="Computed absolute screen Y position")
    opacity: float = Field(default=0.92, ge=0.1, le=1.0, description="Visual opacity of the ghost annotation card")
    click_through: bool = Field(default=True, description="Whether mouse events pass through to windows underneath")
    created_at: float = Field(default_factory=time.time, description="Creation epoch timestamp")
    ttl_seconds: Optional[float] = Field(default=300.0, description="Time-to-live before auto-dismissal; None for indefinite")
    is_dismissed: bool = Field(default=False, description="Whether annotation has been dismissed")
    style_preset: AnnotationStylePreset = Field(default=AnnotationStylePreset.CYBER_CYAN, description="Holographic neon theme preset")


class SpatialOverlayState(BaseModel):
    """Comprehensive state of the transparent holographic spatial overlay."""
    model_config = ConfigDict(use_enum_values=True)

    is_active: bool = Field(default=False, description="Whether holographic overlay canvas is displayed")
    click_through: bool = Field(default=True, description="Global click-through state (WS_EX_TRANSPARENT)")
    direct_composition_enabled: bool = Field(default=True, description="DirectComposition transparent rendering mode")
    active_window: Optional[ActiveWindowTarget] = Field(default=None, description="Currently detected foreground window")
    annotations: List[GhostAnnotation] = Field(default_factory=list, description="Currently active ghost annotations")
    total_annotations_created: int = Field(default=0, description="Lifetime count of annotations created")
    last_updated: float = Field(default_factory=time.time, description="Last state change epoch timestamp")


# ==========================================
# Tool Argument Schemas (SAF-01)
# ==========================================

class SpatialGetFocusArgs(BaseModel):
    """Arguments for querying current foreground focus and active spatial overlay state (Tier 0)."""
    model_config = ConfigDict(extra="forbid")


class SpatialShowOverlayArgs(BaseModel):
    """Arguments for showing/activating the transparent holographic spatial canvas (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    click_through: bool = Field(default=True, description="Enable click-through pass-through mode")
    direct_comp: bool = Field(default=True, description="Enable DirectComposition visual transparency")


class SpatialHideOverlayArgs(BaseModel):
    """Arguments for hiding the transparent holographic spatial canvas (Tier 1)."""
    model_config = ConfigDict(extra="forbid")


class SpatialAddAnnotationArgs(BaseModel):
    """Arguments for adding a new floating ghost annotation (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=120, description="Header title for the ghost annotation")
    content: str = Field(..., min_length=1, max_length=1000, description="Annotation content or suggestion")
    target_window: Optional[str] = Field(default=None, description="Target window title match (None to anchor to active foreground)")
    anchor: str = Field(default="top-right", description="Anchor point: top-left, top-right, bottom-left, bottom-right, center, custom")
    offset_x: int = Field(default=20, description="X pixel offset from anchor")
    offset_y: int = Field(default=20, description="Y pixel offset from anchor")
    ttl_seconds: Optional[float] = Field(default=300.0, description="Time to live in seconds (None for indefinite)")
    style_preset: str = Field(default="cyber_cyan", description="Style theme: cyber_cyan, neon_amber, matrix_green, crimson_alert")
    click_through: bool = Field(default=True, description="Whether clicks pass through this annotation")


class SpatialDismissAnnotationArgs(BaseModel):
    """Arguments for dismissing a ghost annotation by ID (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    annotation_id: str = Field(..., description="Unique ID of the annotation to dismiss")


class SpatialToggleClickThroughArgs(BaseModel):
    """Arguments for toggling click-through pass-through behavior on the overlay (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(..., description="True to enable click-through, False to allow interactive HUD clicking")
