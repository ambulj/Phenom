"""Spatial package for Phenom (Milestone 12.0)."""

from services.backend.spatial.focus_tracker import FocusTrackingEngine
from services.backend.spatial.canvas_manager import SpatialCanvasManager, spatial_canvas_manager

__all__ = ["FocusTrackingEngine", "SpatialCanvasManager", "spatial_canvas_manager"]
