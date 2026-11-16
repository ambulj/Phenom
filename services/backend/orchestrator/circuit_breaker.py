"""
Balanced Mission Circuit Breaker (Phase 47-04, HEAL-02, HEAL-03).
Prevents infinite autonomous execution loops and resource exhaustion:
1. Max 25 total steps per mission (HEAL-03).
2. Max 15 minutes (900 seconds) duration per mission (HEAL-03).
3. Max 5 self-reflective retries per failing step before operator escalation (HEAL-02).
"""

import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class CircuitBreakerTrippedError(RuntimeError):
    """Raised when an autonomous mission breaches step, duration, or retry limits."""
    pass


class CircuitBreakerState(BaseModel):
    """Runtime tracking telemetry for a mission's circuit breaker."""
    mission_id: str = Field(..., description="Active mission identifier")
    total_steps_executed: int = Field(default=0, description="Cumulative steps dispatched")
    step_retry_counts: Dict[str, int] = Field(default_factory=dict, description="Retries attempted per step ID")
    started_at: float = Field(default_factory=time.time, description="Mission initiation timestamp")
    is_tripped: bool = Field(default=False, description="True if safety thresholds were breached")
    trip_reason: Optional[str] = Field(default=None, description="Detailed explanation of trip condition")


class MissionCircuitBreaker:
    """Enforces hard bounds on autonomous mission execution depth, duration, and retries."""

    DEFAULT_MAX_STEPS = 25
    DEFAULT_MAX_DURATION_SECONDS = 900.0  # 15 minutes
    DEFAULT_MAX_RETRIES_PER_STEP = 5

    def __init__(
        self,
        max_steps: int = DEFAULT_MAX_STEPS,
        max_duration_seconds: float = DEFAULT_MAX_DURATION_SECONDS,
        max_retries_per_step: int = DEFAULT_MAX_RETRIES_PER_STEP
    ):
        self.max_steps = max_steps
        self.max_duration_seconds = max_duration_seconds
        self.max_retries_per_step = max_retries_per_step
        self._missions: Dict[str, CircuitBreakerState] = {}

    def start_mission(self, mission_id: str) -> CircuitBreakerState:
        """Initializes or resets tracking state for an autonomous mission."""
        state = CircuitBreakerState(
            mission_id=mission_id,
            total_steps_executed=0,
            step_retry_counts={},
            started_at=time.time(),
            is_tripped=False,
            trip_reason=None
        )
        self._missions[mission_id] = state
        return state

    def get_state(self, mission_id: str) -> Optional[CircuitBreakerState]:
        """Retrieves active circuit breaker telemetry for a mission."""
        return self._missions.get(mission_id)

    def check_health(self, mission_id: str) -> None:
        """
        Verifies that the mission has not exceeded duration or step limits.
        Raises CircuitBreakerTrippedError if thresholds are breached.
        """
        state = self._missions.get(mission_id)
        if not state:
            return

        if state.is_tripped:
            raise CircuitBreakerTrippedError(f"Circuit breaker already tripped: {state.trip_reason}")

        # 1. Duration check (15 minutes limit)
        elapsed = time.time() - state.started_at
        if elapsed > self.max_duration_seconds:
            state.is_tripped = True
            state.trip_reason = f"Mission exceeded hard time cap of {self.max_duration_seconds}s (elapsed: {elapsed:.1f}s)"
            raise CircuitBreakerTrippedError(state.trip_reason)

        # 2. Cumulative steps check (25 steps limit)
        if state.total_steps_executed >= self.max_steps:
            state.is_tripped = True
            state.trip_reason = f"Mission reached maximum execution limit of {self.max_steps} total steps"
            raise CircuitBreakerTrippedError(state.trip_reason)

    def record_step(self, mission_id: str, node_id: str) -> int:
        """
        Records the dispatch of a mission step and validates circuit bounds.
        Returns the updated total step count.
        """
        state = self._missions.get(mission_id)
        if not state:
            state = self.start_mission(mission_id)

        self.check_health(mission_id)

        state.total_steps_executed += 1

        # Check if this new step breaches the threshold
        if state.total_steps_executed > self.max_steps:
            state.is_tripped = True
            state.trip_reason = f"Mission exceeded maximum execution limit of {self.max_steps} total steps"
            raise CircuitBreakerTrippedError(state.trip_reason)

        return state.total_steps_executed

    def record_retry(self, mission_id: str, node_id: str) -> int:
        """
        Records a self-healing retry attempt for a specific step.
        Raises CircuitBreakerTrippedError if retries exceed max_retries_per_step (5).
        """
        state = self._missions.get(mission_id)
        if not state:
            state = self.start_mission(mission_id)

        self.check_health(mission_id)

        current_retries = state.step_retry_counts.get(node_id, 0) + 1
        state.step_retry_counts[node_id] = current_retries

        if current_retries > self.max_retries_per_step:
            state.is_tripped = True
            state.trip_reason = (
                f"Step '{node_id}' exceeded max retry cap of {self.max_retries_per_step} attempts "
                f"(attempted {current_retries}). Escalating to operator."
            )
            raise CircuitBreakerTrippedError(state.trip_reason)

        return current_retries

    def reset(self, mission_id: str) -> None:
        """Clears circuit breaker state for a mission."""
        self._missions.pop(mission_id, None)


# Global singleton instance
mission_circuit_breaker = MissionCircuitBreaker()
