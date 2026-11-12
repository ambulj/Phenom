"""
Unit & Integration Test Suite for Autonomous Diagnostic Test-Runner & Self-Healing Worktree Mission Agent.
Validates worktree sandboxing, traceback parsing, self-healing loop, automatic rollback, and Guardian SLA.

Part of Phenom 20.0 Sovereign Autonomous Developer (DEV-02.1, DEV-02.2, MIS-02.1, SAF-01, SAF-02).
"""

import asyncio
import os
import shutil
import tempfile
import time
from pathlib import Path
import pytest

from services.backend.coding.worktree_manager import WorktreeManager, WorktreeSandbox
from services.backend.coding.test_runner_daemon import TestRunnerDaemon, TestRunResult
from services.backend.coding.traceback_parser import TracebackParser
from services.backend.coding.diagnostic_agent import DiagnosticMissionAgent, MissionRequest, MissionReport
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.diagnostic_tools  # Register tools


# ==========================================
# 1. Worktree Sandbox Lifecycle Tests
# ==========================================

def test_worktree_sandbox_lifecycle(tmp_path):
    mgr = WorktreeManager(repo_root=str(tmp_path))
    
    # Create sandbox
    sb = mgr.create_worktree(sandbox_id="test_wt_01", commit_ish="HEAD")
    assert sb.sandbox_id == "test_wt_01"
    assert Path(sb.path).exists()
    assert sb.is_active is True

    # List sandboxes
    active = mgr.list_worktrees()
    assert any(s.sandbox_id == "test_wt_01" for s in active)

    # Remove sandbox
    removed = mgr.remove_worktree("test_wt_01", force=True)
    assert removed is True
    assert not Path(sb.path).exists()
    assert len(mgr.list_worktrees()) == 0


def test_worktree_pruning(tmp_path):
    mgr = WorktreeManager(repo_root=str(tmp_path))
    
    sb = mgr.create_worktree(sandbox_id="test_wt_stale", commit_ish="HEAD")
    assert Path(sb.path).exists()

    # Artificially age the sandbox
    sb.created_at = time.time() - 7200  # 2 hours old

    pruned = mgr.prune_worktrees(max_age_seconds=3600)
    assert pruned >= 1
    assert not Path(sb.path).exists()


# ==========================================
# 2. Traceback Parser Diagnostic Tests
# ==========================================

def test_traceback_parser_diagnostics():
    parser = TracebackParser()

    # Pytest failure trace
    pytest_sample = """
=================================== FAILURES ===================================
_________________________________ test_calc __________________________________

    def test_calc():
>       assert calculate_tax(100) == 15
E       AssertionError: assert 10 == 15

services/backend/tests/test_sample.py:42: AssertionError
FAILED services/backend/tests/test_sample.py::test_calc - AssertionError: assert 10 == 15
=========================== 1 failed in 0.22s ===========================
"""
    diag = parser.parse(pytest_sample)
    assert diag is not None
    assert diag.runner == "pytest"
    assert "test_sample.py" in diag.failing_file
    assert diag.test_name == "test_calc"
    assert "AssertionError" in diag.error_type
    assert "assert 10 == 15" in diag.error_message

    # TypeScript compiler error trace
    tsc_sample = "apps/desktop/src/components/MyComponent.tsx(24,15): error TS2304: Cannot find name 'foo'."
    diag_tsc = parser.parse(tsc_sample)
    assert diag_tsc is not None
    assert diag_tsc.runner == "tsc"
    assert "MyComponent.tsx" in diag_tsc.failing_file
    assert diag_tsc.line_number == 24
    assert diag_tsc.error_type == "TS2304"
    assert "Cannot find name 'foo'" in diag_tsc.error_message


# ==========================================
# 3. Test Runner Daemon Execution Tests
# ==========================================

@pytest.mark.asyncio
async def test_test_runner_daemon_pytest():
    daemon = TestRunnerDaemon()
    
    # Run a fast existing test file
    res = await daemon.run_pytest(
        target_path="services/backend/tests/test_code_intelligence_ast_indexer.py",
        timeout_seconds=30
    )
    assert res.runner == "pytest"
    assert res.status == "passed"
    assert res.passed_tests >= 5
    assert res.failed_tests == 0
    assert res.duration_ms > 0.0


