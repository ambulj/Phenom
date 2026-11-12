"""
Spatial Canvas Manager (OVR-01, SAF-01, SAF-02).
Manages DirectComposition transparent layered overlay state, ghost annotation positioning,
click-through toggling, and Guardian kill switch shutdown within < 10ms SLA.
"""

import logging
import time
import uuid
from typing import Callable, Dict, List, Optional

from services.backend.schemas.spatial import (
    ActiveWindowTarget,
    AnchorPoint,
    AnnotationStylePreset,
    GhostAnnotation,
    SpatialOverlayState,
    WindowRect,
)
from services.backend.spatial.focus_tracker import FocusTrackingEngine

logger = logging.getLogger(__name__)


class SpatialCanvasManager:
    """Orchestrates holographic spatial desktop overlays and focus-anchored ghost annotations."""

    def __init__(self, focus_tracker: Optional[FocusTrackingEngine] = None) -> None:
        self.focus_tracker = focus_tracker or FocusTrackingEngine()
        self._is_active: bool = False
        self._click_through: bool = True
        self._direct_comp: bool = True
        self._annotations: Dict[str, GhostAnnotation] = {}
        self._total_created: int = 0
        self._halted: bool = False
        self._broadcaster: Optional[Callable[[dict], None]] = None

    def register_broadcaster(self, broadcaster: Callable[[dict], None]) -> None:
        """Register WebSocket notification hook for real-time overlay synchronization."""
        self._broadcaster = broadcaster

    def _notify(self) -> None:
        """Broadcast state updates to connected clients."""
        if self._broadcaster and not self._halted:
            try:
                state = self.get_state()
                self._broadcaster({
                    "type": "spatial_state_update",
                    "payload": state.model_dump(),
                })
            except Exception as e:
                logger.debug(f"[SpatialCanvas] Notification broadcast error: {e}")

    def halt(self) -> None:
        """
        Immediate synchronous halt for Guardian kill switch (< 10ms SLA).
        Immediately hides overlay, wipes all floating annotations, and disengages tracking.
        """
        self._halted = True
        self._is_active = False
        self._click_through = True
        self._annotations.clear()
        self.focus_tracker.halt()
        logger.info("[SpatialCanvas] SpatialCanvasManager halted synchronously by Guardian.")

    def reset(self) -> None:
        """Reset after Guardian disengagement."""
        self._halted = False
        self.focus_tracker.reset()

    def is_halted(self) -> bool:
        return self._halted

    def show_overlay(self, click_through: bool = True, direct_comp: bool = True) -> SpatialOverlayState:
        """Activate the transparent holographic spatial overlay."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Spatial overlay access blocked.")

        self._is_active = True
        self._click_through = click_through
        self._direct_comp = direct_comp
        self._notify()
        return self.get_state()

    def hide_overlay(self) -> SpatialOverlayState:
        """Deactivate and dismiss the transparent holographic spatial overlay."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Spatial overlay access blocked.")

        self._is_active = False
        self._notify()
        return self.get_state()

    def toggle_click_through(self, enabled: bool) -> bool:
        """Toggle mouse click-through behavior (WS_EX_TRANSPARENT)."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Spatial overlay access blocked.")

        self._click_through = enabled
        self._notify()
        return self._click_through

    def _calculate_anchor_coordinates(
        self,
        bounds: WindowRect,
        anchor: AnchorPoint,
        offset_x: int,
        offset_y: int,
    ) -> tuple[int, int]:
        """Compute absolute screen coordinates based on anchor point and window rect."""
        card_width = 320
        card_height = 180

        if anchor == AnchorPoint.TOP_LEFT:
            screen_x = bounds.left + offset_x
            screen_y = bounds.top + offset_y
        elif anchor == AnchorPoint.TOP_RIGHT:
            screen_x = bounds.right - offset_x - card_width
            screen_y = bounds.top + offset_y
        elif anchor == AnchorPoint.BOTTOM_LEFT:
            screen_x = bounds.left + offset_x
            screen_y = bounds.bottom - offset_y - card_height
        elif anchor == AnchorPoint.BOTTOM_RIGHT:
            screen_x = bounds.right - offset_x - card_width
            screen_y = bounds.bottom - offset_y - card_height
        elif anchor == AnchorPoint.CENTER:
            screen_x = bounds.left + max(0, (bounds.width - card_width) // 2)
            screen_y = bounds.top + max(0, (bounds.height - card_height) // 2)
        else:  # CUSTOM
            screen_x = offset_x
            screen_y = offset_y

        # Clamp to non-negative bounds
        return max(0, screen_x), max(0, screen_y)

    def add_annotation(
        self,
        title: str,
        content: str,
        target_window: Optional[str] = None,
        anchor: str = "top-right",
        offset_x: int = 20,
        offset_y: int = 20,
        ttl_seconds: Optional[float] = 300.0,
        style_preset: str = "cyber_cyan",
        click_through: bool = True,
    ) -> GhostAnnotation:
        """Create and anchor a floating ghost annotation to target or foreground window."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Spatial overlay access blocked.")

        self.prune_expired()

        active_window = self.focus_tracker.get_active_window()
        anchor_enum = AnchorPoint(anchor) if anchor in [e.value for e in AnchorPoint] else AnchorPoint.TOP_RIGHT
        style_enum = (
            AnnotationStylePreset(style_preset)
            if style_preset in [e.value for e in AnnotationStylePreset]
            else AnnotationStylePreset.CYBER_CYAN
        )

        screen_x, screen_y = self._calculate_anchor_coordinates(
            active_window.bounds,
            anchor_enum,
            offset_x,
            offset_y,
        )

        annotation_id = f"ghost_{uuid.uuid4().hex[:8]}"
        annotation = GhostAnnotation(
            id=annotation_id,
            title=title.strip(),
            content=content.strip(),
            target_window_title=target_window or active_window.title,
            anchor_point=anchor_enum,
            offset_x=offset_x,
            offset_y=offset_y,
            screen_x=screen_x,
            screen_y=screen_y,
            opacity=0.92,
            click_through=click_through,
            created_at=time.time(),
            ttl_seconds=ttl_seconds,
            is_dismissed=False,
            style_preset=style_enum,
        )

        self._annotations[annotation_id] = annotation
        self._total_created += 1
        # Automatically make overlay active if annotations exist
        self._is_active = True
        self._notify()
        return annotation

    def dismiss_annotation(self, annotation_id: str) -> bool:
        """Dismiss a single ghost annotation by ID."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Spatial overlay access blocked.")

        if annotation_id in self._annotations:
            self._annotations[annotation_id].is_dismissed = True
            del self._annotations[annotation_id]
            self._notify()
            return True
        return False

    def prune_expired(self) -> int:
        """Remove annotations whose TTL has elapsed."""
        now = time.time()
        to_remove = []
        for ann_id, ann in self._annotations.items():
            if ann.ttl_seconds is not None and (now - ann.created_at) > ann.ttl_seconds:
                to_remove.append(ann_id)

        for ann_id in to_remove:
            del self._annotations[ann_id]

        if to_remove:
            self._notify()

        return len(to_remove)

    def get_state(self) -> SpatialOverlayState:
        """Retrieve complete current spatial overlay state."""
        self.prune_expired()
        active_window = self.focus_tracker.get_active_window()

        # Recalculate screen coordinates for annotations anchored to moving active window
        for ann in self._annotations.values():
            if ann.anchor_point != AnchorPoint.CUSTOM:
                sx, sy = self._calculate_anchor_coordinates(
                    active_window.bounds,
                    ann.anchor_point,
                    ann.offset_x,
                    ann.offset_y,
                )
                ann.screen_x = sx
                ann.screen_y = sy

        return SpatialOverlayState(
            is_active=self._is_active and not self._halted,
            click_through=self._click_through,
            direct_composition_enabled=self._direct_comp,
            active_window=active_window,
            annotations=list(self._annotations.values()),
            total_annotations_created=self._total_created,
            last_updated=time.time(),
        )


# Global singleton instance
spatial_canvas_manager = SpatialCanvasManager()
