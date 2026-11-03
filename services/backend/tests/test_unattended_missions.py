"""
Unit tests for Phenom Sovereign Unattended Overnight Missions Runner (MIS-01).
Verifies:
1. Isolated git worktree sandbox creation without touching primary working tree.
2. Multi-iteration self-healing loop (failing test -> diagnosis -> patch applied -> tests pass).
3. Max iterations fallback when test cannot be healed.
4. Subprocess timeout enforcement.
5. Worktree cleanup and Windows readonly directory removal.
6. Guardian halt permission error enforcement.
"""

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import pytest

from services.backend.missions.unattended_runner import (
    UnattendedMissionRunner,
    _clear_readonly,
)
from services.backend.schemas.missions import (
    MissionExecutionPlan,
    MissionStatus,
)


def _init_dummy_git_repo(repo_dir: str):
    """Initializes a temporary git repository with initial commit."""
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "PhenomTest"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "phenom@example.com"], cwd=repo_dir, check=True, capture_output=True)

    dummy_file = os.path.join(repo_dir, "app.py")
    with open(dummy_file, "w", encoding="utf-8") as f:
        f.write("def solve():\n    return False\n")

    test_file = os.path.join(repo_dir, "test_app.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("from app import solve\ndef test_solve():\n    assert solve() is True\n")

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)


@pytest.fixture
def temp_repo():
    """Creates a temporary git repository for testing isolated worktree missions."""
    d = tempfile.mkdtemp(prefix="phenom_test_repo_")
    _init_dummy_git_repo(d)
    yield d
    try:
        shutil.rmtree(d, onerror=_clear_readonly)
    except Exception:
        pass


def test_worktree_sandbox_isolation(temp_repo):
    """Verifies sandbox worktree creation on a fresh branch leaving main working tree untouched."""
    runner = UnattendedMissionRunner()

    # Modify primary working tree with uncommitted change
    main_uncommitted = os.path.join(temp_repo, "uncommitted.txt")
    with open(main_uncommitted, "w", encoding="utf-8") as f:
        f.write("Developer WIP work")

    mission_id = "test_iso_001"
    worktree_path, branch_name, base_sha = runner.create_sandbox(mission_id, temp_repo)

    try:
        assert os.path.exists(worktree_path)
        assert branch_name == f"mission/{mission_id}"
        assert len(base_sha) == 40

        # Invariant: Developer's uncommitted file in main repo remains untouched
        assert os.path.exists(main_uncommitted)
        with open(main_uncommitted, "r", encoding="utf-8") as f:
            assert f.read() == "Developer WIP work"

        # Invariant: Sandbox has its own clean git HEAD matching base_sha
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )
        assert res.stdout.strip() == base_sha
    finally:
        runner.cleanup_sandbox(mission_id, temp_repo, branch_name)
        assert not os.path.exists(worktree_path)


def test_self_healing_test_loop_success(temp_repo):
    """Verifies that failing tests in sandbox are diagnosed, healed via patch, and committed."""
    runner = UnattendedMissionRunner()
    mission_id = "test_heal_001"

    plan = MissionExecutionPlan(
        mission_id=mission_id,
        title="Fix solve return value",
        prompt="Fix solve to return True",
        repo_path=temp_repo,
        test_command="pytest test_app.py",
        max_iterations=3,
        timeout_seconds=30,
    )

    result = runner.run_mission(plan)

    assert result.status == MissionStatus.COMPLETED
    assert result.tests_fixed >= 1
    assert result.tests_passed >= 1
    assert len(result.iterations) == 2  # Iteration 1 fails, Iteration 2 passes
    assert result.iterations[0].passed is False
    assert result.iterations[1].passed is True
    assert result.lines_added > 0 or result.lines_deleted > 0

    # Ensure main repo app.py remains UNTOUCHED
    with open(os.path.join(temp_repo, "app.py"), "r", encoding="utf-8") as f:
        main_content = f.read()
    assert "return False" in main_content

    # Clean up sandbox
    runner.cleanup_sandbox(mission_id, temp_repo)


def test_max_iterations_exhaustion(temp_repo):
    """Verifies graceful fallback when test cannot be healed within max iterations."""
    runner = UnattendedMissionRunner()
    mission_id = "test_exhaust_001"

    # Add an unhealable test
    unhealable = os.path.join(temp_repo, "test_unhealable.py")
    with open(unhealable, "w", encoding="utf-8") as f:
        f.write("def test_impossible():\n    raise RuntimeError('Complex unhealable issue')\n")
    subprocess.run(["git", "add", "."], cwd=temp_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add impossible test"], cwd=temp_repo, check=True)

    plan = MissionExecutionPlan(
        mission_id=mission_id,
        title="Attempt impossible healing",
        prompt="Cannot be healed",
        repo_path=temp_repo,
        test_command="pytest test_unhealable.py",
        max_iterations=2,
        timeout_seconds=15,
    )

    result = runner.run_mission(plan)

    assert result.status == MissionStatus.FAILED
    assert len(result.iterations) == 2
    assert all(not it.passed for it in result.iterations)
    assert "exhausted after 2 iterations" in result.diagnostic_log

    runner.cleanup_sandbox(mission_id, temp_repo)


def test_subprocess_timeout_enforcement(temp_repo):
    """Verifies that hanging test commands are terminated after timeout_seconds."""
    runner = UnattendedMissionRunner()
    mission_id = "test_timeout_001"

    # Test that sleeps forever
    hang_test = os.path.join(temp_repo, "test_hang.py")
    with open(hang_test, "w", encoding="utf-8") as f:
        f.write("import time\ndef test_hang():\n    time.sleep(100)\n")
    subprocess.run(["git", "add", "."], cwd=temp_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add hanging test"], cwd=temp_repo, check=True)

    plan = MissionExecutionPlan(
        mission_id=mission_id,
        title="Test timeout enforcement",
        prompt="Run hanging test",
        repo_path=temp_repo,
        test_command="pytest test_hang.py",
        max_iterations=1,
        timeout_seconds=2,  # Strict 2s timeout
    )

    t0 = time.time()
    result = runner.run_mission(plan)
    duration = time.time() - t0

    assert duration < 10.0  # Finished within reasonable margin of 2s timeout
    assert result.status == MissionStatus.FAILED
    assert "TIMEOUT" in result.diagnostic_log or "exceeded" in result.diagnostic_log

    runner.cleanup_sandbox(mission_id, temp_repo)


def test_guardian_halt_enforcement(temp_repo):
    """Verifies that runner halted state rejects new missions with PermissionError."""
    runner = UnattendedMissionRunner()
    runner.halt()
    assert runner.is_halted is True

    plan = MissionExecutionPlan(
        mission_id="test_halt_001",
        title="Should not run",
        prompt="Halt test",
        repo_path=temp_repo,
        test_command="pytest",
    )

    with pytest.raises(PermissionError) as exc_info:
        runner.run_mission(plan)
    assert "HALTED by Guardian" in str(exc_info.value)

    # Resume
    runner.reset()
    assert runner.is_halted is False
