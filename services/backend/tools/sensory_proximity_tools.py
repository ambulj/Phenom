"""
Phenom Sensory Proximity Tools
ToolRegistry integration for local metric distance estimation, adaptive acoustic scaling,
and optical camera privacy shutter controls.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.ambient.sensory_proximity_manager import (
    sensory_proximity_manager,
    enforce_anti_checkout,
    Rule8ViolationError,
)


# ==========================================
# 1. Get Sensory Proximity Telemetry (Tier 0)
# ==========================================

class GetSensoryProximityTelemetryArgs(BaseModel):
    pass


def preview_get_sensory_proximity_telemetry(args: Dict[str, Any]) -> str:
    return "Query real-time metric user proximity, acoustic volume scaling, and privacy shutter state."


@registry.register(
    name="get_sensory_proximity_telemetry",
    tier=0,
    description="Query real-time metric user proximity, dynamic acoustic scaling, Orb scale, and privacy shutter status (Tier 0 read-only).",
    args_schema=GetSensoryProximityTelemetryArgs,
    preview_fn=preview_get_sensory_proximity_telemetry,
    can_remember_per_folder=False,
)
def handle_get_sensory_proximity_telemetry() -> Dict[str, Any]:
    telemetry = sensory_proximity_manager.get_telemetry()
    return {
        "user_distance_meters": telemetry.user_distance_meters,
        "confidence": telemetry.confidence,
        "acoustic_volume_scale": telemetry.acoustic_volume_scale,
        "speech_rate_scale": telemetry.speech_rate_scale,
        "orb_particle_scale": telemetry.orb_particle_scale,
        "orb_glow_intensity": telemetry.orb_glow_intensity,
        "privacy_shutter_active": telemetry.privacy_shutter_active,
        "shutter_status": telemetry.shutter_status,
        "is_halted": sensory_proximity_manager.is_halted,
        "timestamp": telemetry.timestamp,
    }


# ==========================================
# 2. Simulate Proximity Observation (Tier 0)
# ==========================================

class SimulateProximityObservationArgs(BaseModel):
    ipd_pixels: float = Field(
        ...,
        description="Interpupillary distance in pixels (e.g. 55px = far ~74cm, 120px = close ~34cm)",
    )
    confidence: float = Field(
        0.90,
        ge=0.0,
        le=1.0,
        description="Detection confidence score",
    )


def preview_simulate_proximity_observation(args: Dict[str, Any]) -> str:
    ipd = args.get("ipd_pixels", 55.0)
    return f"Simulate proximity observation with IPD={ipd}px."


@registry.register(
    name="simulate_proximity_observation",
    tier=0,
    description="Ingest observed interpupillary distance (IPD in pixels) to update distance and acoustic scaling without disk persistence (Tier 0 diagnostic).",
    args_schema=SimulateProximityObservationArgs,
    preview_fn=preview_simulate_proximity_observation,
    can_remember_per_folder=False,
)
def handle_simulate_proximity_observation(
    ipd_pixels: float,
    confidence: float = 0.90,
) -> Dict[str, Any]:
    telemetry = sensory_proximity_manager.estimate_distance_from_ipd(
        ipd_pixels=ipd_pixels,
        confidence=confidence,
    )
    return {
        "status": "ESTIMATED",
        "user_distance_meters": telemetry.user_distance_meters,
        "acoustic_volume_scale": telemetry.acoustic_volume_scale,
        "speech_rate_scale": telemetry.speech_rate_scale,
        "orb_particle_scale": telemetry.orb_particle_scale,
        "shutter_status": telemetry.shutter_status,
    }


# ==========================================
# 3. Toggle Camera Privacy Shutter (Tier 1)
# ==========================================

class ToggleCameraPrivacyShutterArgs(BaseModel):
    enabled: bool = Field(
        ...,
        description="True to engage privacy shutter (cut video feed & flush buffers), False to open shutter",
    )


def preview_toggle_camera_privacy_shutter(args: Dict[str, Any]) -> str:
    en = args.get("enabled", True)
    action = "ENGAGE (Close & Wipe Video Feed)" if en else "DISENGAGE (Open Video Feed)"
    return f"Toggle camera privacy shutter: {action}."


@registry.register(
    name="toggle_camera_privacy_shutter",
    tier=1,
    description="Engage or disengage camera privacy shutter, instantly wiping volatile optical buffers and pausing vision tracking (Tier 1 privacy control).",
    args_schema=ToggleCameraPrivacyShutterArgs,
    preview_fn=preview_toggle_camera_privacy_shutter,
    can_remember_per_folder=False,
)
def handle_toggle_camera_privacy_shutter(enabled: bool) -> Dict[str, Any]:
    is_active = sensory_proximity_manager.set_privacy_shutter(enabled)
    return {
        "status": "UPDATED",
        "privacy_shutter_active": is_active,
        "shutter_status": "SHUTTER_CLOSED" if is_active else "SHUTTER_OPEN",
    }


# ==========================================
# 4. Configure Proximity Acoustic Curve (Tier 1)
# ==========================================

class ConfigureProximityAcousticCurveArgs(BaseModel):
    min_distance_m: Optional[float] = Field(
        None,
        description="Minimum distance bounding in meters (desk proximity)",
    )
    max_distance_m: Optional[float] = Field(
        None,
        description="Maximum distance bounding in meters (room perimeter)",
    )
    min_volume_scale: Optional[float] = Field(
        None,
        description="Minimum acoustic volume multiplier (0.10 to 1.0)",
    )
    max_volume_scale: Optional[float] = Field(
        None,
        description="Maximum acoustic volume multiplier (0.10 to 1.0)",
    )


def preview_configure_proximity_acoustic_curve(args: Dict[str, Any]) -> str:
    return "Configure proximity distance bounds and dynamic acoustic scaling curve."


@registry.register(
    name="configure_proximity_acoustic_curve",
    tier=1,
    description="Updates distance bounds and dynamic acoustic volume scaling range (Tier 1 configuration).",
    args_schema=ConfigureProximityAcousticCurveArgs,
    preview_fn=preview_configure_proximity_acoustic_curve,
    can_remember_per_folder=False,
)
def handle_configure_proximity_acoustic_curve(
    min_distance_m: Optional[float] = None,
    max_distance_m: Optional[float] = None,
    min_volume_scale: Optional[float] = None,
    max_volume_scale: Optional[float] = None,
) -> Dict[str, Any]:
    config = sensory_proximity_manager.configure_acoustic_curve(
        min_distance_m=min_distance_m,
        max_distance_m=max_distance_m,
        min_volume_scale=min_volume_scale,
        max_volume_scale=max_volume_scale,
    )
    return {
        "status": "CONFIGURED",
        "config": config,
    }
