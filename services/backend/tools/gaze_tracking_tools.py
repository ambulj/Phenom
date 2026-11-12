"""Attentive Gaze & Engagement Tracking Tools for Phenom (Milestone 33 Phase 1).

Registers 4 specialized tools in ToolRegistry:
1. get_gaze_engagement_telemetry (Tier 0)
2. simulate_gaze_observation (Tier 0)
3. configure_gaze_thresholds (Tier 1)
4. reset_gaze_tracker_state (Tier 0)
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.vision.gaze_tracker import gaze_tracker


# ==========================================
# 1. Get Gaze Engagement Telemetry (Tier 0)
# ==========================================

class GetGazeTelemetryArgs(BaseModel):
    pass


def preview_get_gaze_telemetry(args: Dict[str, Any]) -> str:
    return "Query current attentive gaze and user engagement telemetry"


@registry.register(
    name="get_gaze_engagement_telemetry",
    tier=0,
    description="Returns read-only gaze vector, eye contact status, and touchless engagement state (Tier 0 read-only).",
    args_schema=GetGazeTelemetryArgs,
    preview_fn=preview_get_gaze_telemetry,
    can_remember_per_folder=False,
)
def handle_get_gaze_engagement_telemetry() -> Dict[str, Any]:
    return gaze_tracker.get_telemetry()


# ==========================================
# 2. Simulate Gaze Observation (Tier 0)
# ==========================================

class SimulateGazeObservationArgs(BaseModel):
    yaw: float = Field(..., description="Horizontal gaze angle in degrees (-90 to +90).")
    pitch: float = Field(..., description="Vertical gaze angle in degrees (-90 to +90).")
    roll: float = Field(0.0, description="Head tilt in degrees.")
    confidence: float = Field(0.95, description="Confidence score (0.0 to 1.0).")


def preview_simulate_gaze_observation(args: Dict[str, Any]) -> str:
    y = args.get("yaw", 0.0)
    p = args.get("pitch", 0.0)
    return f"Simulate gaze observation (yaw={y}°, pitch={p}°)"


@registry.register(
    name="simulate_gaze_observation",
    tier=0,
    description="Feeds a simulated on-device gaze observation into the engagement state machine (Tier 0 diagnostic).",
    args_schema=SimulateGazeObservationArgs,
    preview_fn=preview_simulate_gaze_observation,
    can_remember_per_folder=False,
)
def handle_simulate_gaze_observation(
    yaw: float,
    pitch: float,
    roll: float = 0.0,
    confidence: float = 0.95,
) -> Dict[str, Any]:
    telemetry = gaze_tracker.update_gaze(yaw=yaw, pitch=pitch, roll=roll, confidence=confidence)
    return telemetry.model_dump()


# ==========================================
# 3. Configure Gaze Thresholds (Tier 1)
# ==========================================

class ConfigureGazeThresholdsArgs(BaseModel):
    yaw_threshold_deg: Optional[float] = Field(None, description="Max yaw angle deviation for direct eye contact.")
    pitch_threshold_deg: Optional[float] = Field(None, description="Max pitch angle deviation for direct eye contact.")
    sustained_trigger_ms: Optional[float] = Field(None, description="Duration in ms of eye contact before triggering touchless listening.")
    look_away_pause_ms: Optional[float] = Field(None, description="Duration in ms of looking away before pausing speech.")


def preview_configure_gaze_thresholds(args: Dict[str, Any]) -> str:
    return "Configure attentive gaze engagement and pause thresholds"


@registry.register(
    name="configure_gaze_thresholds",
    tier=1,
    description="Updates gaze angle tolerances and touchless listening trigger thresholds (Tier 1 configuration).",
    args_schema=ConfigureGazeThresholdsArgs,
    preview_fn=preview_configure_gaze_thresholds,
    can_remember_per_folder=False,
)
def handle_configure_gaze_thresholds(
    yaw_threshold_deg: Optional[float] = None,
    pitch_threshold_deg: Optional[float] = None,
    sustained_trigger_ms: Optional[float] = None,
    look_away_pause_ms: Optional[float] = None,
) -> Dict[str, Any]:
    if yaw_threshold_deg is not None:
        gaze_tracker.yaw_threshold_deg = yaw_threshold_deg
    if pitch_threshold_deg is not None:
        gaze_tracker.pitch_threshold_deg = pitch_threshold_deg
    if sustained_trigger_ms is not None:
        gaze_tracker.sustained_trigger_ms = sustained_trigger_ms
    if look_away_pause_ms is not None:
        gaze_tracker.look_away_pause_ms = look_away_pause_ms

    return {
        "status": "CONFIGURED",
        "yaw_threshold_deg": gaze_tracker.yaw_threshold_deg,
        "pitch_threshold_deg": gaze_tracker.pitch_threshold_deg,
        "sustained_trigger_ms": gaze_tracker.sustained_trigger_ms,
        "look_away_pause_ms": gaze_tracker.look_away_pause_ms,
    }


# ==========================================
# 4. Reset Gaze Tracker State (Tier 0)
# ==========================================

class ResetGazeTrackerStateArgs(BaseModel):
    pass


def preview_reset_gaze_tracker_state(args: Dict[str, Any]) -> str:
    return "Reset gaze engagement state to DISENGAGED"


@registry.register(
    name="reset_gaze_tracker_state",
    tier=0,
    description="Resets the user gaze engagement state and timers (Tier 0 safe reset).",
    args_schema=ResetGazeTrackerStateArgs,
    preview_fn=preview_reset_gaze_tracker_state,
    can_remember_per_folder=False,
)
def handle_reset_gaze_tracker_state() -> Dict[str, Any]:
    return gaze_tracker.reset_state()
