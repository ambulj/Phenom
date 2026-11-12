from typing import Dict, Any, Optional

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.subsystem_governance import (
    SubsystemGetHealthArgs,
    SubsystemTriggerRemediationArgs,
    SubsystemResetCircuitBreakerArgs,
    SubsystemConfigureThresholdsArgs,
    RemediationActionType,
)
from services.backend.governance import subsystem_governance_watchdog


@registry.register(
    name="subsystem_get_health",
    tier=0,
    description="Inspect system health, subsystem circuit breaker states, and resource telemetry (Read-Only)",
    args_schema=SubsystemGetHealthArgs,
    preview_fn=lambda args: "Querying subsystem governance health and circuit telemetry (Tier 0 read-only)",
)
def subsystem_get_health(subsystem_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Inspect health across all subsystems or a specific subsystem."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: subsystem health check blocked.")
    return subsystem_governance_watchdog.get_health(subsystem_name=subsystem_name).model_dump()


def _preview_trigger_remediation(args: Dict[str, Any]) -> str:
    return f"Trigger deterministic self-healing remediation '{args.get('action_type')}' for subsystem '{args.get('subsystem_name')}'"


@registry.register(
    name="subsystem_trigger_remediation",
    tier=1,
    description="Execute deterministic self-healing remediation (recycle worker, flush buffers, trim GPU) (Tier 1 Preview)",
    args_schema=SubsystemTriggerRemediationArgs,
    preview_fn=_preview_trigger_remediation,
)
def subsystem_trigger_remediation(
    subsystem_name: str,
    action_type: RemediationActionType,
    **kwargs,
) -> Dict[str, Any]:
    """Execute remediation for a degraded subsystem."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: remediation execution blocked.")
    res = subsystem_governance_watchdog.trigger_remediation(
        subsystem=subsystem_name,
        action_type=action_type,
    )
    return res.model_dump()


def _preview_reset_circuit_breaker(args: Dict[str, Any]) -> str:
    return f"Reset tripped circuit breaker for subsystem '{args.get('subsystem_name')}' to NORMAL"


@registry.register(
    name="subsystem_reset_circuit_breaker",
    tier=1,
    description="Reset a tripped or degraded circuit breaker back to NORMAL (Tier 1 Preview)",
    args_schema=SubsystemResetCircuitBreakerArgs,
    preview_fn=_preview_reset_circuit_breaker,
)
def subsystem_reset_circuit_breaker(subsystem_name: str, **kwargs) -> Dict[str, Any]:
    """Reset circuit breaker to NORMAL."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: circuit breaker reset blocked.")
    res = subsystem_governance_watchdog.reset_circuit_breaker(subsystem=subsystem_name)
    return res.model_dump()


def _preview_configure_thresholds(args: Dict[str, Any]) -> str:
    return (
        f"Configure subsystem watchdog thresholds: max_errors={args.get('max_error_count')}, "
        f"max_mem={args.get('max_memory_mb')}MB, max_vram={args.get('max_vram_mb')}MB"
    )


@registry.register(
    name="subsystem_configure_thresholds",
    tier=1,
    description="Configure anomaly detection error and resource thresholds (Tier 1 Preview)",
    args_schema=SubsystemConfigureThresholdsArgs,
    preview_fn=_preview_configure_thresholds,
)
def subsystem_configure_thresholds(
    max_error_count: Optional[int] = None,
    max_memory_mb: Optional[float] = None,
    max_vram_mb: Optional[float] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Configure anomaly detection thresholds."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: threshold configuration blocked.")
    return subsystem_governance_watchdog.configure_thresholds(
        max_error_count=max_error_count,
        max_memory_mb=max_memory_mb,
        max_vram_mb=max_vram_mb,
    )
