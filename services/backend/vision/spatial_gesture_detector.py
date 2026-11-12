"""
Phenom Spatial Gesture Detector & Touchless Safety Halt
100% On-device, local multi-modal hand landmark tracking and gesture recognition.
Supports natural spatial gestures (raised palm emergency stop, index point, swipe left/right, thumbs up)
with volatile in-RAM frame buffering and sub-15ms Guardian safety halt integration.
"""

from collections import deque
from dataclasses import dataclass
from enum import Enum
import math
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from services.backend.safety.guardian import guardian


class Rule8ViolationError(Exception):
    """Raised when spatial gesture mapping or parameters target payment, checkout, or billing."""
    pass


_CHECKOUT_PATTERN = re.compile(
    r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
    re.IGNORECASE,
)


def enforce_anti_checkout(text: str) -> None:
    if _CHECKOUT_PATTERN.search(text):
        raise Rule8ViolationError(
            f"Rule 8 Violation: Payment, checkout, or billing directive detected in spatial gesture: '{text}'"
        )


class GestureType(str, Enum):
    NONE = "NONE"
    OPEN_PALM = "OPEN_PALM"
    RAISED_PALM = "RAISED_PALM"
    INDEX_POINT = "INDEX_POINT"
    SWIPE_LEFT = "SWIPE_LEFT"
    SWIPE_RIGHT = "SWIPE_RIGHT"
    THUMBS_UP = "THUMBS_UP"


@dataclass
class HandLandmark:
    x: float  # Normalized 0.0 to 1.0 (left to right)
    y: float  # Normalized 0.0 to 1.0 (top to bottom)
    z: float = 0.0  # Relative depth


@dataclass
class GestureTelemetry:
    gesture: GestureType
    confidence: float
    palm_normal: Tuple[float, float, float]
    pointing_target: Optional[Dict[str, float]]
    emergency_halt_triggered: bool
    mapped_action: Optional[str]
    timestamp: float


