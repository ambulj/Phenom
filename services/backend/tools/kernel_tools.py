"""
Deep OS Telemetry & Autonomous Environment Self-Healing Tools (KER-01, SAF-01, SAF-02).
Registers Tier 0 and Tier 1 tools for inspecting ETW crash telemetry,
diagnosing unhandled exceptions, scanning virtual environments, and applying deterministic remediation patches.
"""

from typing import Dict, Any, Optional

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.kernel_telemetry import (
    KernelGetTelemetryStatusArgs,
    KernelDiagnoseCrashArgs,
    KernelScanVenvDiscrepanciesArgs,
    KernelApplyHealingPatchArgs,
)
from services.backend.kernel.telemetry_listener import kernel_telemetry_fabric


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="kernel_get_telemetry_status",
    tier=0,
    description="Inspects real-time OS kernel telemetry, active crash events, and pending healing patches (Read-Only)",
    args_schema=KernelGetTelemetryStatusArgs,
    preview_fn=lambda a: "Inspect OS kernel telemetry, crash logs, and self-healing fabric state (Read-Only)",
)
def kernel_get_telemetry_status(**kwargs) -> Dict[str, Any]:
    """Inspect kernel telemetry status."""
    state = kernel_telemetry_fabric.get_fabric_state()
    return {
        "status": "success",
        "fabric_state": state.model_dump(),
    }


@registry.register(
    name="kernel_diagnose_crash",
    tier=0,
    description="Analyzes an unhandled process crash or ETW event, producing root cause diagnosis and proposed patch (Read-Only)",
    args_schema=KernelDiagnoseCrashArgs,
    preview_fn=lambda a: (
        f"Diagnose process crash in '{a.get('process_name') if isinstance(a, dict) else getattr(a, 'process_name', '')}' "
        f"(code: {a.get('exception_code') if isinstance(a, dict) else getattr(a, 'exception_code', '')}) [Read-Only]"
    ),
)
def kernel_diagnose_crash(
    process_name: str,
    exception_code: str,
    stack_trace: str = "",
    **kwargs,
) -> Dict[str, Any]:
    """Diagnose a crash and produce a suggested patch."""
    if guardian.is_halted or kernel_telemetry_fabric.is_halted():
        raise PermissionError("Kernel telemetry operations halted by Guardian kill switch.")

    crash_event = kernel_telemetry_fabric.ingest_crash_event(
        process_name=process_name,
        exception_code=exception_code,
        stack_trace=stack_trace,
    )

    return {
        "status": "success",
        "crash_event": crash_event.model_dump(),
    }


@registry.register(
    name="kernel_scan_venv_discrepancies",
    tier=0,
    description="Scans Python runtime environment for missing packages or manifest discrepancies (Read-Only)",
    args_schema=KernelScanVenvDiscrepanciesArgs,
    preview_fn=lambda a: "Scan Python virtual environment for missing or corrupted dependencies (Read-Only)",
)
def kernel_scan_venv_discrepancies(**kwargs) -> Dict[str, Any]:
    """Scan venv discrepancies."""
    if guardian.is_halted or kernel_telemetry_fabric.is_halted():
        raise PermissionError("Kernel telemetry operations halted by Guardian kill switch.")

    scan_res = kernel_telemetry_fabric.scan_venv_discrepancies()
    return {
        "status": "success",
        "scan_result": scan_res,
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

@registry.register(
    name="kernel_apply_healing_patch",
    tier=1,
    description="Applies a validated deterministic self-healing remediation patch to resolve environment discrepancies (Reversible change with preview)",
    args_schema=KernelApplyHealingPatchArgs,
    preview_fn=lambda a: (
        f"Apply self-healing remediation patch '{a.get('patch_id') if isinstance(a, dict) else getattr(a, 'patch_id', '')}' "
        f"to repair virtual environment"
    ),
)
def kernel_apply_healing_patch(
    patch_id: str,
    **kwargs,
) -> Dict[str, Any]:
    """Apply a deterministic self-healing patch."""
    if guardian.is_halted or kernel_telemetry_fabric.is_halted():
        raise PermissionError("Kernel self-healing operations halted by Guardian kill switch.")

    patch = kernel_telemetry_fabric.apply_healing_patch(patch_id)
    return {
        "status": "success",
        "patch": patch.model_dump(),
    }
