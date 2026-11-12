"""
Automated Verification Suite for Phase 2: Proactive Dev Build Sentinel & Patch Fix Drafter (DEV-02).
Tests traceback parsing across multiple runners, unified diff patch synthesis,
atomic git stash pre-patch snapshots, 1-click rollback, Obsidian debug journaling,
ToolRegistry wrappers, and Guardian kill switch halt SLA.
"""

import os
import subprocess
import tempfile
import time
from unittest.mock import patch
import pytest

from services.backend.coding.traceback_parser import TracebackParser, BuildFailureDiagnostic
from services.backend.coding.patch_drafter import PatchDrafter, patch_drafter
from services.backend.coding.build_sentinel import BuildSentinel, build_sentinel
from services.backend.safety.registry import registry
from services.backend.proactive.dispatcher import proactive_dispatcher
import services.backend.tools.coding_tools  # noqa: F401


# ==========================================
# 1. Traceback Parser Unit Tests
# ==========================================

def test_traceback_parser():
    """Verify parsing across pytest, vitest, tsc, cargo, and python exceptions."""
    parser = TracebackParser()

    # 1. Pytest failure
    pytest_log = """
============================= test session starts =============================
collected 3 items
test_app.py .F.
================================== FAILURES ===================================
__________________________________ test_auth __________________________________
FAILED services/backend/tests/test_auth.py::test_auth_token_refresh - AssertionError: assert 401 == 200
=========================== short test summary info ===========================
"""
    d1 = parser.parse(pytest_log)
    assert d1 is not None
    assert d1.runner == "pytest"
    assert "test_auth.py" in d1.failing_file
    assert d1.test_name == "test_auth_token_refresh"
    assert d1.error_type == "AssertionError"
    assert "401 == 200" in d1.error_message

    # 2. Vitest failure
    vitest_log = """
FAIL src/components/HeaderBar.test.tsx > HeaderBar > renders status badge
Error: expect(received).toBe(expected) // Object.is equality
Expected: "ONLINE"
Received: "OFFLINE"
"""
    d2 = parser.parse(vitest_log)
    assert d2 is not None
    assert d2.runner == "vitest"
    assert "HeaderBar.test.tsx" in d2.failing_file
    assert "renders status badge" in (d2.test_name or "")
    assert "expect(received).toBe(expected)" in d2.error_message

    # 3. TypeScript compilation error
    tsc_log = "src/App.tsx(378,29): error TS2304: Cannot find name 'data'."
    d3 = parser.parse(tsc_log)
    assert d3 is not None
    assert d3.runner == "tsc"
    assert d3.failing_file == "src/App.tsx"
    assert d3.line_number == 378
    assert d3.error_type == "TS2304"
    assert "Cannot find name 'data'" in d3.error_message

    # 4. Cargo error
    cargo_log = """
error[E0425]: cannot find value `unresolved_var` in this scope
  --> src/main.rs:42:13
"""
    d4 = parser.parse(cargo_log)
    assert d4 is not None
    assert d4.runner == "cargo"
    assert d4.failing_file == "src/main.rs"
    assert d4.line_number == 42
    assert d4.error_type == "error[E0425]"

    # 5. Python traceback
    py_log = """
Traceback (most recent call last):
  File "C:\\Phenom\\main.py", line 124, in handle_request
    raise ValueError("Invalid request payload")
ValueError: Invalid request payload
"""
    d5 = parser.parse(py_log)
    assert d5 is not None
    assert d5.runner == "python"
    assert "main.py" in d5.failing_file
    assert d5.line_number == 124
    assert d5.error_type == "ValueError"
    assert "Invalid request payload" in d5.error_message


# ==========================================
# 2. Patch Synthesis Tests
# ==========================================

def test_patch_drafter():
    """Verify minimal unified diff generation and patch check."""
    drafter = PatchDrafter()

    orig = "def add(a, b):\n    return a - b\n"
    fixed = "def add(a, b):\n    return a + b\n"

    diff = drafter.create_unified_diff("math_util.py", orig, fixed)
    assert "--- a/math_util.py" in diff
    assert "+++ b/math_util.py" in diff
    assert "-    return a - b" in diff
    assert "+    return a + b" in diff


# ==========================================
# 3. Atomic Rollback & Pre-Patch Snapshot Tests
# ==========================================

