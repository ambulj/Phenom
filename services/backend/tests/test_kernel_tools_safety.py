"""Safety registry and execution tests for Milestone 13 Phase 4: Kernel Tools (SAF-01, SAF-02)."""

import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.kernel.telemetry_listener import kernel_telemetry_fabric
import services.backend.tools.kernel_tools as ktools


EXPECTED_KERNEL_TOOLS = {
    "kernel_get_telemetry_status": 0,
    "kernel_diagnose_crash": 0,
    "kernel_scan_venv_discrepancies": 0,
    "kernel_apply_healing_patch": 1,
}


@pytest.fixture(autouse=True)
def clean_kernel_state():
    guardian.resume()
    kernel_telemetry_fabric.reset()
    yield
    guardian.resume()
    kernel_telemetry_fabric.reset()


def test_kernel_tools_registered_in_registry():
    """Verify all 4 kernel tools exist in ToolRegistry with their required risk tiers."""
    for tool_name, expected_tier in EXPECTED_KERNEL_TOOLS.items():
        assert tool_name in registry._tools, f"Tool '{tool_name}' must be in ToolRegistry"
        meta = registry._tools[tool_name]
        assert meta.tier == expected_tier, (
            f"Tool '{tool_name}' must have Risk Tier {expected_tier}, but got {meta.tier}"
        )
        assert meta.args_schema is not None
        assert meta.preview_fn is not None


def test_kernel_tier_0_queries_execute():
    """Verify Tier 0 queries execute cleanly."""
    res = ktools.kernel_get_telemetry_status()
    assert res["status"] == "success"
    assert "fabric_state" in res
    assert res["fabric_state"]["is_monitoring"] is True

    diag = ktools.kernel_diagnose_crash(
        process_name="python.exe",
        exception_code="ModuleNotFoundError",
        stack_trace="No module named 'torch'",
    )
    assert diag["status"] == "success"
    assert "torch" in diag["crash_event"]["root_cause_diagnosis"]

    scan = ktools.kernel_scan_venv_discrepancies()
    assert scan["status"] == "success"
    assert scan["scan_result"]["status"] == "healthy"


def test_kernel_apply_healing_patch_tier_1():
    """Verify Tier 1 remediation patch execution with preview."""
    diag = ktools.kernel_diagnose_crash(
        process_name="python.exe",
        exception_code="ModuleNotFoundError",
        stack_trace="No module named 'numpy'",
    )
    patch_id = diag["crash_event"]["remediation_patch"]["patch_id"]

    patch_meta = registry._tools["kernel_apply_healing_patch"]
    preview = patch_meta.preview_fn({"patch_id": patch_id})
    assert patch_id in preview
    assert "remediation patch" in preview

    apply_res = ktools.kernel_apply_healing_patch(patch_id=patch_id)
    assert apply_res["status"] == "success"
    assert apply_res["patch"]["is_applied"] is True


def test_kernel_tools_fail_closed_under_guardian_halt():
    """Verify fail-closed behavior under Guardian kill switch lockdown."""
    diag = ktools.kernel_diagnose_crash(
        process_name="test.exe",
        exception_code="0xC0000005",
        stack_trace="Memory access violation",
    )
    patch_id = diag["crash_event"]["remediation_patch"]["patch_id"]

    try:
        guardian.trigger("Emergency test halt")
        kernel_telemetry_fabric.halt()

        assert kernel_telemetry_fabric.is_halted() is True

        # Tier 1 tools must raise PermissionError
        with pytest.raises(PermissionError, match="halted by Guardian"):
            ktools.kernel_apply_healing_patch(patch_id=patch_id)

    finally:
        guardian.resume()
        kernel_telemetry_fabric.reset()
