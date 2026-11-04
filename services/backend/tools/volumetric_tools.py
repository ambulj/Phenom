"""
Multi-Modal Holographic Workspace & Spatial 3D Volumetric Canvas Tools (VOL-01, SAF-01, SAF-02).
Registers Tier 0 and Tier 1 tools for managing 3D spatial node scene graphs,
configuring holographic projection geometry, clearing canvases, and processing vision gestures.
"""

from typing import Dict, Any, Optional

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.volumetric import (
    VolumetricGetWorkspaceStatusArgs,
    VolumetricSetProjectionModeArgs,
    VolumetricSpawnNodeArgs,
    VolumetricClearCanvasArgs,
    VolumetricIngestGestureArgs,
    Vector3D,
    GestureType,
    VisionGesturePayload,
)
from services.backend.volumetric.canvas_manager import volumetric_canvas_manager
from services.backend.volumetric.gesture_tracker import vision_gesture_tracker


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="volumetric_get_status",
    tier=0,
    description="Inspects active 3D holographic workspace state, rendered nodes, and gesture telemetry (Read-Only)",
    args_schema=VolumetricGetWorkspaceStatusArgs,
    preview_fn=lambda a: "Inspect 3D holographic spatial workspace state and active nodes (Read-Only)",
)
def volumetric_get_status(**kwargs) -> Dict[str, Any]:
    """Inspect volumetric workspace state."""
    state = volumetric_canvas_manager.get_state()
    return {
        "status": "success",
        "workspace_state": state.model_dump(),
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

@registry.register(
    name="volumetric_set_projection",
    tier=1,
    description="Configures 3D spatial coordinate projection geometry: cylindrical, spherical, or planar (Reversible change with preview)",
    args_schema=VolumetricSetProjectionModeArgs,
    preview_fn=lambda a: (
        f"Switch 3D holographic projection geometry to '{a.get('mode') if isinstance(a, dict) else getattr(a, 'mode', 'cylindrical')}'"
    ),
)
def volumetric_set_projection(
    mode: str,
    **kwargs,
) -> Dict[str, Any]:
    """Switch 3D projection mode."""
    if guardian.is_halted or volumetric_canvas_manager.is_halted():
        raise PermissionError("Volumetric canvas operations halted by Guardian kill switch.")

    new_mode = volumetric_canvas_manager.set_projection_mode(mode)
    return {
        "status": "success",
        "projection_mode": str(new_mode.value if hasattr(new_mode, "value") else new_mode),
    }


@registry.register(
    name="volumetric_spawn_node",
    tier=1,
    description="Spawns an interactive 3D spatial node or card into the volumetric canvas scene (Reversible change with preview)",
    args_schema=VolumetricSpawnNodeArgs,
    preview_fn=lambda a: (
        f"Spawn 3D volumetric node '{a.get('label') if isinstance(a, dict) else getattr(a, 'label', '')}' "
        f"at ({a.get('x', 0.0) if isinstance(a, dict) else getattr(a, 'x', 0.0):.1f}, "
        f"{a.get('y', 0.0) if isinstance(a, dict) else getattr(a, 'y', 0.0):.1f}, "
        f"{a.get('z', 1.5) if isinstance(a, dict) else getattr(a, 'z', 1.5):.1f}) "
        f"[layer {a.get('depth_layer', 1) if isinstance(a, dict) else getattr(a, 'depth_layer', 1)}]"
    ),
)
def volumetric_spawn_node(
    label: str,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 1.5,
    color_hex: str = "#00f0ff",
    depth_layer: int = 1,
    is_pinned: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Spawn a 3D spatial node."""
    if guardian.is_halted or volumetric_canvas_manager.is_halted():
        raise PermissionError("Volumetric canvas operations halted by Guardian kill switch.")

    node = volumetric_canvas_manager.spawn_node(
        label=label,
        x=x,
        y=y,
        z=z,
        color_hex=color_hex,
        depth_layer=depth_layer,
        is_pinned=is_pinned,
    )
    return {
        "status": "success",
        "node": node.model_dump(),
    }


@registry.register(
    name="volumetric_clear_canvas",
    tier=1,
    description="Clears all spatial nodes and cards from the 3D volumetric workspace (Reversible change with preview)",
    args_schema=VolumetricClearCanvasArgs,
    preview_fn=lambda a: "Clear all spatial nodes from the 3D volumetric canvas scene",
)
def volumetric_clear_canvas(**kwargs) -> Dict[str, Any]:
    """Clear all volumetric nodes."""
    if guardian.is_halted or volumetric_canvas_manager.is_halted():
        raise PermissionError("Volumetric canvas operations halted by Guardian kill switch.")

    count = volumetric_canvas_manager.clear_canvas()
    return {
        "status": "success",
        "cleared_count": count,
    }


@registry.register(
    name="volumetric_ingest_gesture",
    tier=1,
    description="Ingests a touchless vision gesture vector into the spatial engine (Reversible change with preview)",
    args_schema=VolumetricIngestGestureArgs,
    preview_fn=lambda a: (
        f"Ingest vision gesture '{a.get('gesture_type') if isinstance(a, dict) else getattr(a, 'gesture_type', 'IDLE')}' "
        f"(confidence={a.get('confidence', 0.9) if isinstance(a, dict) else getattr(a, 'confidence', 0.9):.2f})"
    ),
)
def volumetric_ingest_gesture(
    gesture_type: str,
    confidence: float = 0.9,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 1.0,
    pinch_distance: Optional[float] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Ingest a vision gesture into the volumetric canvas."""
    if guardian.is_halted or volumetric_canvas_manager.is_halted():
        raise PermissionError("Volumetric canvas operations halted by Guardian kill switch.")

    try:
        gtype = GestureType(gesture_type.upper().strip())
    except ValueError:
        gtype = GestureType.IDLE

    payload = vision_gesture_tracker.ingest_gesture(
        gesture_type=gtype,
        confidence=confidence,
        hand_position=Vector3D(x=x, y=y, z=z),
        pinch_distance=pinch_distance,
    )

    return {
        "status": "success",
        "gesture": payload.model_dump(),
        "selected_node_id": volumetric_canvas_manager.get_state().selected_node_id,
    }