def test_patch_rollback():
    """Verify non-destructive git stash create snapshot and 1-click rollback."""
    drafter = PatchDrafter()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize temp git repo
        subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "TestUser"], cwd=tmpdir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmpdir, check=True)

        target_file = os.path.join(tmpdir, "calc.py")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("def calculate():\n    return 10\n")

        subprocess.run(["git", "add", "calc.py"], cwd=tmpdir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmpdir, check=True)

        # Developer makes an uncommitted change
        uncommitted_content = "def calculate():\n    return 10\n# Developer WIP uncommitted note\n"
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(uncommitted_content)

        # Drafter prepares patch modifying calculate return value
        fixed_content = "def calculate():\n    return 20\n# Developer WIP uncommitted note\n"
        patch_diff = drafter.create_unified_diff(
            "calc.py",
            uncommitted_content,
            fixed_content,
        )

        # Apply patch with pre-patch snapshot
        success, rollback_token, err = drafter.apply_patch(tmpdir, patch_diff)
        assert success is True, f"apply_patch failed: {err}"
        assert rollback_token is not None

        # Verify patch applied
        with open(target_file, "r", encoding="utf-8") as f:
            patched_content = f.read()
        assert "return 20" in patched_content

        # Revert patch using rollback token
        revert_success = drafter.revert_patch(tmpdir, rollback_token)
        assert revert_success is True

        # Verify exact uncommitted state restored
        with open(target_file, "r", encoding="utf-8") as f:
            restored_content = f.read()
        assert "return 10" in restored_content
        assert "# Developer WIP uncommitted note" in restored_content


# ==========================================
# 4. Proactive Cyber HUD & Obsidian Sync Tests
# ==========================================

def test_hud_and_obsidian_sync():
    """Verify proactive Cyber HUD card dispatch and Obsidian debug journal writing."""
    with tempfile.TemporaryDirectory() as tmp_vault:
        sentinel = BuildSentinel(vault_root=tmp_vault, failure_cooldown_seconds=1.0)

        diag = BuildFailureDiagnostic(
            runner="pytest",
            failing_file="services/backend/tests/test_foo.py",
            line_number=45,
            test_name="test_foo_calculation",
            error_type="AssertionError",
            error_message="assert 5 == 10",
        )

        # Test Obsidian logging
        log_success = sentinel.log_resolution_to_obsidian(
            workspace_path="C:\\Phenom",
            diagnostic=diag,
            resolution="Corrected calculation factor in math.py",
            rollback_token="mock_sha_12345",
        )
        assert log_success is True

        # Verify journal note was created
        journal_path = os.path.join(tmp_vault, "Projects", "Phenom.md")
        assert os.path.exists(journal_path)

        with open(journal_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "## Build & Test Debug Journal" in content
        assert "test_foo_calculation" in content
        assert "Corrected calculation factor" in content
        assert "mock_sha_12345" in content

        # Test proactive card dispatching
        with patch.object(sentinel, "_broadcast_proactive_failure_card") as mock_broadcast:
            sentinel.diagnose_output("FAILED tests/test_bar.py::test_bar - AssertionError: assert False")
            assert mock_broadcast.called
            call_diag = mock_broadcast.call_args[0][0]
            assert call_diag.runner == "pytest"
            assert "test_bar" in (call_diag.test_name or "")


# ==========================================
# 5. ToolRegistry & Guardian Kill Switch Tests
# ==========================================

def test_tools_and_guardian():
    """Verify safety tool registration, risk tiers, and Guardian halt SLA (< 25ms)."""
    # 1. ToolRegistry verification
    tool_diagnose = registry.get("coding_diagnose_build_failure")
    assert tool_diagnose is not None
    assert tool_diagnose.tier == 0

    tool_draft = registry.get("coding_draft_patch")
    assert tool_draft is not None
    assert tool_draft.tier == 0

    tool_apply = registry.get("coding_apply_patch")
    assert tool_apply is not None
    assert tool_apply.tier == 1

    tool_revert = registry.get("coding_revert_patch")
    assert tool_revert is not None
    assert tool_revert.tier == 1

    # 2. Guardian halt latency benchmark (< 25ms SLA)
    sentinel = BuildSentinel()
    assert sentinel.is_halted is False

    t0 = time.perf_counter()
    sentinel.halt()
    halt_duration_ms = (time.perf_counter() - t0) * 1000.0

    assert sentinel.is_halted is True
    assert halt_duration_ms < 25.0, f"Halt exceeded 25ms SLA: {halt_duration_ms:.3f} ms"

    # Operation rejected when halted
    assert sentinel.diagnose_output("FAILED test.py::test_fail - Error: fail") is None
    success, _, err = sentinel.apply_patch_fix("diff")
    assert success is False
    assert "halted" in str(err)

    # Resume restores functionality
    sentinel.reset()
    assert sentinel.is_halted is False
