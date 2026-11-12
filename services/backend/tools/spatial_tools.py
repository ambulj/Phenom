"""
Transparent Holographic Spatial Canvas Safety Tools (OVR-01, SAF-01, SAF-02).
Registers Tier 0 and Tier 1 governance tools for foreground window focus inspection,
transparent spatial overlay activation, and floating ghost annotation anchoring.
"""

from typing import Dict, Any, Optional

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.spatial import (
    SpatialGetFocusArgs,
    SpatialShowOverlayArgs,
    SpatialHideOverlayArgs,
    SpatialAddAnnotationArgs,
    SpatialDismissAnnotationArgs,
    SpatialToggleClickThroughArgs,
)
from services.backend.spatial.canvas_manager import spatial_canvas_manager


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="spatial_get_focus",
    tier=0,
    description="Queries current foreground active window focus, bounds, and spatial overlay state (Read-Only)",
    args_schema=SpatialGetFocusArgs,
    preview_fn=lambda a: "Inspect current desktop foreground window focus and spatial overlay state (Read-Only)",
)
def spatial_get_focus(**kwargs) -> Dict[str, Any]:
    """Inspect active window target and spatial overlay state."""
    state = spatial_canvas_manager.get_state()
    return {
        "status": "success",
        "spatial_state": state.model_dump(),
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

@registry.register(
    name="spatial_show_overlay",
    tier=1,
    description="Activates transparent holographic spatial canvas overlay (Reversible change with preview)",
    args_schema=SpatialShowOverlayArgs,
    preview_fn=lambda a: (
        f"Activate transparent holographic desktop spatial canvas "
        f"(click_through={a.get('click_through', True) if isinstance(a, dict) else getattr(a, 'click_through', True)})"
    ),
)
def spatial_show_overlay(
    click_through: bool = True,
    direct_comp: bool = True,
    **kwargs,
) -> Dict[str, Any]:
    """Display transparent holographic spatial canvas."""
    if guardian.is_halted or spatial_canvas_manager.is_halted():
        raise PermissionError("Spatial canvas operations halted by Guardian kill switch.")

    state = spatial_canvas_manager.show_overlay(click_through=click_through, direct_comp=direct_comp)
    return {
        "status": "success",
        "spatial_state": state.model_dump(),
    }


@registry.register(
    name="spatial_hide_overlay",
    tier=1,
    description="Hides and deactivates the transparent holographic spatial canvas (Reversible change with preview)",
    args_schema=SpatialHideOverlayArgs,
    preview_fn=lambda a: "Hide transparent holographic desktop spatial canvas",
)
def spatial_hide_overlay(**kwargs) -> Dict[str, Any]:
    """Hide and dismiss transparent holographic spatial canvas."""
    if guardian.is_halted or spatial_canvas_manager.is_halted():
        raise PermissionError("Spatial canvas operations halted by Guardian kill switch.")

    state = spatial_canvas_manager.hide_overlay()
    return {
        "status": "success",
        "spatial_state": state.model_dump(),
    }


@registry.register(
    name="spatial_add_annotation",
    tier=1,
    description="Adds a floating holographic ghost annotation anchored to active or target window (Reversible change with preview)",
    args_schema=SpatialAddAnnotationArgs,
    preview_fn=lambda a: (
        f"Add floating ghost annotation: '{a.get('title') if isinstance(a, dict) else getattr(a, 'title', '')}' "
        f"anchored at {a.get('anchor', 'top-right') if isinstance(a, dict) else getattr(a, 'anchor', 'top-right')}"
    ),
)
def spatial_add_annotation(
    title: str,
    content: str,
    target_window: Optional[str] = None,
    anchor: str = "top-right",
    offset_x: int = 20,
    offset_y: int = 20,
    ttl_seconds: Optional[float] = 300.0,
    style_preset: str = "cyber_cyan",
    click_through: bool = True,
    **kwargs,
) -> Dict[str, Any]:
    """Add a new floating ghost annotation."""
    if guardian.is_halted or spatial_canvas_manager.is_halted():
        raise PermissionError("Spatial canvas operations halted by Guardian kill switch.")

    annotation = spatial_canvas_manager.add_annotation(
        title=title,
        content=content,
        target_window=target_window,
        anchor=anchor,
        offset_x=offset_x,
        offset_y=offset_y,
        ttl_seconds=ttl_seconds,
        style_preset=style_preset,
        click_through=click_through,
    )
    return {
        "status": "success",
        "annotation": annotation.model_dump(),
    }


@registry.register(
    name="spatial_dismiss_annotation",
    tier=1,
    description="Dismisses a specific floating ghost annotation by ID (Reversible change with preview)",
    args_schema=SpatialDismissAnnotationArgs,
    preview_fn=lambda a: (
        f"Dismiss floating ghost annotation '{a.get('annotation_id') if isinstance(a, dict) else getattr(a, 'annotation_id', '')}'"
    ),
)
def spatial_dismiss_annotation(
    annotation_id: str,
    **kwargs,
) -> Dict[str, Any]:
    """Dismiss a floating ghost annotation."""
    if guardian.is_halted or spatial_canvas_manager.is_halted():
        raise PermissionError("Spatial canvas operations halted by Guardian kill switch.")

    dismissed = spatial_canvas_manager.dismiss_annotation(annotation_id=annotation_id)
    return {
        "status": "success" if dismissed else "not_found",
        "annotation_id": annotation_id,
        "dismissed": dismissed,
    }


@registry.register(
    name="spatial_toggle_click_through",
    tier=1,
    description="Toggles click-through pass-through mode for transparent spatial overlay (Reversible change with preview)",
    args_schema=SpatialToggleClickThroughArgs,
    preview_fn=lambda a: (
        f"Set spatial canvas click-through to {a.get('enabled') if isinstance(a, dict) else getattr(a, 'enabled', True)}"
    ),
)
def spatial_toggle_click_through(
    enabled: bool,
    **kwargs,
) -> Dict[str, Any]:
    """Toggle click-through mode."""
    if guardian.is_halted or spatial_canvas_manager.is_halted():
        raise PermissionError("Spatial canvas operations halted by Guardian kill switch.")

    result = spatial_canvas_manager.toggle_click_through(enabled=enabled)
    return {
        "status": "success",
        "click_through": result,
    }
