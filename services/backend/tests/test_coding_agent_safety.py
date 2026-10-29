"""
Unit Tests for Phenom Coding Agent Safety Architecture (Task 7i)
Covers:
1. Workspace isolation, snapshot creation, and proof of pristine original project.
2. Diff generation and confirmed application with secondary rollback snapshot.
3. 20/20 typosquat attack corpus detection and warning banners.
4. Hard runtime constraints, network isolation, and Guardian kill switch process-tree termination.
5. Safety tool registry integration and risk tiers.
"""

import os
import sys
import time
import zipfile
import pytest
import tempfile
import shutil

from services.backend.coding.workspace import WorkspaceManager, IsolatedWorkspace
from services.backend.coding.typosquat_guard import TyposquatGuard, typosquat_guard
from services.backend.coding.runner import CodeRunner, ExecutionResult
from services.backend.safety.guardian import GuardianKillSwitch
from services.backend.safety.registry import registry
import services.backend.tools.coding_tools

@pytest.fixture
def temp_project(tmp_path):
    """Creates a temporary project with sample files."""
    proj_dir = tmp_path / "sample_project"
    proj_dir.mkdir()
    
    (proj_dir / "main.py").write_text("print('hello world')\n", encoding="utf-8")
    (proj_dir / "utils.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (proj_dir / "README.md").write_text("# Sample Project\nInitial readme.\n", encoding="utf-8")
    
    return str(proj_dir)

@pytest.fixture
def workspace_mgr(tmp_path):
    """Creates a WorkspaceManager backed by a temporary workspaces root."""
    ws_root = tmp_path / "workspaces"
    ws_root.mkdir()
    return WorkspaceManager(workspaces_root=str(ws_root))

# ==============================================================================
# 1. Workspace Isolation & Snapshot Tests
# ==============================================================================

def test_workspace_isolation_and_snapshot(temp_project, workspace_mgr):
    """Verifies isolated copy is created, snapshot exists, and original is pristine."""
    orig_main = os.path.join(temp_project, "main.py")
    orig_mtime = os.path.getmtime(orig_main)

    ws = workspace_mgr.create_isolated_workspace(temp_project)

    assert os.path.exists(ws.isolated_workspace_path)
    assert os.path.exists(ws.snapshot_path)
    assert zipfile.is_zipfile(ws.snapshot_path)

    # Modify file in isolated workspace
    iso_main = os.path.join(ws.isolated_workspace_path, "main.py")
    with open(iso_main, "w", encoding="utf-8") as f:
        f.write("print('hello from isolated workspace')\n")

    # Add a new file in isolated workspace
    iso_new = os.path.join(ws.isolated_workspace_path, "new_feature.py")
    with open(iso_new, "w", encoding="utf-8") as f:
        f.write("# New feature\n")

    # Verify original project directory is 100% UNTOUCHED
    assert workspace_mgr.verify_original_untouched(ws) is True
    with open(orig_main, "r", encoding="utf-8") as f:
        assert f.read() == "print('hello world')\n"
    assert os.path.getmtime(orig_main) == orig_mtime
    assert not os.path.exists(os.path.join(temp_project, "new_feature.py"))

def test_workspace_diff_and_apply_flow(temp_project, workspace_mgr):
    """Verifies diff generation and confirmed application of changes."""
    ws = workspace_mgr.create_isolated_workspace(temp_project)

    # Modify utils.py in workspace
    iso_utils = os.path.join(ws.isolated_workspace_path, "utils.py")
    with open(iso_utils, "a", encoding="utf-8") as f:
        f.write("def sub(a, b):\n    return a - b\n")

    # Delete README.md in workspace
    iso_readme = os.path.join(ws.isolated_workspace_path, "README.md")
    os.remove(iso_readme)

    # Add config.json in workspace
    iso_config = os.path.join(ws.isolated_workspace_path, "config.json")
    with open(iso_config, "w", encoding="utf-8") as f:
        f.write('{"debug": true}\n')

    # Get diff
    diff_report = workspace_mgr.get_diff(ws)
    assert "utils.py" in diff_report["files_modified"]
    assert "README.md" in diff_report["files_deleted"]
    assert "config.json" in diff_report["files_added"]
    assert diff_report["total_changes"] == 3
    assert "def sub(a, b):" in diff_report["diff_text"]

    # Unconfirmed apply must fail
    with pytest.raises(PermissionError):
        workspace_mgr.apply_to_original(ws, confirmed=False)

    # Confirmed apply succeeds
    res = workspace_mgr.apply_to_original(ws, confirmed=True)
    assert res["status"] == "applied"
    assert res["applied_changes"] == 3
    assert os.path.exists(res["rollback_snapshot"])

    # Verify original project directory now has the changes
    orig_utils = os.path.join(temp_project, "utils.py")
    with open(orig_utils, "r", encoding="utf-8") as f:
        assert "def sub(a, b):" in f.read()
    assert not os.path.exists(os.path.join(temp_project, "README.md"))
    assert os.path.exists(os.path.join(temp_project, "config.json"))

# ==============================================================================
# 2. Typosquatting Protection 20/20 Corpus Tests
# ==============================================================================

def test_legitimate_packages_are_safe():
    """Legitimate popular packages must not be flagged as typosquatting."""
    legit_packages = ["requests", "numpy", "torch", "fastapi", "flask", "cryptography", "pytest"]
    for pkg in legit_packages:
        report = typosquat_guard.evaluate_package(pkg)
        assert report.is_suspicious is False, f"Legitimate package '{pkg}' falsely flagged!"

def test_typosquatting_20_corpus_detection():
    """Tests the exact 20-corpus typosquat attack strings from PLAN_NEXT.md."""
    corpus = [
        "reqeusts",            # 1. requests (transposition)
        "colourama",           # 2. colorama (insertion)
        "py-torch",            # 3. torch (prefix)
        "cryptography-v2",     # 4. cryptography (suffix)
        "fast-api",            # 5. fastapi (hyphenation)
        "pydantic-core-fast",  # 6. pydantic-core (suffix)
        "python-dateutil-lib", # 7. python-dateutil (suffix)
        "urlib3",              # 8. urllib3 (deletion)
        "beautifulsoup",       # 9. beautifulsoup4 (truncation)
        "numpy-tools",         # 10. numpy (suffix)
        "pandas-data",         # 11. pandas (suffix)
        "scikit",              # 12. scikit-learn (truncation)
        "flaks",               # 13. flask (transposition)
        "async-io",            # 14. asyncio (hyphenation)
        "websockets-client",   # 15. websockets (suffix)
        "ps-util",             # 16. psutil (hyphenation)
        "pillow-imaging",      # 17. pillow (suffix)
        "open-cv",             # 18. opencv (hyphenation)
        "report-lab",          # 19. reportlab (hyphenation)
        "docx-python"          # 20. python-docx (token inversion)
    ]

    flagged_count = 0
    for attack_str in corpus:
        report = typosquat_guard.evaluate_package(attack_str)
        assert report.is_suspicious is True, f"Attack string '{attack_str}' was NOT flagged!"
        assert report.target_popular_package is not None
        assert report.warning_banner is not None
        assert f"Warning: '{attack_str}' is within edit distance of popular package" in report.warning_banner
        flagged_count += 1

    assert flagged_count == 20

# ==============================================================================
# 3. Execution Constraints & Guardian Process-Tree SIGKILL
# ==============================================================================

def test_code_runner_normal_execution(tmp_path):
    """Executes a standard command and captures outputs."""
    runner = CodeRunner()
    res = runner.execute_in_workspace(
        command=[sys.executable, "-c", "print('hello isolated execution')"],
        cwd=str(tmp_path),
        allow_network=False
    )
    assert res.exit_code == 0
    assert "hello isolated execution" in res.stdout
    assert res.timed_out is False
    assert res.killed_by_guardian is False

def test_code_runner_network_isolation_env(tmp_path):
    """Verifies that network proxy blocks are injected by default."""
    script = (
        "import os\n"
        "print('PROXY:', os.environ.get('HTTP_PROXY'))\n"
        "print('OFFLINE:', os.environ.get('PHENOM_OFFLINE_MODE'))\n"
    )
    runner = CodeRunner()
    res = runner.execute_in_workspace(
        command=[sys.executable, "-c", script],
        cwd=str(tmp_path),
        allow_network=False
    )
    assert "PROXY: http://127.0.0.1:0" in res.stdout
    assert "OFFLINE: 1" in res.stdout

def test_code_runner_guardian_killswitch_termination(tmp_path):
    """
    Spawns a hanging process and triggers Guardian kill switch.
    Verifies that the process tree is immediately terminated.
    """
    guardian_inst = GuardianKillSwitch()
    runner = CodeRunner(guardian_instance=guardian_inst)

    # Script that loops infinitely
    infinite_script = "import time\nwhile True:\n    time.sleep(0.05)\n"

    import threading
    def trigger_kill():
        time.sleep(0.3)
        guardian_inst.trigger(reason="test_killswitch_trigger")

    t = threading.Thread(target=trigger_kill, daemon=True)
    t.start()

    res = runner.execute_in_workspace(
        command=[sys.executable, "-c", infinite_script],
        cwd=str(tmp_path),
        timeout_seconds=30.0
    )

    t.join()
    assert res.killed_by_guardian is True
    assert guardian_inst.is_halted is True
    assert res.duration_sec < 5.0  # Must be killed quickly, not wait 30s

    # Clean up guardian state
    guardian_inst.resume()

def test_code_runner_timeout_cap(tmp_path):
    """Verifies that the runner terminates processes exceeding the timeout limit."""
    runner = CodeRunner()
    hanging_script = "import time\ntime.sleep(10)\n"

    res = runner.execute_in_workspace(
        command=[sys.executable, "-c", hanging_script],
        cwd=str(tmp_path),
        timeout_seconds=0.5
    )

    assert res.timed_out is True
    assert res.duration_sec < 3.0

# ==============================================================================
# 4. Tool Registry Verification
# ==============================================================================

def test_coding_tools_registered_in_safety_registry():
    """Confirms that all 5 coding agent tools are registered with proper tiers."""
    tool_names = [
        "coding_create_workspace",
        "coding_get_diff",
        "coding_run_in_workspace",
        "coding_verify_package",
        "coding_apply_changes"
    ]
    for name in tool_names:
        tool = registry.get(name)
        assert tool is not None, f"Tool '{name}' is not registered in safety registry!"

    # Verify risk tiers
    assert registry.get("coding_create_workspace").tier == 1
    assert registry.get("coding_get_diff").tier == 0
    assert registry.get("coding_run_in_workspace").tier == 1
    assert registry.get("coding_verify_package").tier == 0
    assert registry.get("coding_apply_changes").tier == 2  # Tier 2 confirmation
