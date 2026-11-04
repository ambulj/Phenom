"""Milestone 13 Phase 2: Multi-Modal Holographic Workspace & Spatial 3D Volumetric Canvas.
Exports the VolumetricCanvasManager and VisionGestureTracker singletons and classes.
"""

from services.backend.volumetric.gesture_tracker import (
    VisionGestureTracker,
    vision_gesture_tracker,
)
from services.backend.volumetric.canvas_manager import (
    VolumetricCanvasManager,
    volumetric_canvas_manager,
)

__all__ = [
    "VisionGestureTracker",
    "vision_gesture_tracker",
    "VolumetricCanvasManager",
    "volumetric_canvas_manager",
]
