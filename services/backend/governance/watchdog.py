import time
from typing import Dict, Any, List, Optional
from collections import deque

from services.backend.schemas.subsystem_governance import (
    CircuitBreakerStatus,
    RemediationActionType,
    SubsystemTelemetry,
    RemediationResult,
    GovernanceWatchdogState,
)
from services.backend.governance.circuit_breaker import SelfHealingCircuitBreaker


class SubsystemGovernanceWatchdog:
    """
    Continuous background health observer for all Phenom subsystems.
    Tracks resource thresholds, anomalies, and executes deterministic remediations.
    """

    CORE_SUBSYSTEMS = [
        "telepresence",
        "biometric_enclaves",
        "deep_uia",
        "extension_fabric",
        "voice_action",
        "cognitive_twin",
    ]

    def __init__(self):
        self._is_active: bool = True
        self._circuit_breaker = SelfHealingCircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
        self._telemetry: Dict[str, SubsystemTelemetry] = {}
        self._recent_remediations: deque = deque(maxlen=30)

        # Thresholds
        self._max_error_count: int = 5
        self._max_memory_mb: float = 2048.0
        self._max_vram_mb: float = 4096.0

        self._init_subsystems()

    def _init_subsystems(self) -> None:
        now = time.time()
        for name in self.CORE_SUBSYSTEMS:
            self._telemetry[name] = SubsystemTelemetry(
                subsystem_name=name,
                health_score=1.0,
                circuit_status=CircuitBreakerStatus.NORMAL,
                memory_mb=128.0,
                vram_mb=256.0,
                last_heartbeat=now,
                error_count=0,
            )

    @property
    def is_active(self) -> bool:
        return self._is_active

    def record_telemetry(
        self,
        subsystem: str,
        health_score: float,
        memory_mb: float,
        vram_mb: float,
        is_error: bool = False,
    ) -> SubsystemTelemetry:
        if not self._is_active:
            raise PermissionError("Subsystem watchdog is halted under Guardian kill switch.")

        now = time.time()
        if is_error:
            circuit_status = self._circuit_breaker.record_error(subsystem)
        else:
            self._circuit_breaker.record_success(subsystem)
            circuit_status = self._circuit_breaker.get_status(subsystem)

        current = self._telemetry.get(subsystem)
        new_errors = (current.error_count + 1) if (current and is_error) else 0

        # Adjust health score if memory or errors spike
        adjusted_health = max(0.0, min(1.0, health_score))
        if memory_mb > self._max_memory_mb or vram_mb > self._max_vram_mb:
            adjusted_health = min(adjusted_health, 0.50)
            if circuit_status == CircuitBreakerStatus.NORMAL:
                circuit_status = CircuitBreakerStatus.DEGRADED

        telemetry = SubsystemTelemetry(
            subsystem_name=subsystem,
            health_score=round(adjusted_health, 3),
            circuit_status=circuit_status,
            memory_mb=round(memory_mb, 1),
            vram_mb=round(vram_mb, 1),
            last_heartbeat=now,
            error_count=new_errors,
        )
        self._telemetry[subsystem] = telemetry
        return telemetry

    def configure_thresholds(
        self,
        max_error_count: Optional[int] = None,
        max_memory_mb: Optional[float] = None,
        max_vram_mb: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not self._is_active:
            raise PermissionError("Subsystem watchdog is halted under Guardian kill switch.")

        if max_error_count is not None:
            self._max_error_count = max_error_count
            self._circuit_breaker._failure_threshold = max_error_count
        if max_memory_mb is not None:
            self._max_memory_mb = max_memory_mb
        if max_vram_mb is not None:
            self._max_vram_mb = max_vram_mb

        return {
            "max_error_count": self._max_error_count,
            "max_memory_mb": self._max_memory_mb,
            "max_vram_mb": self._max_vram_mb,
        }

    def trigger_remediation(
        self,
        subsystem: str,
        action_type: RemediationActionType,
    ) -> RemediationResult:
        if not self._is_active:
            raise PermissionError("Subsystem watchdog is halted under Guardian kill switch.")

        res = self._circuit_breaker.execute_remediation(subsystem, action_type)
        self._recent_remediations.appendleft(res)

        # Update telemetry after remediation
        if subsystem in self._telemetry:
            telem = self._telemetry[subsystem]
            self._telemetry[subsystem] = SubsystemTelemetry(
                subsystem_name=subsystem,
                health_score=1.0 if res.success else telem.health_score,
                circuit_status=self._circuit_breaker.get_status(subsystem),
                memory_mb=telem.memory_mb * 0.7 if action_type == RemediationActionType.FLUSH_STALE_BUFFERS else telem.memory_mb,
                vram_mb=telem.vram_mb * 0.5 if action_type == RemediationActionType.TRIM_GPU_CACHE else telem.vram_mb,
                last_heartbeat=time.time(),
                error_count=0 if res.success else telem.error_count,
            )

        return res

    def reset_circuit_breaker(self, subsystem: str) -> RemediationResult:
        return self.trigger_remediation(subsystem, RemediationActionType.RESET_CIRCUIT_BREAKER)

    def get_health(self, subsystem_name: Optional[str] = None) -> GovernanceWatchdogState:
        if subsystem_name:
            sub_dict = {subsystem_name: self._telemetry[subsystem_name]} if subsystem_name in self._telemetry else {}
        else:
            sub_dict = dict(self._telemetry)

        scores = [t.health_score for t in sub_dict.values()]
        avg_health = sum(scores) / len(scores) if scores else 1.0

        anomalies = []
        for name, t in sub_dict.items():
            if t.circuit_status in [CircuitBreakerStatus.DEGRADED, CircuitBreakerStatus.TRIPPED]:
                anomalies.append(f"{name} circuit {t.circuit_status.value} (errors: {t.error_count})")
            elif t.health_score < 0.70:
                anomalies.append(f"{name} health score degraded: {t.health_score}")

        return GovernanceWatchdogState(
            is_active=self._is_active,
            subsystems=sub_dict,
            overall_health=round(avg_health, 3),
            active_anomalies=anomalies,
            recent_remediations=list(self._recent_remediations),
        )

    def halt(self) -> None:
        """
        Synchronous Guardian halt (< 10ms SLA).
        Disengages background observers and freezes remediation tasks.
        """
        self._is_active = False

    def reset(self) -> None:
        """Restores watchdog to active state."""
        self._is_active = True
