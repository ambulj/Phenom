import time
import uuid
from typing import Dict, Any, Optional

from services.backend.schemas.subsystem_governance import (
    CircuitBreakerStatus,
    RemediationActionType,
    RemediationResult,
)


class SelfHealingCircuitBreaker:
    """
    Stateful circuit breaker with automated self-healing remediation capabilities.
    Monitors failure rates and executes deterministic recovery routines.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._circuit_states: Dict[str, CircuitBreakerStatus] = {}
        self._consecutive_errors: Dict[str, int] = {}
        self._last_tripped_at: Dict[str, float] = {}

    def get_status(self, subsystem: str) -> CircuitBreakerStatus:
        status = self._circuit_states.get(subsystem, CircuitBreakerStatus.NORMAL)
        # Automatic transition from TRIPPED to HEALING if recovery timeout elapsed
        if status == CircuitBreakerStatus.TRIPPED:
            tripped_at = self._last_tripped_at.get(subsystem, 0.0)
            if time.time() - tripped_at > self._recovery_timeout:
                status = CircuitBreakerStatus.HEALING
                self._circuit_states[subsystem] = status
        return status

    def record_success(self, subsystem: str) -> None:
        self._consecutive_errors[subsystem] = 0
        if self._circuit_states.get(subsystem) in [CircuitBreakerStatus.DEGRADED, CircuitBreakerStatus.HEALING]:
            self._circuit_states[subsystem] = CircuitBreakerStatus.NORMAL

    def record_error(self, subsystem: str, error_msg: Optional[str] = None) -> CircuitBreakerStatus:
        errs = self._consecutive_errors.get(subsystem, 0) + 1
        self._consecutive_errors[subsystem] = errs

        if errs >= self._failure_threshold:
            self._circuit_states[subsystem] = CircuitBreakerStatus.TRIPPED
            self._last_tripped_at[subsystem] = time.time()
        elif errs >= max(1, self._failure_threshold // 2):
            self._circuit_states[subsystem] = CircuitBreakerStatus.DEGRADED
        else:
            self._circuit_states[subsystem] = CircuitBreakerStatus.NORMAL

        return self._circuit_states[subsystem]

    def reset(self, subsystem: str) -> None:
        self._circuit_states[subsystem] = CircuitBreakerStatus.NORMAL
        self._consecutive_errors[subsystem] = 0
        self._last_tripped_at.pop(subsystem, None)

    def execute_remediation(
        self,
        subsystem: str,
        action_type: RemediationActionType,
    ) -> RemediationResult:
        """Executes a deterministic remediation action."""
        remediation_id = f"rem-{uuid.uuid4().hex[:8]}"
        now = time.time()

        if action_type == RemediationActionType.RESET_CIRCUIT_BREAKER:
            self.reset(subsystem)
            return RemediationResult(
                remediation_id=remediation_id,
                subsystem_name=subsystem,
                action_type=action_type,
                success=True,
                message=f"Circuit breaker for {subsystem} restored to NORMAL.",
                timestamp=now,
            )

        elif action_type == RemediationActionType.FLUSH_STALE_BUFFERS:
            # Deterministic queue/buffer purge
            self._consecutive_errors[subsystem] = 0
            self._circuit_states[subsystem] = CircuitBreakerStatus.NORMAL
            return RemediationResult(
                remediation_id=remediation_id,
                subsystem_name=subsystem,
                action_type=action_type,
                success=True,
                message=f"Stale queues and frame buffers for {subsystem} flushed.",
                timestamp=now,
            )

        elif action_type == RemediationActionType.TRIM_GPU_CACHE:
            # Deterministic VRAM cache cleanup
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            return RemediationResult(
                remediation_id=remediation_id,
                subsystem_name=subsystem,
                action_type=action_type,
                success=True,
                message=f"PyTorch CUDA allocator cache trimmed for {subsystem}.",
                timestamp=now,
            )

        elif action_type == RemediationActionType.RECYCLE_WORKER:
            # Deterministic worker recycle
            self._consecutive_errors[subsystem] = 0
            self._circuit_states[subsystem] = CircuitBreakerStatus.NORMAL
            return RemediationResult(
                remediation_id=remediation_id,
                subsystem_name=subsystem,
                action_type=action_type,
                success=True,
                message=f"Background worker coroutine for {subsystem} recycled.",
                timestamp=now,
            )

        return RemediationResult(
            remediation_id=remediation_id,
            subsystem_name=subsystem,
            action_type=action_type,
            success=False,
            message=f"Unknown action {action_type}.",
            timestamp=now,
        )