# ==========================================
# 4. Self-Healing Mission Agent Tests
# ==========================================

@pytest.mark.asyncio
async def test_self_healing_mission_agent_success(tmp_path):
    agent = DiagnosticMissionAgent()

    # Setup mini test sandbox environment
    mgr = WorktreeManager(repo_root=str(tmp_path))
    # Replace global worktree_manager's base dir with temporary path for isolated testing
    orig_base = agent
    
    # Create a small failing test file and source file
    src_dir = tmp_path / "pkg"
    src_dir.mkdir(parents=True)
    src_file = src_dir / "math_mod.py"
    src_file.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

    test_file = tmp_path / "test_mini.py"
    test_file.write_text(
        "from pkg.math_mod import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8"
    )

    # Run mission with replacement patch
    req = MissionRequest(
        test_path=str(test_file),
        target_file=str(src_file),
        search_target="return a - b",
        replacement_target="return a + b"
    )

    # Direct agent execution on test
    report = await agent.execute_mission(req)
    assert report.mission_id.startswith("mission_")
    assert report.verified_pass is True
    assert report.status == "healed"
    assert "-    return a - b" in report.patch_diff
    assert "+    return a + b" in report.patch_diff


@pytest.mark.asyncio
async def test_self_healing_mission_agent_rollback_on_failure(tmp_path):
    agent = DiagnosticMissionAgent()

    src_dir = tmp_path / "pkg"
    src_dir.mkdir(parents=True)
    src_file = src_dir / "math_mod.py"
    src_file.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

    test_file = tmp_path / "test_mini_fail.py"
    test_file.write_text(
        "from pkg.math_mod import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8"
    )

    # Propose an incorrect patch
    req = MissionRequest(
        test_path=str(test_file),
        target_file=str(src_file),
        search_target="return a - b",
        replacement_target="return a * b"  # 2 * 3 = 6 != 5
    )

    report = await agent.execute_mission(req)
    assert report.verified_pass is False
    assert report.status == "rolled_back"


# ==========================================
# 5. Tool Registration & Safety Invariant Tests
# ==========================================

def test_diagnostic_tools_registration():
    expected_tools = [
        ("create_worktree_sandbox", 1),
        ("remove_worktree_sandbox", 1),
        ("run_isolated_tests", 1),
        ("diagnose_and_heal_failure", 2),
        ("prune_worktrees", 1),
    ]

    for tool_name, expected_tier in expected_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered in ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch: expected {expected_tier}, got {tool_def.tier}"
        assert tool_def.preview_fn is not None
        assert callable(tool_def.preview_fn)

    # Test preview string generation
    create_preview = registry.get("create_worktree_sandbox").preview_fn({"commit_ish": "HEAD", "sandbox_id": "wt_123"})
    assert "Create isolated git worktree sandbox 'wt_123'" in create_preview

    heal_preview = registry.get("diagnose_and_heal_failure").preview_fn({"test_path": "tests/test_auth.py", "target_file": "auth.py"})
    assert "tests/test_auth.py" in heal_preview
    assert "auth.py" in heal_preview


# ==========================================
# 6. Universal Guardian Kill Switch SLA Benchmark
# ==========================================

def test_guardian_kill_switch_sla():
    guardian.resume()
    latencies = []

    # Benchmark SLA check latency over 50 iterations
    for _ in range(50):
        t0 = time.perf_counter()
        _ = guardian.is_halted
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    max_latency = max(latencies)
    avg_latency = sum(latencies) / len(latencies)

    print(f"\n[Guardian SLA Phase 2 Benchmark] Max: {max_latency:.4f}ms | Avg: {avg_latency:.4f}ms | SLA Target: < 25.0ms")
    assert max_latency < 25.0, f"Guardian SLA breached: max latency {max_latency:.4f}ms exceeds 25.0ms threshold"

    # Trigger halt and verify synchronous block
    guardian.trigger(reason="Emergency test stop")
    assert guardian.is_halted is True

    mgr = WorktreeManager()
    with pytest.raises(PermissionError, match="halted"):
        mgr.create_worktree()

    with pytest.raises(PermissionError, match="halted"):
        mgr.remove_worktree("wt_fake")

    # Resume kill switch
    guardian.resume()
    assert guardian.is_halted is False
