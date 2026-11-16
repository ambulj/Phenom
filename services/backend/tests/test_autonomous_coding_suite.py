"""
Comprehensive Unit Test Battery for Phase 47-02:
Autonomous Coding Workspace Engine, In-Memory AST Validation & Rollback-Capable Diff Generator.
Verifies requirements: EXEC-01, EXEC-02, EXEC-03.
"""

import os
import sys
import shutil
import tempfile
import time
import zipfile
import pytest

from services.backend.coding.workspace_cloner import (
    WorkspaceCloner,
    IsolatedWorkspaceContext,
    workspace_cloner
)
from services.backend.coding.ast_validator import (
    ASTValidator,
    ASTValidationResult,
    ast_validator
)
from services.backend.coding.test_runner import (
    WorkspaceTestRunner,
    TestExecutionResult,
    workspace_test_runner
)
from services.backend.coding.diff_engine import (
    WorkspaceDiffEngine,
    WorkspaceDiffReport,
    ApplyResult,
    workspace_diff_engine
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.autonomous_coding_tools as coding_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    """Ensure Guardian kill switch is reset before and after each test."""
    guardian.resume()
    yield
    guardian.resume()


# ============================================================================
# 1. Isolated Workspace Cloning & Invariant Verification (EXEC-01)
# ============================================================================

def test_workspace_cloner_isolation_and_snapshot():
    """
    Verifies that target project is cloned to .workspaces,
    original files remain 100% untouched when workspace is modified,
    and pre-execution snapshot zip is preserved.
    """
    with tempfile.TemporaryDirectory() as temp_root:
        orig_proj = os.path.join(temp_root, "my_repo")
        os.makedirs(orig_proj, exist_ok=True)

        # Create source files and ignored directory
        file1 = os.path.join(orig_proj, "main.py")
        with open(file1, "w", encoding="utf-8") as f:
            f.write("def run():\n    return 'original'\n")

        file2 = os.path.join(orig_proj, "config.json")
        with open(file2, "w", encoding="utf-8") as f:
            f.write('{"mode": "prod"}')

        ignored_dir = os.path.join(orig_proj, ".git")
        os.makedirs(ignored_dir, exist_ok=True)
        with open(os.path.join(ignored_dir, "HEAD"), "w", encoding="utf-8") as f:
            f.write("ref: refs/heads/main\n")

        # Custom workspaces root
        ws_root = os.path.join(temp_root, "workspaces_sandbox")
        cloner = WorkspaceCloner(workspaces_root=ws_root)

        ctx = cloner.clone_project(orig_proj, task_name="fix_bug_123")
        assert os.path.exists(ctx.isolated_workspace_path)
        assert os.path.exists(ctx.snapshot_path)
        assert zipfile.is_zipfile(ctx.snapshot_path)

        # Verify ignored folder was NOT copied to isolated workspace
        assert not os.path.exists(os.path.join(ctx.isolated_workspace_path, ".git"))

        # Modify files in isolated workspace
        ws_file1 = os.path.join(ctx.isolated_workspace_path, "main.py")
        with open(ws_file1, "w", encoding="utf-8") as f:
            f.write("def run():\n    return 'healed_bug'\n")

        # Assert original project file is 100% untouched
        with open(file1, "r", encoding="utf-8") as f:
            assert f.read() == "def run():\n    return 'original'\n"

        # Cleanup workspace
        assert cloner.cleanup_workspace(ctx.workspace_id) is True
        assert not os.path.exists(ctx.isolated_workspace_path)


# ============================================================================
# 2. In-Memory AST Syntax Validation (EXEC-02)
# ============================================================================

def test_ast_validator_python_syntax():
    """Verifies that Python AST validator catches syntax errors and accepts clean code."""
    validator = ASTValidator()

    # Valid Python code
    clean_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    res_clean = validator.validate_code(clean_code, language="python")
    assert res_clean.valid is True
    assert res_clean.error_message is None

    # Broken Python code (missing colon / syntax error)
    broken_code = "def broken(a, b\n    return a + b\n"
    res_broken = validator.validate_code(broken_code, language="python")
    assert res_broken.valid is False
    assert res_broken.line is not None
    assert res_broken.error_message is not None


def test_ast_validator_js_ts_syntax():
    """Verifies that JS/TS validator catches unclosed delimiters and mismatched brackets."""
    validator = ASTValidator()

    clean_ts = "function calculateTotal(price: number): number {\n    return price * 1.05;\n}\n"
    res_clean = validator.validate_code(clean_ts, language="typescript")
    assert res_clean.valid is True

    # Broken TS (unclosed brace)
    broken_ts = "function calculateTotal(price: number): number {\n    return price * 1.05;\n"
    res_broken = validator.validate_code(broken_ts, language="typescript")
    assert res_broken.valid is False
    assert "Unclosed" in res_broken.error_message or "Mismatched" in res_broken.error_message

    # Mismatched bracket
    mismatched = "const arr = [1, 2, 3};\n"
    res_mismatch = validator.validate_code(mismatched, language="javascript")
    assert res_mismatch.valid is False


def test_ast_validator_json_syntax():
    """Verifies JSON syntax validation."""
    validator = ASTValidator()

    clean_json = '{"name": "phenom", "version": 47}'
    assert validator.validate_code(clean_json, language="json").valid is True

    broken_json = '{"name": "phenom", "version": 47,}'
    res = validator.validate_code(broken_json, language="json")
    assert res.valid is False
    assert res.line is not None


# ============================================================================
# 3. Workspace Test Runner & Traceback Parsing (EXEC-02)
# ============================================================================

def test_workspace_test_runner_execution_and_parsing():
    """
    Creates an isolated workspace with real pytest tests (one passing, one failing)
    and verifies that test counts and traceback snippets are parsed.
    """
    with tempfile.TemporaryDirectory() as ws_dir:
        test_file = os.path.join(ws_dir, "test_sample.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(
                "def test_success():\n"
                "    assert 1 + 1 == 2\n\n"
                "def test_failure():\n"
                "    assert 1 + 1 == 99\n"
            )

        runner = WorkspaceTestRunner()
        res = runner.run_tests(ws_dir, framework="pytest", timeout_seconds=30)

        assert res.success is False
        assert res.exit_code != 0
        assert res.passed_count == 1
        assert res.failed_count == 1
        assert res.duration_seconds > 0.0
        assert res.error_traceback is not None
        assert "assert 1 + 1 == 99" in res.error_traceback or "assert 2 == 99" in res.error_traceback


def test_workspace_test_runner_guardian_kill_switch():
    """Verifies that Guardian halt prevents test execution."""
    guardian.trigger()
    runner = WorkspaceTestRunner()
    res = runner.run_tests("C:/Phenom", framework="pytest")
    assert res.success is False
    assert res.exit_code == -99
    assert "Guardian kill switch is active" in res.error_traceback


# ============================================================================
# 4. Rollback-Capable Diff Engine & Atomic Merge (EXEC-03)
# ============================================================================

def test_diff_engine_computation():
    """Verifies computation of unified diffs across modified, added, and deleted files."""
    with tempfile.TemporaryDirectory() as temp_root:
        orig = os.path.join(temp_root, "orig")
        work = os.path.join(temp_root, "work")
        os.makedirs(orig, exist_ok=True)
        os.makedirs(work, exist_ok=True)

        # File 1: Modified
        with open(os.path.join(orig, "f1.txt"), "w", encoding="utf-8") as f:
            f.write("Line 1\nLine 2\n")
        with open(os.path.join(work, "f1.txt"), "w", encoding="utf-8") as f:
            f.write("Line 1\nLine 2 Modified\nLine 3 Added\n")

        # File 2: Added in work
        with open(os.path.join(work, "new_file.txt"), "w", encoding="utf-8") as f:
            f.write("Brand new content\n")

        # File 3: Deleted from work
        with open(os.path.join(orig, "old_file.txt"), "w", encoding="utf-8") as f:
            f.write("To be deleted\n")

        engine = WorkspaceDiffEngine(snapshots_dir=os.path.join(temp_root, "snapshots"))
        report = engine.compute_diff(orig, work)

        assert report.total_files_changed == 3
        assert report.total_additions >= 2
        assert report.total_deletions >= 1

        statuses = {d.path: d.status for d in report.file_diffs}
        assert statuses.get("f1.txt") == "modified"
        assert statuses.get("new_file.txt") == "added"
        assert statuses.get("old_file.txt") == "deleted"


def test_diff_engine_apply_and_atomic_rollback():
    """Verifies safe application of diffs with pre-apply snapshot and clean rollback."""
    with tempfile.TemporaryDirectory() as temp_root:
        orig = os.path.join(temp_root, "orig")
        work = os.path.join(temp_root, "work")
        snapshots_dir = os.path.join(temp_root, "snapshots")
        os.makedirs(orig, exist_ok=True)
        os.makedirs(work, exist_ok=True)

        # Base file
        f_path = os.path.join(orig, "code.py")
        with open(f_path, "w", encoding="utf-8") as f:
            f.write("version = 1.0\n")

        # Modified file in workspace
        f_work = os.path.join(work, "code.py")
        with open(f_work, "w", encoding="utf-8") as f:
            f.write("version = 2.0\n")

        engine = WorkspaceDiffEngine(snapshots_dir=snapshots_dir)

        # Apply diff
        res = engine.apply_diff(orig, work, create_backup=True)
        assert res.success is True
        assert res.rollback_snapshot_path is not None
        assert os.path.exists(res.rollback_snapshot_path)

        # Check original file updated
        with open(f_path, "r", encoding="utf-8") as f:
            assert f.read() == "version = 2.0\n"

        # Test Rollback
        rollback_ok = engine.rollback_from_snapshot(res.rollback_snapshot_path, orig)
        assert rollback_ok is True
        with open(f_path, "r", encoding="utf-8") as f:
            assert f.read() == "version = 1.0\n"


# ============================================================================
# 5. Tool Registry Integration & Safety Tiers (EXEC-01, EXEC-02, EXEC-03)
# ============================================================================

def test_autonomous_coding_tools_registry():
    """Verifies that all 4 autonomous coding tools are registered with strict safety tiers."""
    tool_names = [
        "clone_isolated_workspace",
        "validate_ast_syntax",
        "run_workspace_tests",
        "apply_workspace_diff"
    ]

    for name in tool_names:
        tool_def = registry.get(name)
        assert tool_def is not None, f"Tool '{name}' must be registered"
        assert callable(tool_def.preview_fn)
        assert tool_def.args_schema is not None

    # Tier invariants
    assert registry.get("validate_ast_syntax").tier == 0  # Read-only
    assert registry.get("clone_isolated_workspace").tier == 1  # Reversible
    assert registry.get("run_workspace_tests").tier == 1  # Reversible / sandboxed
    assert registry.get("apply_workspace_diff").tier == 2  # Confirmation required

    # Execute validate_ast_syntax through tool handler
    res = coding_tools.handle_validate_ast_syntax(code="x = 10\n", language="python")
    assert res["valid"] is True
