"""Humanized Cubic Bezier Trajectory Generator (Milestone 49 Phase 4, CHOREO-01).

Calculates natural mouse motion curves using cubic Bezier interpolation,
sinusoidal ease-in-ease-out velocity profiles, and physiological micro-jitter.
"""

from __future__ import annotations

import math
import random
import threading
from typing import List, Optional, Tuple

from services.backend.schemas.desktop_choreography import (
    BezierPoint,
    BezierTrajectory,
)
from services.backend.safety.guardian import guardian


class BezierTrajectoryGenerator:
    """Generates humanized cubic Bezier trajectories for smooth desktop automation."""

    def __init__(self, random_seed: Optional[int] = None) -> None:
        self._rng = random.Random(random_seed)
        self._lock = threading.RLock()

    def _assert_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Trajectory generation aborted.")

    def generate(
        self,
        start_pos: Tuple[int, int],
        target_pos: Tuple[int, int],
        duration_ms: Optional[float] = None,
        add_jitter: bool = True,
    ) -> BezierTrajectory:
        """Computes a smooth cubic Bezier curve connecting start_pos to target_pos."""
        self._assert_guardian()

        x0, y0 = float(start_pos[0]), float(start_pos[1])
        x3, y3 = float(target_pos[0]), float(target_pos[1])

        dx = x3 - x0
        dy = y3 - y0
        distance = math.hypot(dx, dy)

        # Dynamic duration based on Fitts' Law / distance scaling if not provided
        if duration_ms is None or duration_ms <= 0:
            duration_ms = max(150.0, min(800.0, 120.0 + (distance * 0.55)))

        # Determine number of intermediate waypoints (~10ms per point)
        num_points = max(15, min(80, int(duration_ms / 10.0)))

        with self._lock:
            # Control points generation with perpendicular human curvature
            if distance > 1e-3:
                # Perpendicular unit normal (-dy, dx)
                nx = -dy / distance
                ny = dx / distance

                # Randomized deviation magnitude (up to 15% of distance)
                dev1 = self._rng.uniform(-0.15, 0.15) * distance
                dev2 = self._rng.uniform(-0.15, 0.15) * distance

                x1 = x0 + (0.28 * dx) + (dev1 * nx)
                y1 = y0 + (0.28 * dy) + (dev1 * ny)

                x2 = x0 + (0.72 * dx) + (dev2 * nx)
                y2 = y0 + (0.72 * dy) + (dev2 * ny)
            else:
                x1, y1 = x0, y0
                x2, y2 = x3, y3

            points: List[BezierPoint] = []
            for i in range(num_points):
                # Normalized linear progress
                t = i / float(num_points - 1) if num_points > 1 else 1.0

                # Sinusoidal easing function (ease-in-out motor velocity)
                u = (1.0 - math.cos(math.pi * t)) / 2.0

                # Cubic Bezier formula: B(u) = (1-u)^3*P0 + 3(1-u)^2*u*P1 + 3(1-u)*u^2*P2 + u^3*P3
                c0 = (1.0 - u) ** 3
                c1 = 3.0 * ((1.0 - u) ** 2) * u
                c2 = 3.0 * (1.0 - u) * (u ** 2)
                c3 = u ** 3

                bx = (c0 * x0) + (c1 * x1) + (c2 * x2) + (c3 * x3)
                by = (c0 * y0) + (c1 * y1) + (c2 * y2) + (c3 * y3)

                # Apply physiological micro-jitter for intermediate points (tremor simulation)
                if add_jitter and 0 < i < (num_points - 1):
                    jx = max(-1.8, min(1.8, self._rng.gauss(0.0, 0.5)))
                    jy = max(-1.8, min(1.8, self._rng.gauss(0.0, 0.5)))
                    bx += jx
                    by += jy

                points.append(
                    BezierPoint(
                        x=round(bx, 2),
                        y=round(by, 2),
                        t=round(t, 4),
                        timestamp_ms=round(t * duration_ms, 2),
                    )
                )

        return BezierTrajectory(
            start_pos=start_pos,
            target_pos=target_pos,
            duration_ms=round(duration_ms, 2),
            total_distance_px=round(distance, 2),
            points=points,
            has_micro_jitter=add_jitter,
        )
