"""Unit test suite for Proactive Workspace Self-Healing Daemon & Automated AST Hot-Patching (Milestone 31 Phase 4).

Tests:
- Diagnostic error triage for TypeScript compiler errors (HEAL-01.1, HEAL-01.2).
- Diagnostic triage for Pytest test failures and missing dependencies (HEAL-01.1, HEAL-01.2).
- Automated AST hot-patch synthesis and formatted unified diff generation (PATCH-02.1).
- 1-click apply and non-destructive snapshot rollback lifecycle (PATCH-02.2).
- Strict Rule 8 anti-checkout enforcement across error triage and patch synthesis.
- Rule 11 credential protection and secret redaction.
- Guardian kill switch SLA < 25.0ms (Rule 3).
- Safety ToolRegistry registration and risk tiers (Tier 0 & Tier 1).
"""

from __future__ import annotations

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.evolution.workspace_self_healer import (
    WorkspaceSelfHealer,
    ErrorCategory,
    PatchStatus,
    Rule8ViolationError,
)
import services.backend.tools.workspace_self_healing_tools  # noqa: F401


@pytest.fixture(autouse=True)
def clean_guardian_and_healer():
    """Ensures guardian is resumed and provides a fresh WorkspaceSelfHealer instance."""
    guardian.resume()
    healer = WorkspaceSelfHealer()
    yield healer
    guardian.resume()


def test_diagnostic_triage_compiler_error(clean_guardian_and_healer):
    """HEAL-01.1 & HEAL-01.2: Verify parsing and triage of TypeScript compiler failures."""
    healer = clean_guardian_and_healer
    ts_error_trace = "src/components/Orb.tsx(42,15): error TS2339: Property 'renderTarget' does not exist on type 'WebGLRenderer'."

    diag = healer.diagnose_error(ts_error_trace)
    assert diag.category == ErrorCategory.COMPILER_ERROR
    assert "Orb.tsx" in diag.file_path
    assert diag.line_number == 42
    assert "TS2339" in diag.error_message
    assert diag.confidence >= 0.90
    assert "Orb.tsx at line 42" in diag.suggested_strategy


def test_diagnostic_triage_test_failure_and_missing_dep(clean_guardian_and_healer):
    """HEAL-01.1 & HEAL-01.2: Verify triage of Pytest test failures and missing modules."""
    healer = clean_guardian_and_healer

    # 1. Pytest failure
    pytest_trace = "FAILED services/backend/tests/test_barge_in.py::test_latency_sla - AssertionError: assert 0.018 < 0.015"
    diag_pytest = healer.diagnose_error(pytest_trace)
    assert diag_pytest.category == ErrorCategory.TEST_FAILURE
    assert "test_barge_in.py" in diag_pytest.file_path
    assert "test_latency_sla()" == diag_pytest.culprit_snippet
    assert "AssertionError" in diag_pytest.error_message

    # 2. Missing dependency
    dep_trace = "ModuleNotFoundError: No module named 'onnxruntime'"
    diag_dep = healer.diagnose_error(dep_trace)
    assert diag_dep.category == ErrorCategory.MISSING_DEPENDENCY
    assert "onnxruntime" in diag_dep.error_message
    assert "Install missing dependency" in diag_dep.suggested_strategy


def test_ast_hot_patch_synthesis_unified_diff(clean_guardian_and_healer):
    """PATCH-02.1: Verify unified diff generation for diagnosed code snippet."""
    healer = clean_guardian_and_healer

    diag = healer.diagnose_error("src/components/Orb.tsx(42,15): error TS2339: Property 'renderTarget'")
    target_code = "const target = (renderer as any).renderTarget;"
    repaired_code = "const target = renderer.getRenderTarget();"

    patch = healer.synthesize_hot_patch(
        diagnosis_id=diag.id,
        file_path="src/components/Orb.tsx",
        target_snippet=target_code,
        replacement_snippet=repaired_code,
    )

    assert patch.diagnosis_id == diag.id
    assert patch.file_path == "src/components/Orb.tsx"
    assert patch.status == PatchStatus.STAGED
    assert "--- a/src/components/Orb.tsx" in patch.unified_diff
    assert "+++ b/src/components/Orb.tsx" in patch.unified_diff
    assert f"-{target_code}" in patch.unified_diff
    assert f"+{repaired_code}" in patch.unified_diff


