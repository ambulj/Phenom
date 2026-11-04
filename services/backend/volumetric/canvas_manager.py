"""
Volumetric Spatial Canvas Manager (VOL-01, SAF-01, SAF-02).
Coordinates 3D spatial node scene graphs, projection geometries (cylindrical, spherical, planar),
depth buffer layers, and gesture raycast selection with sub-10ms Guardian kill switch dismissal.
"""

import logging
import math
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from services.backend.schemas.volumetric import (
    GestureType,
    ProjectionGeometry,
    Vector3D,
    VisionGesturePayload,
    VolumetricNode,
    VolumetricWorkspaceState,
)
from services.backend.volumetric.gesture_tracker import (
    VisionGestureTracker,
    vision_gesture_tracker,
)

logger = logging.getLogger(__name__)


class VolumetricCanvasManager:
    """Manages 3D spatial scene graphs and holographic projection workspaces."""

    def __init__(self, gesture_tracker: Optional[VisionGestureTracker] = None) -> None:
        self.gesture_tracker = gesture_tracker or vision_gesture_tracker
        self._nodes: Dict[str, VolumetricNode] = {}
        self._projection_mode: ProjectionGeometry = ProjectionGeometry.CYLINDRICAL
        self._is_active: bool = False
        self._selected_node_id: Optional[str] = None
        self._halted: bool = False
        self._broadcaster: Optional[Callable[[dict], None]] = None

        # Wire gesture events
        self.gesture_tracker.register_listener(self._handle_gesture)

    def register_broadcaster(self, broadcaster: Callable[[dict], None]) -> None:
        self._broadcaster = broadcaster

    def _notify(self) -> None:
        if self._broadcaster and not self._halted:
            try:
                state = self.get_state()
                self._broadcaster({
                    "type": "volumetric_state_update",
                    "payload": state.model_dump(),
                })
            except Exception as e:
                logger.debug(f"[VolumetricCanvas] Broadcast error: {e}")

    def halt(self) -> None:
        """Immediate synchronous halt for Guardian kill switch (< 10ms SLA)."""
        self._halted = True
        self._is_active = False
        self._nodes.clear()
        self._selected_node_id = None
        self.gesture_tracker.halt()
        logger.info("[VolumetricCanvas] VolumetricCanvasManager halted synchronously by Guardian.")

    def reset(self) -> None:
        self._halted = False
        self.gesture_tracker.reset()

    def is_halted(self) -> bool:
        return self._halted

    def set_projection_mode(self, mode: str) -> ProjectionGeometry:
        """Switch 3D spatial coordinate projection geometry (cylindrical, spherical, planar)."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Volumetric canvas operations blocked.")

        clean_mode = mode.lower().strip()
        try:
            self._projection_mode = ProjectionGeometry(clean_mode)
        except ValueError:
            self._projection_mode = ProjectionGeometry.CYLINDRICAL

        self._notify()
        return self._projection_mode

    def spawn_node(
        self,
        label: str,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 1.5,
        color_hex: str = "#00f0ff",
        depth_layer: int = 1,
        is_pinned: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VolumetricNode:
        """Spawn an interactive 3D spatial node or card into the volumetric scene."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Volumetric canvas operations blocked.")

        node_id = f"vnode_{uuid.uuid4().hex[:8]}"
        node = VolumetricNode(
            node_id=node_id,
            label=label.strip(),
            position=Vector3D(x=x, y=y, z=max(0.2, z)),
            color_hex=color_hex,
            radius=0.15,
            is_pinned=is_pinned,
            depth_layer=depth_layer,
            metadata=metadata or {},
            created_at=time.time(),
        )

        self._nodes[node_id] = node
        self._is_active = True
        self._notify()
        return node

    def remove_node(self, node_id: str) -> bool:
        """Remove a node by ID."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Volumetric canvas operations blocked.")

        if node_id in self._nodes:
            del self._nodes[node_id]
            if self._selected_node_id == node_id:
                self._selected_node_id = None
            self._notify()
            return True
        return False

    def clear_canvas(self) -> int:
        """Remove all nodes from 3D scene."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Volumetric canvas operations blocked.")

        count = len(self._nodes)
        self._nodes.clear()
        self._selected_node_id = None
        self._notify()
        return count

    def select_node_by_raycast(
        self,
        ray_origin: Vector3D,
        ray_direction: Optional[Vector3D] = None,
    ) -> Optional[VolumetricNode]:
        """
        Select nearest spatial node using 3D Euclidean distance or direction raycast.
        """
        if not self._nodes:
            self._selected_node_id = None
            return None

        closest_node: Optional[VolumetricNode] = None
        min_dist = float("inf")

        for node in self._nodes.values():
            # Euclidean distance in 3D meters
            dx = node.position.x - ray_origin.x
            dy = node.position.y - ray_origin.y
            dz = node.position.z - ray_origin.z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)

            if dist < min_dist:
                min_dist = dist
                closest_node = node

        if closest_node and min_dist <= 2.5:  # Within 2.5m interaction sphere
            self._selected_node_id = closest_node.node_id
        else:
            self._selected_node_id = None

        return closest_node

    def _handle_gesture(self, gesture: VisionGesturePayload) -> None:
        """Autonomous gesture reaction."""
        if self._halted:
            return

        if gesture.gesture_type == GestureType.PALM_DISMISS:
            # Dismiss unpinned nodes
            unpinned = [nid for nid, n in self._nodes.items() if not n.is_pinned]
            for nid in unpinned:
                del self._nodes[nid]
            self._selected_node_id = None
            self._notify()

        elif gesture.gesture_type in (GestureType.POINT, GestureType.PINCH):
            # Target node near pointing finger
            self.select_node_by_raycast(gesture.hand_position)
            self._notify()

    def get_state(self) -> VolumetricWorkspaceState:
        return VolumetricWorkspaceState(
            is_active=self._is_active and not self._halted and len(self._nodes) > 0,
            projection_mode=self._projection_mode,
            total_nodes=len(self._nodes),
            nodes=list(self._nodes.values()),
            active_gesture=self.gesture_tracker.get_last_gesture(),
            multi_monitor_enabled=True,
            depth_buffer_enabled=True,
            selected_node_id=self._selected_node_id,
            last_updated=time.time(),
        )


# Global singleton instance
volumetric_canvas_manager = VolumetricCanvasManager()
