"""Pre-Action Semantic Focus Guard (Milestone 49 Phase 3, GUI-02).

Enforces strict semantic validation on desktop foreground window title, PID,
process executable, and coordinate bounds prior to any mouse/keyboard interaction.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from services.backend.schemas.semantic_focus import (
    FocusVerificationRequest,
    FocusVerificationResult,
    WindowContext,
)
from services.backend.desktop.window_focus_tracker import WindowFocusTracker
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.desktop.semantic_focus_guard")


class SemanticFocusGuard:
    """Validates that the active desktop window strictly matches expected automation targets."""

    def __init__(self, tracker: Optional[WindowFocusTracker] = None) -> None:
        self.tracker = tracker or WindowFocusTracker()
        self._lock = threading.RLock()

    def _assert_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Focus verification aborted.")

    def verify_focus(self, request: FocusVerificationRequest) -> FocusVerificationResult:
        """Verifies active window context against requested preconditions."""
        self._assert_guardian()
        t0 = time.perf_counter()

        with self._lock:
            active_window = self.tracker.get_active_window()

            # 1. Check Minimized
            if active_window.is_minimized:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return FocusVerificationResult(
                    is_valid=False,
                    active_window=active_window,
                    error_reason=f"Target window '{active_window.title}' is minimized.",
                    latency_ms=round(elapsed_ms, 3),
                )

            # 2. Check Title
            if request.expected_title_contains:
                exp_title = request.expected_title_contains.strip().lower()
                act_title = active_window.title.lower()
                if exp_title not in act_title:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    return FocusVerificationResult(
                        is_valid=False,
                        active_window=active_window,
                        error_reason=f"Window title mismatch: expected substring '{request.expected_title_contains}', but active window is '{active_window.title}'",
                        latency_ms=round(elapsed_ms, 3),
                    )

            # 3. Check Process Name
            if request.expected_process_name:
                exp_proc = request.expected_process_name.strip().lower()
                act_proc = active_window.process_name.lower()
                if exp_proc not in act_proc:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    return FocusVerificationResult(
                        is_valid=False,
                        active_window=active_window,
                        error_reason=f"Process name mismatch: expected '{request.expected_process_name}', found '{active_window.process_name}'",
                        latency_ms=round(elapsed_ms, 3),
                    )

            # 4. Check PID
            if request.expected_pid is not None and request.expected_pid > 0:
                if request.expected_pid != active_window.pid:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    return FocusVerificationResult(
                        is_valid=False,
                        active_window=active_window,
                        error_reason=f"PID mismatch: expected PID {request.expected_pid}, found {active_window.pid}",
                        latency_ms=round(elapsed_ms, 3),
                    )

            # 5. Check Target Coordinates Containment
            if request.target_coordinates is not None:
                x, y = request.target_coordinates
                if not active_window.bounding_rect.contains(x, y):
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    b = active_window.bounding_rect
                    return FocusVerificationResult(
                        is_valid=False,
                        active_window=active_window,
                        error_reason=f"Target point ({x}, {y}) is outside active window bounding rect ({b.left}, {b.top}, {b.right}, {b.bottom})",
                        latency_ms=round(elapsed_ms, 3),
                    )

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return FocusVerificationResult(
                is_valid=True,
                active_window=active_window,
                error_reason=None,
                latency_ms=round(elapsed_ms, 3),
            )
