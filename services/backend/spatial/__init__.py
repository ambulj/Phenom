"""Spatial package for Phenom (Milestone 12.0)."""

from services.backend.spatial.focus_tracker import FocusTrackingEngine
from services.backend.spatial.canvas_manager import SpatialCanvasManager, spatial_canvas_manager
from services.backend.spatial.cursor_telemetry_tracker import (
    CursorTelemetryTracker,
    cursor_telemetry_tracker,
    CursorSpatialContext,
)
from services.backend.spatial.spatial_intent_resolver import (
    SpatialIntentResolver,
    spatial_intent_resolver,
    SpatialResolvedIntent,
)

__all__ = [
    "FocusTrackingEngine",
    "SpatialCanvasManager",
    "spatial_canvas_manager",
    "CursorTelemetryTracker",
    "cursor_telemetry_tracker",
    "CursorSpatialContext",
    "SpatialIntentResolver",
    "spatial_intent_resolver",
    "SpatialResolvedIntent",
]
