"""
Volumetric Spatial 3D Canvas & Vision Gesture Schemas (VOL-01, SAF-01, SAF-02).
Defines Pydantic v2 models for:
- 3D Cartesian vectors and depth layers
- Volumetric nodes with spatial positioning and physics velocities
- Touchless vision gesture classifications (Pinch, Point, Palm Dismiss, Swipes)
- Volumetric workspace scene graph state and projection geometries
- Safety tool argument schemas for spatial canvas manipulation
"""

import time
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class ProjectionGeometry(str, Enum):
    CYLINDRICAL = "cylindrical"  # Arc wrap around user
    SPHERICAL = "spherical"      # Full spherical surround
    PLANAR = "planar"            # Multi-monitor depth layers


class GestureType(str, Enum):
    IDLE = "IDLE"
    POINT = "POINT"
    PINCH = "PINCH"
    PALM_DISMISS = "PALM_DISMISS"
    SWIPE_LEFT = "SWIPE_LEFT"
    SWIPE_RIGHT = "SWIPE_RIGHT"
    SWIPE_UP = "SWIPE_UP"
    SWIPE_DOWN = "SWIPE_DOWN"


class Vector3D(BaseModel):
    """3D coordinates in meters or normalized spatial projection space."""
    model_config = ConfigDict(use_enum_values=True)

    x: float = Field(default=0.0, description="X coordinate (horizontal: left/right)")
    y: float = Field(default=0.0, description="Y coordinate (vertical: up/down)")
    z: float = Field(default=0.0, description="Z coordinate (depth: near/far)")


class VolumetricNode(BaseModel):
    """A 3D spatial entity card or interactive HUD widget."""
    model_config = ConfigDict(use_enum_values=True)

    node_id: str = Field(..., description="Unique volumetric node identifier")
    label: str = Field(..., description="Readable label or card title")
    position: Vector3D = Field(default_factory=Vector3D, description="Spatial 3D position")
    velocity: Vector3D = Field(default_factory=Vector3D, description="Optional spatial physics velocity")
    color_hex: str = Field(default="#00f0ff", description="Neon glow tint")
    radius: float = Field(default=0.15, ge=0.01, le=2.0, description="Interactive hit radius")
    is_pinned: bool = Field(default=False, description="Whether node is anchored in world space")
    depth_layer: int = Field(default=1, ge=0, le=10, description="Z-index depth projection layer")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual payload or tool link")
    created_at: float = Field(default_factory=time.time, description="Creation epoch timestamp")


class VisionGesturePayload(BaseModel):
    """Real-time touchless vision gesture extracted from camera landmarks."""
    model_config = ConfigDict(use_enum_values=True)

    gesture_id: str = Field(..., description="Unique gesture event identifier")
    gesture_type: GestureType = Field(default=GestureType.IDLE, description="Classified gesture")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Classification confidence")
    hand_position: Vector3D = Field(default_factory=Vector3D, description="Wrist or palm center 3D position")
    pinch_distance: Optional[float] = Field(default=None, description="Normalized distance between thumb and index tip")
    timestamp: float = Field(default_factory=time.time, description="Detection epoch timestamp")


class VolumetricWorkspaceState(BaseModel):
    """Comprehensive state of the 3D volumetric spatial workspace."""
    model_config = ConfigDict(use_enum_values=True)

    is_active: bool = Field(default=False, description="Whether volumetric 3D workspace is rendered")
    projection_mode: ProjectionGeometry = Field(default=ProjectionGeometry.CYLINDRICAL, description="Active 3D projection model")
    total_nodes: int = Field(default=0, description="Active node count")
    nodes: List[VolumetricNode] = Field(default_factory=list, description="Currently rendered 3D spatial nodes")
    active_gesture: Optional[VisionGesturePayload] = Field(default=None, description="Most recent classified gesture")
    multi_monitor_enabled: bool = Field(default=True, description="Multi-monitor spatial span enabled")
    depth_buffer_enabled: bool = Field(default=True, description="Z-buffer occlusion enabled")
    selected_node_id: Optional[str] = Field(default=None, description="Currently raycast-targeted node")
    last_updated: float = Field(default_factory=time.time, description="Last update epoch timestamp")


# ==========================================
# Tool Argument Schemas (SAF-01)
# ==========================================

class VolumetricGetWorkspaceStatusArgs(BaseModel):
    """Arguments for querying volumetric workspace status and 3D nodes (Tier 0)."""
    model_config = ConfigDict(extra="forbid")


class VolumetricSetProjectionModeArgs(BaseModel):
    """Arguments for configuring 3D projection geometry (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    mode: str = Field(..., description="Projection mode: cylindrical, spherical, or planar")


class VolumetricSpawnNodeArgs(BaseModel):
    """Arguments for spawning a 3D spatial node or card (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., min_length=1, max_length=100, description="Node title or card label")
    x: float = Field(default=0.0, description="X coordinate (-5.0 to 5.0 meters)")
    y: float = Field(default=0.0, description="Y coordinate (-5.0 to 5.0 meters)")
    z: float = Field(default=1.5, description="Z depth coordinate (0.2 to 10.0 meters)")
    color_hex: str = Field(default="#00f0ff", description="Hex color accent (#00f0ff, #00ffcc, #ffb800, #ff3366)")
    depth_layer: int = Field(default=1, ge=0, le=10, description="Depth layer index")
    is_pinned: bool = Field(default=False, description="Pin node in place")


class VolumetricClearCanvasArgs(BaseModel):
    """Arguments for clearing all spatial nodes from the 3D canvas (Tier 1)."""
    model_config = ConfigDict(extra="forbid")


class VolumetricIngestGestureArgs(BaseModel):
    """Arguments for programmatically or sensor-injecting a hand vision gesture (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    gesture_type: str = Field(..., description="Gesture: PINCH, POINT, PALM_DISMISS, SWIPE_LEFT, SWIPE_RIGHT, SWIPE_UP, SWIPE_DOWN, IDLE")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Detection confidence score")
    x: float = Field(default=0.0, description="Hand X coordinate")
    y: float = Field(default=0.0, description="Hand Y coordinate")
    z: float = Field(default=1.0, description="Hand Z depth")
    pinch_distance: Optional[float] = Field(default=None, description="Pinch distance between thumb and index")