def test_apply_and_rollback_hot_patch_lifecycle(clean_guardian_and_healer):
    """PATCH-02.2: Verify 1-click apply and non-destructive snapshot rollback lifecycle."""
    healer = clean_guardian_and_healer

    file_dummy = "test_module.py"
    original_file_content = "def calculate():\n    return 10 / 0\n"
    target = "    return 10 / 0"
    replacement = "    return 10"

    patch = healer.synthesize_hot_patch(
        diagnosis_id="diag-lifecycle-1",
        file_path=file_dummy,
        target_snippet=target,
        replacement_snippet=replacement,
    )

    # Apply patch
    t0 = time.perf_counter()
    res_apply = healer.apply_patch(patch.id, file_override_content=original_file_content)
    apply_latency_ms = (time.perf_counter() - t0) * 1000.0

    assert res_apply.success is True
    assert res_apply.action == "APPLIED"
    assert patch.status == PatchStatus.APPLIED
    assert apply_latency_ms < 50.0

    # Snapshot must preserve original content
    assert healer._snapshots[patch.id] == original_file_content

    # Rollback patch (1-click non-destructive restoration)
    t1 = time.perf_counter()
    res_rollback = healer.rollback_patch(patch.id)
    rollback_latency_ms = (time.perf_counter() - t1) * 1000.0

    assert res_rollback.success is True
    assert res_rollback.action == "ROLLED_BACK"
    assert patch.status == PatchStatus.ROLLED_BACK
    assert rollback_latency_ms < 50.0
    assert healer.total_rollbacks == 1


def test_rule_8_anti_checkout_rejection(clean_guardian_and_healer):
    """Rule 8: Self-healer rejects error traces or patches touching payment/checkout operations."""
    healer = clean_guardian_and_healer

    checkout_traces = [
        "Exception in checkout_payment_gateway.py: Credit card authorization failed",
        "Error in order_billing_service.ts: Payment declined",
        "Purchase flow failed at line 89 in CartCheckout.tsx",
    ]

    for trace in checkout_traces:
        with pytest.raises(Rule8ViolationError):
            healer.diagnose_error(trace)

        with pytest.raises(Rule8ViolationError):
            healer.synthesize_hot_patch("diag-bad", "checkout.py", "pay()", "proceed()")


def test_rule_11_credential_protection(clean_guardian_and_healer):
    """Rule 11: Scrubbing sensitive API keys, secrets, and passwords in diagnostics and patches."""
    healer = clean_guardian_and_healer

    trace_with_secrets = "Auth failed: api_key: sk-proj-1234567890abcdef12345678 and token: auth-token-9876543210"
    diag = healer.diagnose_error(trace_with_secrets)
    assert "sk-proj" not in diag.error_message
    assert "auth-token" not in diag.error_message
    assert "[REDACTED]" in diag.error_message

    patch = healer.synthesize_hot_patch(
        diagnosis_id="diag-secret",
        file_path="config.py",
        target_snippet="api_key = 'sk-proj-1234567890abcdef12345678'",
        replacement_snippet="api_key = os.getenv('API_KEY')",
    )
    assert "sk-proj" not in patch.target_snippet
    assert "[REDACTED]" in patch.target_snippet


def test_guardian_kill_switch_sla(clean_guardian_and_healer):
    """Rule 3: Guardian kill switch halts self-healer operations with SLA < 25.0ms."""
    healer = clean_guardian_and_healer

    # Trip guardian
    t0 = time.perf_counter()
    guardian.trigger("Emergency self-healer halt")
    trip_latency_ms = (time.perf_counter() - t0) * 1000.0
    assert trip_latency_ms < 25.0

    # Operations must halt immediately
    t1 = time.perf_counter()
    with pytest.raises(RuntimeError, match="Execution halted by Guardian kill switch"):
        healer.diagnose_error("src/components/Orb.tsx(10,5): error TS1005: ';' expected.")
    check_latency_ms = (time.perf_counter() - t1) * 1000.0

    assert check_latency_ms < 25.0, f"Guardian SLA {check_latency_ms:.3f}ms exceeded 25.0ms"


def test_tool_registry_and_tiers():
    """Verify all 4 workspace self-healing tools are registered with correct Safety tiers."""
    diag_tool = registry.get("diagnose_workspace_error")
    synth_tool = registry.get("synthesize_ast_hot_patch")
    apply_tool = registry.get("apply_workspace_hot_patch")
    rollback_tool = registry.get("rollback_workspace_hot_patch")

    assert diag_tool is not None
    assert diag_tool.tier == 0  # Tier 0 read-only

    assert synth_tool is not None
    assert synth_tool.tier == 1  # Tier 1 staging

    assert apply_tool is not None
    assert apply_tool.tier == 1  # Tier 1 reversible file modification

    assert rollback_tool is not None
    assert rollback_tool.tier == 1  # Tier 1 reversible file restoration
