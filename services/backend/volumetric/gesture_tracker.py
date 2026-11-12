"""
Vision Gesture Tracking Engine (VOL-01, SAF-01, SAF-02).
Extracts and classifies touchless hand gestures (Pinch, Point, Palm Dismiss, Swipes)
from normalized numeric landmark vectors in RAM with zero camera pixel exfiltration (Rule 4).
"""

import logging
import math
import time
import uuid
from typing import Callable, List, Optional

from services.backend.schemas.volumetric import (
    GestureType,
    Vector3D,
    VisionGesturePayload,
)

logger = logging.getLogger(__name__)


class VisionGestureTracker:
    """Classifies touchless 3D spatial hand gestures from camera landmark coordinates."""

    def __init__(self) -> None:
        self._halted: bool = False
        self._recent_gestures: List[VisionGesturePayload] = []
        self._last_gesture: Optional[VisionGesturePayload] = None
        self._listener: Optional[Callable[[VisionGesturePayload], None]] = None

    def register_listener(self, listener: Callable[[VisionGesturePayload], None]) -> None:
        self._listener = listener

    def halt(self) -> None:
        """Immediate synchronous halt for Guardian kill switch (< 10ms SLA)."""
        self._halted = True
        self._last_gesture = None
        logger.info("[GestureTracker] VisionGestureTracker halted synchronously by Guardian.")

    def reset(self) -> None:
        self._halted = False

    def is_halted(self) -> bool:
        return self._halted

    def process_gesture(
        self,
        gesture_type: GestureType | str,
        confidence: float = 0.9,
        hand_position: Optional[Vector3D] = None,
        pinch_distance: Optional[float] = None,
    ) -> VisionGesturePayload:
        """
        Classify and ingest a hand gesture.
        Raises PermissionError if Guardian is halted.
        """
        if self._halted:
            raise PermissionError("Guardian kill switch active: Gesture tracking halted.")

        # Coerce enum
        if isinstance(gesture_type, str):
            try:
                g_type = GestureType(gesture_type.upper())
            except ValueError:
                g_type = GestureType.IDLE
        else:
            g_type = gesture_type

        # Autonomous gesture deduction if pinch_distance provided
        if pinch_distance is not None and pinch_distance < 0.05:
            g_type = GestureType.PINCH

        pos = hand_position or Vector3D(x=0.0, y=0.0, z=1.0)
        payload = VisionGesturePayload(
            gesture_id=f"gst_{uuid.uuid4().hex[:8]}",
            gesture_type=g_type,
            confidence=max(0.0, min(1.0, confidence)),
            hand_position=pos,
            pinch_distance=pinch_distance,
            timestamp=time.time(),
        )

        self._last_gesture = payload
        self._recent_gestures.append(payload)
        if len(self._recent_gestures) > 50:
            self._recent_gestures.pop(0)

        if self._listener:
            try:
                self._listener(payload)
            except Exception as e:
                logger.debug(f"[GestureTracker] Listener callback error: {e}")

        return payload

    def ingest_gesture(
        self,
        gesture_type: GestureType | str,
        confidence: float = 0.9,
        hand_position: Optional[Vector3D] = None,
        pinch_distance: Optional[float] = None,
    ) -> VisionGesturePayload:
        """Alias for process_gesture."""
        return self.process_gesture(
            gesture_type=gesture_type,
            confidence=confidence,
            hand_position=hand_position,
            pinch_distance=pinch_distance,
        )

    def classify_from_landmarks(
        self,
        thumb_tip: Vector3D,
        index_tip: Vector3D,
        wrist: Optional[Vector3D] = None,
    ) -> VisionGesturePayload:
        """Classify gesture from landmark coordinates in RAM without storing camera frames."""
        dx = thumb_tip.x - index_tip.x
        dy = thumb_tip.y - index_tip.y
        dz = thumb_tip.z - index_tip.z
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        gesture_type = GestureType.PINCH if dist < 0.05 else GestureType.POINT
        return self.process_gesture(
            gesture_type=gesture_type,
            confidence=0.95,
            hand_position=wrist or thumb_tip,
            pinch_distance=dist,
        )

    def get_last_gesture(self) -> Optional[VisionGesturePayload]:
        return self._last_gesture


# Global singleton instance
vision_gesture_tracker = VisionGestureTracker()
