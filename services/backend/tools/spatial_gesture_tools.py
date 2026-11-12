"""
Phenom Spatial Gesture Safety Tools
Provides ToolRegistry integration for multi-modal spatial hand gesture tracking,
dynamic action binding, and sub-15ms Guardian emergency safety halt triggers.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.vision.spatial_gesture_detector import (
    spatial_gesture_detector,
    GestureType,
    Rule8ViolationError,
    enforce_anti_checkout,
)


def _generate_synthetic_landmarks(gesture_name: str) -> List[Dict[str, float]]:
    """Helper to synthesize canonical 21-point hand landmark skeletons."""
    pts = [{"x": 0.5, "y": 0.7, "z": 0.0} for _ in range(21)]
    pts[0] = {"x": 0.5, "y": 0.8, "z": 0.0}
    pts[5] = {"x": 0.45, "y": 0.6, "z": 0.0}
    pts[9] = {"x": 0.50, "y": 0.58, "z": 0.0}
    pts[13] = {"x": 0.55, "y": 0.6, "z": 0.0}
    pts[17] = {"x": 0.60, "y": 0.65, "z": 0.0}

    gn = gesture_name.upper()
    if gn in ("OPEN_PALM", "RAISED_PALM"):
        pts[4] = {"x": 0.35, "y": 0.45, "z": 0.0}
        pts[3] = {"x": 0.38, "y": 0.52, "z": 0.0}
        pts[8] = {"x": 0.45, "y": 0.35, "z": 0.0}
        pts[6] = {"x": 0.45, "y": 0.50, "z": 0.0}
        pts[12] = {"x": 0.50, "y": 0.32, "z": 0.0}
        pts[10] = {"x": 0.50, "y": 0.48, "z": 0.0}
        pts[16] = {"x": 0.55, "y": 0.35, "z": 0.0}
        pts[14] = {"x": 0.55, "y": 0.50, "z": 0.0}
        pts[20] = {"x": 0.60, "y": 0.40, "z": 0.0}
        pts[18] = {"x": 0.60, "y": 0.55, "z": 0.0}
    elif gn == "INDEX_POINT":
        pts[4] = {"x": 0.45, "y": 0.65, "z": 0.0}
        pts[3] = {"x": 0.42, "y": 0.60, "z": 0.0}
        pts[8] = {"x": 0.45, "y": 0.30, "z": 0.0}
        pts[6] = {"x": 0.45, "y": 0.48, "z": 0.0}
        pts[12] = {"x": 0.50, "y": 0.65, "z": 0.0}
        pts[10] = {"x": 0.50, "y": 0.55, "z": 0.0}
        pts[16] = {"x": 0.55, "y": 0.65, "z": 0.0}
        pts[14] = {"x": 0.55, "y": 0.55, "z": 0.0}
        pts[20] = {"x": 0.60, "y": 0.68, "z": 0.0}
        pts[18] = {"x": 0.60, "y": 0.58, "z": 0.0}
    elif gn == "THUMBS_UP":
        pts[4] = {"x": 0.35, "y": 0.30, "z": 0.0}
        pts[3] = {"x": 0.38, "y": 0.45, "z": 0.0}
        pts[8] = {"x": 0.48, "y": 0.65, "z": 0.0}
        pts[6] = {"x": 0.46, "y": 0.58, "z": 0.0}
        pts[12] = {"x": 0.52, "y": 0.65, "z": 0.0}
        pts[10] = {"x": 0.50, "y": 0.58, "z": 0.0}
        pts[16] = {"x": 0.55, "y": 0.65, "z": 0.0}
        pts[14] = {"x": 0.53, "y": 0.58, "z": 0.0}
        pts[20] = {"x": 0.58, "y": 0.65, "z": 0.0}
        pts[18] = {"x": 0.56, "y": 0.58, "z": 0.0}
    return pts


# ==========================================
# 1. Get Spatial Gesture Telemetry (Tier 0)
# ==========================================

class GetSpatialGestureTelemetryArgs(BaseModel):
    pass


def preview_get_spatial_gesture_telemetry(args: Dict[str, Any]) -> str:
    return "Query real-time spatial hand gesture telemetry, pointing target, and emergency halt status."


@registry.register(
    name="get_spatial_gesture_telemetry",
    tier=0,
    description="Query real-time spatial hand gesture telemetry, 21-point landmarks, pointing target, and emergency halt state (Tier 0 read-only).",
    args_schema=GetSpatialGestureTelemetryArgs,
    preview_fn=preview_get_spatial_gesture_telemetry,
    can_remember_per_folder=False,
)
def handle_get_spatial_gesture_telemetry() -> Dict[str, Any]:
    telemetry = spatial_gesture_detector.get_telemetry()
    return {
        "gesture": telemetry.gesture.value,
        "confidence": round(telemetry.confidence, 3),
        "palm_normal": [round(c, 3) for c in telemetry.palm_normal],
        "pointing_target": telemetry.pointing_target,
        "emergency_halt_triggered": telemetry.emergency_halt_triggered,
        "mapped_action": telemetry.mapped_action,
        "is_halted": spatial_gesture_detector.is_halted,
        "timestamp": telemetry.timestamp,
    }


# ==========================================
# 2. Simulate Hand Gesture Observation (Tier 0)
# ==========================================

class SimulateHandGestureObservationArgs(BaseModel):
    gesture_name: Optional[str] = Field(
        None,
        description="Optional shorthand gesture template name: 'OPEN_PALM', 'RAISED_PALM', 'INDEX_POINT', 'SWIPE_LEFT', 'SWIPE_RIGHT', 'THUMBS_UP', or 'NONE'",
    )
    landmarks: Optional[List[Dict[str, float]]] = Field(
        None,
        description="List of 21 3D hand landmark coordinates {'x': float, 'y': float, 'z': float}",
    )
    confidence: float = Field(
        0.90,
        ge=0.0,
        le=1.0,
        description="Confidence score for the gesture observation",
    )


def preview_simulate_hand_gesture_observation(args: Dict[str, Any]) -> str:
    g = args.get("gesture_name", "custom_landmarks")
    c = args.get("confidence", 0.9)
    return f"Simulate hand gesture observation: gesture={g} (confidence={c})."


@registry.register(
    name="simulate_hand_gesture_observation",
    tier=0,
    description="Ingest synthetic or camera hand observation with 21 normalized landmarks for evaluation without disk persistence (Tier 0 diagnostic).",
    args_schema=SimulateHandGestureObservationArgs,
    preview_fn=preview_simulate_hand_gesture_observation,
    can_remember_per_folder=False,
)
def handle_simulate_hand_gesture_observation(
    gesture_name: Optional[str] = None,
    landmarks: Optional[List[Dict[str, float]]] = None,
    confidence: float = 0.90,
) -> Dict[str, Any]:
    if gesture_name:
        enforce_anti_checkout(gesture_name)

    if not landmarks and gesture_name:
        landmarks = _generate_synthetic_landmarks(gesture_name)
    elif not landmarks:
        landmarks = [{"x": 0.0, "y": 0.0, "z": 0.0} for _ in range(21)]

    telemetry = spatial_gesture_detector.ingest_hand_landmarks(
        landmarks=landmarks,
        confidence=confidence,
    )
    return {
        "status": "INGESTED",
        "gesture": telemetry.gesture.value,
        "confidence": round(telemetry.confidence, 3),
        "pointing_target": telemetry.pointing_target,
        "emergency_halt_triggered": telemetry.emergency_halt_triggered,
        "mapped_action": telemetry.mapped_action,
    }


# ==========================================
# 3. Map Spatial Gesture Action (Tier 1)
# ==========================================

class MapSpatialGestureActionArgs(BaseModel):
    gesture: str = Field(
        ...,
        description="Target gesture to bind: 'SWIPE_LEFT', 'SWIPE_RIGHT', 'THUMBS_UP', 'INDEX_POINT', 'OPEN_PALM'",
    )
    action_name: str = Field(
        ...,
        description="Named system action to trigger upon gesture recognition (e.g. 'switch_window_left')",
    )


def preview_map_spatial_gesture_action(args: Dict[str, Any]) -> str:
    g = args.get("gesture", "")
    a = args.get("action_name", "")
    return f"Map spatial gesture '{g}' to action '{a}'."


@registry.register(
    name="map_spatial_gesture_action",
    tier=1,
    description="Binds a recognized gesture (SWIPE_LEFT, SWIPE_RIGHT, THUMBS_UP) to a named system action with Rule 8 anti-checkout enforcement (Tier 1 configuration).",
    args_schema=MapSpatialGestureActionArgs,
    preview_fn=preview_map_spatial_gesture_action,
    can_remember_per_folder=False,
)
def handle_map_spatial_gesture_action(gesture: str, action_name: str) -> Dict[str, Any]:
    enforce_anti_checkout(action_name)
    enforce_anti_checkout(gesture)

    try:
        gt = GestureType(gesture.upper())
    except ValueError:
        return {"status": "ERROR", "message": f"Invalid gesture type: {gesture}"}

    spatial_gesture_detector.map_action(gt, action_name)
    return {
        "status": "MAPPED",
        "gesture": gt.value,
        "action_name": action_name,
        "current_mappings": spatial_gesture_detector.get_action_mappings(),
    }


# ==========================================
# 4. Trigger Gesture Safety Halt (Tier 0)
# ==========================================

class TriggerGestureSafetyHaltArgs(BaseModel):
    reason: str = Field(
        "Raised open-palm emergency stop",
        description="Reason description for the gesture-initiated emergency stop",
    )


def preview_trigger_gesture_safety_halt(args: Dict[str, Any]) -> str:
    r = args.get("reason", "Raised open-palm emergency stop")
    return f"Trigger emergency Guardian safety halt from gesture: {r}."


@registry.register(
    name="trigger_gesture_safety_halt",
    tier=0,
    description="Immediately triggers Guardian emergency stop halt on behalf of raised-palm gesture detection, returning halt latency (< 15ms) (Tier 0 safety override).",
    args_schema=TriggerGestureSafetyHaltArgs,
    preview_fn=preview_trigger_gesture_safety_halt,
    can_remember_per_folder=False,
)
def handle_trigger_gesture_safety_halt(reason: str = "Raised open-palm emergency stop") -> Dict[str, Any]:
    enforce_anti_checkout(reason)
    elapsed_ms = spatial_gesture_detector.trigger_emergency_halt(reason=reason)
    return {
        "status": "HALTED",
        "reason": reason,
        "elapsed_ms": round(elapsed_ms, 3),
        "sla_pass": elapsed_ms < 15.0,
    }
