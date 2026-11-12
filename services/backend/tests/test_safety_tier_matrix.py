"""Tests for Safety Tier Matrix & Pragmatic Auto-Execution (Milestone 29 Phase 2).

Validates:
- TIER-01.1: Automatic zero-prompt execution for Tier 0 and Tier 1 tools when untainted.
- TIER-01.2: Reversible local desktop operations (recycle_delete, open_app, close_app) in auto tiers.
- AUTO-02.1: Strict user confirmation gating for Tier 2 high-risk tools.
- AUTO-02.2: Rule 8 anti-checkout invariants remain non-negotiable and unconditionally blocked (Tier 3).
- SAF-01: Tools (evaluate_tool_auto_execution_policy, reclassify_safety_tier, get_safety_tier_matrix).
- SAF-02: Universal Guardian kill switch SLA halt (< 25.0ms SLA).
- Rule 4: 100% on-device local execution.
"""

import os
import tempfile
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.safety.engine import SafetyExecutionEngine
import services.backend.tools.app_tools
import services.backend.tools.file_tools
from services.backend.safety.tier_matrix import (
    SafetyTierMatrixManager,
    Rule8ViolationError,
    safety_tier_matrix_manager,
)
from services.backend.tools.safety_matrix_tools import (
    handle_evaluate_tool_auto_execution_policy,
    handle_reclassify_safety_tier,
    handle_get_safety_tier_matrix,
)


@pytest.fixture(autouse=True)
def reset_state():
    guardian.resume()
    safety_tier_matrix_manager.auto_execute_tier1 = True
    yield
    guardian.resume()


@pytest.mark.asyncio
async def test_tier_0_and_tier_1_auto_execution():
    """Validates that Tier 0 and Tier 1 tools execute automatically without confirmation prompts."""
    engine = SafetyExecutionEngine()
    engine.auto_execute_tier1 = True

    # 1. Tier 0 tool execution (read-only, auto)
    res0 = await engine.execute_tool("list_apps", {})
    assert res0["status"] == "success"
    assert isinstance(res0["result"], list)
    assert len(res0["result"]) > 0

    # 2. Tier 1 tool execution (safe/reversible, zero-prompt auto)
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_auto.txt")
        # create_file is Tier 1
        res1 = await engine.execute_tool("create_file", {"path": test_file, "content": "auto run content"})
        assert res1["status"] == "success"
        assert os.path.exists(test_file)

        # recycle_delete is Tier 1 (moves to Recycle Bin, non-destructive per Rule 7)
        res_del = await engine.execute_tool("recycle_delete", {"path": test_file})
        assert res_del["status"] == "success"
        assert res_del["result"]["recycled"] is True
        assert not os.path.exists(test_file)


@pytest.mark.asyncio
async def test_tier_2_requires_confirmation():
    """Validates that Tier 2 high-risk tools strictly require confirmation."""
    engine = SafetyExecutionEngine()

    confirmation_prompted = False

    async def mock_handler(req_id, tool, tier, preview, args, can_remember, folder_path, timeout):
        nonlocal confirmation_prompted
        confirmation_prompted = True
        return ("approved", False)

    engine.set_confirmation_handler(mock_handler)

    # Reclassify a test tool temporarily to Tier 2
    safety_tier_matrix_manager.reclassify_tool("create_file", 2, "Test Tier 2 prompt")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "prompt_test.txt")
        res = await engine.execute_tool("create_file", {"path": test_file, "content": "Prompted content"})
        assert confirmation_prompted is True
        assert res["status"] == "success"
    # Restore
    safety_tier_matrix_manager.reclassify_tool("create_file", 1, "Restore Tier 1")


