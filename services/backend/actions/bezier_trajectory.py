"""Cubic Bezier trajectory generator for human-like mouse cursor motion."""

from __future__ import annotations

import math
import random
from typing import List, Tuple
from services.backend.schemas.computer_use import BezierPath, Point2D, TrajectoryPoint


class BezierTrajectoryGenerator:
    """Generates natural, human-like mouse trajectories using cubic Bezier curves with Fitts' Law velocity profiles."""

    def __init__(self, jitter_factor: float = 0.15) -> None:
        self.jitter_factor = jitter_factor

    def _ease_in_out(self, t: float) -> float:
        """Sinusoidal ease-in ease-out velocity profile (Fitts' Law approximation)."""
        return 0.5 * (1.0 - math.cos(t * math.pi))

    def _cubic_bezier(
        self, p0: Tuple[float, float], p1: Tuple[float, float],
        p2: Tuple[float, float], p3: Tuple[float, float], t: float
    ) -> Tuple[float, float]:
        """Calculates point on cubic Bezier curve at parameter t in [0, 1]."""
        u = 1.0 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t

        x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
        y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
        return (x, y)

    def generate_path(
        self,
        start: Point2D,
        end: Point2D,
        duration_ms: float = 250.0,
        sample_interval_ms: float = 8.0,
    ) -> BezierPath:
        """Generates a smooth Bezier path from start to end with human-like curvature and velocity."""
        dx = end.x - start.x
        dy = end.y - start.y
        dist = math.hypot(dx, dy)

        if dist < 1.0 or duration_ms < sample_interval_ms:
            return BezierPath(
                start=start,
                end=end,
                points=[
                    TrajectoryPoint(x=start.x, y=start.y, timestamp_ms=0.0),
                    TrajectoryPoint(x=end.x, y=end.y, timestamp_ms=duration_ms)
                ],
                total_duration_ms=duration_ms
            )

        # Perpendicular unit vector for curvature displacement
        perp_x = -dy / dist
        perp_y = dx / dist

        # Random lateral offsets for control points P1 and P2
        max_lateral = min(dist * 0.25, 120.0) * self.jitter_factor
        offset1 = random.uniform(-max_lateral, max_lateral)
        offset2 = random.uniform(-max_lateral, max_lateral)

        # Control points at ~25% and ~75% along the segment
        p0 = (float(start.x), float(start.y))
        p1 = (
            start.x + dx * 0.25 + perp_x * offset1,
            start.y + dy * 0.25 + perp_y * offset1
        )
        p2 = (
            start.x + dx * 0.75 + perp_x * offset2,
            start.y + dy * 0.75 + perp_y * offset2
        )
        p3 = (float(end.x), float(end.y))

        num_steps = max(2, int(duration_ms / sample_interval_ms))
        points: List[TrajectoryPoint] = []

        for i in range(num_steps + 1):
            normalized_time = i / float(num_steps)
            eased_t = self._ease_in_out(normalized_time)
            x, y = self._cubic_bezier(p0, p1, p2, p3, eased_t)
            elapsed_ms = normalized_time * duration_ms
            points.append(
                TrajectoryPoint(
                    x=int(round(x)),
                    y=int(round(y)),
                    timestamp_ms=round(elapsed_ms, 2)
                )
            )

        # Guarantee final point exactly lands on target
        if points[-1].x != end.x or points[-1].y != end.y:
            points[-1] = TrajectoryPoint(x=end.x, y=end.y, timestamp_ms=duration_ms)

        return BezierPath(
            start=start,
            end=end,
            points=points,
            total_duration_ms=duration_ms
        )