class SpatialGestureDetector:
    """
    Local on-device 21-point hand landmark tracker and spatial gesture classifier.
    Features:
    1. Zero disk persistence: frame representations live strictly in volatile memory.
    2. Emergency raised-palm stop with < 15.0ms Guardian kill switch trigger SLA.
    3. Spatial pointing coordinate resolution for touchless selection.
    4. Swipe left/right velocity tracking for desktop workspace switching.
    5. Action mapping with Rule 8 anti-checkout enforcement.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._halted: bool = False
        self._in_ram_frame_buffer: deque = deque(maxlen=3)

        # Configurable thresholds
        self.min_confidence: float = 0.65
        self.emergency_halt_confidence: float = 0.80
        self.swipe_velocity_threshold: float = 0.40  # normalized units per second
        self.emergency_auto_halt_enabled: bool = True

        # Gesture action mappings (e.g. SWIPE_LEFT -> "switch_workspace_left")
        self._action_mappings: Dict[GestureType, str] = {
            GestureType.SWIPE_LEFT: "switch_window_left",
            GestureType.SWIPE_RIGHT: "switch_window_right",
            GestureType.THUMBS_UP: "confirm_dialog",
        }

        # Historical landmark tracking for velocity / swipe calculation
        self._previous_wrist_x: Optional[float] = None
        self._previous_timestamp: Optional[float] = None

        # Current telemetry state
        self._current_telemetry: GestureTelemetry = GestureTelemetry(
            gesture=GestureType.NONE,
            confidence=0.0,
            palm_normal=(0.0, 0.0, 1.0),
            pointing_target=None,
            emergency_halt_triggered=False,
            mapped_action=None,
            timestamp=time.time(),
        )

    def halt(self, emergency_halt: bool = False) -> None:
        """Universal Guardian synchronous halt hook (< 25ms SLA)."""
        with self._lock:
            self._halted = True
            self._in_ram_frame_buffer.clear()
            self._previous_wrist_x = None
            self._previous_timestamp = None
            self._current_telemetry = GestureTelemetry(
                gesture=self._current_telemetry.gesture if emergency_halt else GestureType.NONE,
                confidence=self._current_telemetry.confidence if emergency_halt else 0.0,
                palm_normal=(0.0, 0.0, 1.0),
                pointing_target=None,
                emergency_halt_triggered=emergency_halt or self._current_telemetry.emergency_halt_triggered,
                mapped_action=None,
                timestamp=time.time(),
            )

    def reset_halt(self) -> None:
        """Reset halted state."""
        with self._lock:
            self._halted = False
            self._previous_wrist_x = None
            self._previous_timestamp = None
            self._current_telemetry = GestureTelemetry(
                gesture=GestureType.NONE,
                confidence=0.0,
                palm_normal=(0.0, 0.0, 1.0),
                pointing_target=None,
                emergency_halt_triggered=False,
                mapped_action=None,
                timestamp=time.time(),
            )

    @property
    def is_halted(self) -> bool:
        with self._lock:
            return self._halted

    def map_action(self, gesture: GestureType, action_name: str) -> None:
        """
        Map a spatial gesture to a named system action with Rule 8 validation.
        """
        enforce_anti_checkout(action_name)
        with self._lock:
            self._action_mappings[gesture] = action_name

    def get_action_mappings(self) -> Dict[str, str]:
        with self._lock:
            return {k.value: v for k, v in self._action_mappings.items()}

    def get_telemetry(self) -> GestureTelemetry:
        """Read-only telemetry snapshot."""
        with self._lock:
            return self._current_telemetry

    def trigger_emergency_halt(self, reason: str = "Raised open-palm emergency stop") -> float:
        """
        Directly invoke Guardian killswitch upon raised palm gesture.
        Returns execution latency in milliseconds (< 15.0ms hard SLA).
        """
        start = time.perf_counter()
        guardian.trigger(reason=reason)
        self.halt(emergency_halt=True)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return elapsed_ms

    def ingest_hand_landmarks(
        self,
        landmarks: List[Dict[str, float]],
        confidence: float = 0.90,
        frame_bytes: Optional[bytes] = None,
    ) -> GestureTelemetry:
        """
        Ingest 21 3D hand landmarks, classify spatial gesture, compute pointing coordinates,
        and optionally trigger emergency stop if raised open palm is detected.
        """
        now = time.time()
        with self._lock:
            if self._halted:
                return self._current_telemetry

            # Volatile in-RAM buffer lifecycle (Rule 4: Zero disk persistence)
            if frame_bytes:
                self._in_ram_frame_buffer.append({"bytes": frame_bytes, "ts": now})

            if len(landmarks) < 21 or confidence < self.min_confidence:
                self._current_telemetry = GestureTelemetry(
                    gesture=GestureType.NONE,
                    confidence=confidence,
                    palm_normal=(0.0, 0.0, 1.0),
                    pointing_target=None,
                    emergency_halt_triggered=False,
                    mapped_action=None,
                    timestamp=now,
                )
                self._previous_wrist_x = None
                self._previous_timestamp = None
                return self._current_telemetry

            pts = [HandLandmark(x=p.get("x", 0.0), y=p.get("y", 0.0), z=p.get("z", 0.0)) for p in landmarks]

            # 1. Compute Palm Normal vector (Wrist=0, Index_MCP=5, Pinky_MCP=17)
            v1 = (pts[5].x - pts[0].x, pts[5].y - pts[0].y, pts[5].z - pts[0].z)
            v2 = (pts[17].x - pts[0].x, pts[17].y - pts[0].y, pts[17].z - pts[0].z)
            # Cross product v1 x v2
            normal = (
                v1[1] * v2[2] - v1[2] * v2[1],
                v1[2] * v2[0] - v1[0] * v2[2],
                v1[0] * v2[1] - v1[1] * v2[0],
            )
            norm_mag = math.sqrt(normal[0] ** 2 + normal[1] ** 2 + normal[2] ** 2) or 1.0
            palm_normal = (normal[0] / norm_mag, normal[1] / norm_mag, normal[2] / norm_mag)

            # 2. Check finger extensions:
            # A finger is considered extended if Tip is noticeably above PIP / MCP in Y (y=0 is top of screen)
            # Or Euclidean distance from MCP to TIP is greater than MCP to PIP
            thumb_extended = pts[4].y < pts[3].y
            index_extended = pts[8].y < pts[6].y
            middle_extended = pts[12].y < pts[10].y
            ring_extended = pts[16].y < pts[14].y
            pinky_extended = pts[20].y < pts[18].y

            all_fingers_extended = (
                thumb_extended and index_extended and middle_extended and ring_extended and pinky_extended
            )
            only_index_extended = (
                index_extended and not middle_extended and not ring_extended and not pinky_extended
            )
            only_thumb_extended = (
                thumb_extended and not index_extended and not middle_extended and not ring_extended and not pinky_extended
            )

            # 3. Check for Swipe Velocity
            detected_gesture = GestureType.NONE
            wrist_x = pts[0].x
            if self._previous_wrist_x is not None and self._previous_timestamp is not None:
                dt = now - self._previous_timestamp
                if 0.01 <= dt <= 0.5:
                    velocity_x = (wrist_x - self._previous_wrist_x) / dt
                    if velocity_x < -self.swipe_velocity_threshold:
                        detected_gesture = GestureType.SWIPE_LEFT
                    elif velocity_x > self.swipe_velocity_threshold:
                        detected_gesture = GestureType.SWIPE_RIGHT

            self._previous_wrist_x = wrist_x
            self._previous_timestamp = now

            # If not a swipe, evaluate static poses
            pointing_target: Optional[Dict[str, float]] = None
            if detected_gesture == GestureType.NONE:
                if all_fingers_extended:
                    # Raised palm / Open palm facing camera
                    if pts[0].y > pts[9].y:  # Wrist lower than palm center
                        detected_gesture = GestureType.RAISED_PALM
                    else:
                        detected_gesture = GestureType.OPEN_PALM
                elif only_index_extended:
                    detected_gesture = GestureType.INDEX_POINT
                    # Pointing target derived from index tip projection (clamped 0.0 to 1.0)
                    pointing_target = {
                        "x": max(0.0, min(1.0, pts[8].x)),
                        "y": max(0.0, min(1.0, pts[8].y)),
                    }
                elif only_thumb_extended and pts[4].y < pts[0].y:
                    detected_gesture = GestureType.THUMBS_UP

            # 4. Check for Emergency Raised Palm Halt
            halt_triggered = False
            if detected_gesture in (GestureType.RAISED_PALM, GestureType.OPEN_PALM):
                if self.emergency_auto_halt_enabled and confidence >= self.emergency_halt_confidence:
                    halt_triggered = True

            mapped_action = self._action_mappings.get(detected_gesture)

            self._current_telemetry = GestureTelemetry(
                gesture=detected_gesture,
                confidence=confidence,
                palm_normal=palm_normal,
                pointing_target=pointing_target,
                emergency_halt_triggered=halt_triggered,
                mapped_action=mapped_action,
                timestamp=now,
            )

        # Trigger kill switch outside lock to prevent deadlock
        if halt_triggered:
            self.trigger_emergency_halt(reason="Emergency raised open-palm gesture detected")

        return self._current_telemetry


# Global singleton instance
spatial_gesture_detector = SpatialGestureDetector()