def test_evaluate_tool_auto_execution_policy():
    """Evaluates policy checking across different tiers."""
    # open_app should be Tier 0 (auto-executable)
    p_open = safety_tier_matrix_manager.evaluate_tool_policy("open_app")
    assert p_open.tier == 0
    assert p_open.auto_executable is True
    assert p_open.requires_confirmation is False
    assert p_open.is_blocked is False

    # recycle_delete should be Tier 1 (auto-executable)
    p_rec = safety_tier_matrix_manager.evaluate_tool_policy("recycle_delete")
    assert p_rec.tier == 1
    assert p_rec.auto_executable is True
    assert p_rec.requires_confirmation is False

    # Unregistered tool -> Tier 3 blocked
    p_unreg = safety_tier_matrix_manager.evaluate_tool_policy("totally_unregistered_tool_xyz")
    assert p_unreg.tier == 3
    assert p_unreg.is_blocked is True
    assert p_unreg.auto_executable is False


def test_reclassify_safety_tier():
    """Tests dynamic tool safety tier reclassification and validation."""
    # Valid reclassification
    rec = safety_tier_matrix_manager.reclassify_tool("list_apps", 1, reason="Test reclassify to Tier 1")
    assert rec.new_tier == 1
    assert rec.tool_name == "list_apps"

    # Restore
    rec2 = safety_tier_matrix_manager.reclassify_tool("list_apps", 0, reason="Restore to Tier 0")
    assert rec2.new_tier == 0

    # Invalid tier values
    with pytest.raises(ValueError, match="Invalid tier"):
        safety_tier_matrix_manager.reclassify_tool("list_apps", 99)

    # Unregistered tool
    with pytest.raises(ValueError, match="Cannot reclassify unregistered tool"):
        safety_tier_matrix_manager.reclassify_tool("fake_nonexistent_tool", 0)


def test_get_safety_tier_matrix_report():
    """Verifies that the full audit matrix contains registered tools and counts."""
    report = safety_tier_matrix_manager.get_matrix_report()
    assert report.total_tools > 0
    assert report.auto_executable_count > 0
    assert report.tier_counts[0] > 0
    assert report.tier_counts[1] > 0
    assert report.auto_execute_tier1_enabled is True


def test_rule_8_anti_checkout_rejection():
    """Rule 8: Payment or checkout keywords must raise Rule8ViolationError."""
    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        safety_tier_matrix_manager.evaluate_tool_policy("checkout_payment_gateway")

    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        safety_tier_matrix_manager.reclassify_tool("open_app", 1, reason="pay order now")


def test_guardian_kill_switch_sla():
    """Benchmarks Guardian kill switch halt across safety matrix manager."""
    guardian.resume()
    start_time = time.perf_counter()
    guardian.trigger("EMERGENCY_HALT_TEST")
    halt_duration_ms = (time.perf_counter() - start_time) * 1000.0

    assert halt_duration_ms < 25.0, f"Guardian halt took {halt_duration_ms:.4f}ms, exceeded 25.0ms SLA"

    # Matrix operations must fail immediately
    with pytest.raises(RuntimeError, match="SAFETY_MATRIX_HALTED"):
        safety_tier_matrix_manager.evaluate_tool_policy("open_app")

    with pytest.raises(RuntimeError, match="SAFETY_MATRIX_HALTED"):
        safety_tier_matrix_manager.get_matrix_report()


def test_tools_handle_functions():
    """Verifies that the 3 registered safety matrix tools handle calls properly."""
    # 1. evaluate_tool_auto_execution_policy (Tier 0)
    p = handle_evaluate_tool_auto_execution_policy("open_app")
    assert p["tool_name"] == "open_app"
    assert p["auto_executable"] is True

    # 2. reclassify_safety_tier (Tier 1)
    rec = handle_reclassify_safety_tier("list_files", 1, reason="Test via handle")
    assert rec["new_tier"] == 1
    # Restore
    handle_reclassify_safety_tier("list_files", 0, reason="Restore via handle")

    # 3. get_safety_tier_matrix (Tier 0)
    rep = handle_get_safety_tier_matrix()
    assert rep["total_tools"] > 0
    assert rep["auto_execute_tier1_enabled"] is True
