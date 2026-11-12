"""
Comprehensive Day-in-the-Life End-to-End Simulation for Milestone 8.0:
Phenom 8.0 Dual-Presence Autonomous Developer & Mobile Executive Partner
(DEV-01, DEV-02, MOB-01, MOB-02, RES-01, SAF-01, SAF-02)
"""

import asyncio
import os
import subprocess
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from services.backend.coding.workspace_sentinel import workspace_sentinel
from services.backend.coding.build_sentinel import build_sentinel
from services.backend.coding.project_crystallizer import project_crystallizer
from services.backend.remote.telegram_bot import TelegramBotController
from services.backend.remote.telegram_client import TelegramClient
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.workspace import DeveloperWorkspaceState, WorkspaceFileChange


@pytest.fixture
def test_repo_and_vault(tmp_path):
    """Sets up an isolated git repository and Obsidian vault for E2E testing."""
    repo_dir = tmp_path / "PhenomCore"
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "config", "user.email", "tester@phenom.ai"], cwd=str(repo_dir), check=True)

    # Initial file and commit
    calc_py = repo_dir / "calculator.py"
    calc_py.write_text("def add(a, b):\n    return a + b - 1  # Buggy implementation\n", encoding="utf-8")
    subprocess.run(["git", "add", "calculator.py"], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(repo_dir), check=True)

    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)

    return str(repo_dir), str(vault_dir)


@pytest.mark.asyncio
async def test_full_milestone_8_day_in_the_life_simulation(test_repo_and_vault):
    """
    Executes complete autonomous developer & mobile executive partner workflow:
    1. Workspace Sentinel tracks git state & uncommitted changes (DEV-01)
    2. Build failure diagnosed & unified patch drafted (DEV-02)
    3. Mobile Dual-Presence push to Telegram with inline buttons (MOB-01, MOB-02)
    4. Remote 1-click approval resolves desktop confirmation Future (MOB-02)
    5. Patch applied with atomic pre-patch snapshot token (DEV-02)
    6. Technical knowledge crystallized in Obsidian with wikilinks (RES-01)
    7. Remote Guardian kill switch synchronously halts all subsystems < 25ms (SAF-02)
    """
    repo_path, vault_path = test_repo_and_vault
    project_crystallizer.vault_path = vault_path

    # =========================================================================
    # Step 1: Workspace Sentinel Git State Tracking (DEV-01)
    # =========================================================================
    # Modify a file to make repo dirty
    with open(os.path.join(repo_path, "calculator.py"), "a", encoding="utf-8") as f:
        f.write("# WIP developer note\n")

    state = workspace_sentinel.inspect_workspace(repo_path)
    assert state.is_git is True
    assert state.is_dirty is True
    assert state.lines_added > 0
    assert any(f.path == "calculator.py" for f in state.modified_files)

    # =========================================================================
    # Step 2: Build Sentinel Diagnoses Failure & Drafts Patch (DEV-02)
    # =========================================================================
    pytest_failure_output = """
=================================== FAILURES ===================================
__________________________________ test_add ___________________________________
    def test_add():
>       assert add(2, 3) == 5
E       assert 4 == 5

calculator_test.py:4: AssertionError
=========================== short test summary info ===========================
FAILED calculator_test.py::test_add - assert 4 == 5
    """

    diagnostic = build_sentinel.diagnose_output(pytest_failure_output, workspace_path=repo_path)
    assert diagnostic.runner == "pytest"
    assert diagnostic.error_type == "AssertionError"

    # Draft patch
    failing_file = "calculator.py"
    clean_code = "def add(a, b):\n    return a + b\n"
    patch_diff = build_sentinel.draft_patch(failing_file, clean_code, workspace_path=repo_path)
    assert patch_diff is not None
    assert "return a + b" in patch_diff

    # =========================================================================
    # Step 3 & 4: Mobile Dual-Presence Gateway: Push & 1-Click Remote Approval (MOB-01, MOB-02)
    # =========================================================================
    from services.backend.main import pending_confirmations

    mock_telegram_client = MagicMock(spec=TelegramClient)
    mock_telegram_client.send_message = AsyncMock(return_value={"message_id": 100})
    mock_telegram_client.edit_message_text = AsyncMock(return_value={"message_id": 100})
    mock_telegram_client.answer_callback_query = AsyncMock(return_value=True)
    mock_telegram_client.send_approval_request = AsyncMock(return_value={"message_id": 101})

    owner_id = 12345678
    bot = TelegramBotController(token="sim_token", owner_id=owner_id, client=mock_telegram_client)

    req_id = "e2e_approval_req_01"
    desktop_future = asyncio.get_event_loop().create_future()
    pending_confirmations[req_id] = desktop_future

    # Desktop pushes confirmation request to Telegram
    pushed = await bot.notify_desktop_approval_request(
        request_id=req_id,
        tool="coding_apply_patch",
        tier=1,
        preview="Apply fix for add(a, b) in calculator.py",
        args={"patch": patch_diff},
        diff=patch_diff
    )
    assert pushed is True

    # Owner views diff remotely via Telegram callback
    cb_diff = {
        "update_id": 100,
        "callback_query": {
            "id": "cb_view",
            "from": {"id": owner_id},
            "data": f"diff:{req_id}",
            "message": {"message_id": 101, "chat": {"id": owner_id}}
        }
    }
    diff_res = await bot.process_update(cb_diff)
    assert diff_res["status"] == "diff_viewed"

    # Owner approves patch with 1-click on mobile
    cb_approve = {
        "update_id": 101,
        "callback_query": {
            "id": "cb_ok",
            "from": {"id": owner_id},
            "data": f"approve:{req_id}",
            "message": {"message_id": 101, "chat": {"id": owner_id}}
        }
    }
    appr_res = await bot.process_update(cb_approve)
    assert appr_res["status"] == "approved"

    # Verify desktop future was resolved asynchronously
    assert desktop_future.done()
    decision, _ = desktop_future.result()
    assert decision == "approved"

    pending_confirmations.pop(req_id, None)

    # =========================================================================
    # Step 5: Patch Applied with Non-Destructive Rollback Token (DEV-02)
    # =========================================================================
    success, stash_token, err = build_sentinel.apply_patch_fix(
        patch_diff,
        workspace_path=repo_path,
        resolution_notes="Fixed off-by-one bug in addition"
    )
    assert success is True
    assert stash_token is not None

    with open(os.path.join(repo_path, "calculator.py"), "r", encoding="utf-8") as f:
        fixed_content = f.read()
    assert "return a + b" in fixed_content
    assert "- 1" not in fixed_content

    # =========================================================================
    # Step 6: Deep Project Knowledge Crystallization in Obsidian (RES-01)
    # =========================================================================
    cryst_res = project_crystallizer.crystallize_build_fix(
        project_name="PhenomCore",
        root_path=repo_path,
        error_type="AssertionError",
        file_path="calculator.py",
        patch_summary="Corrected off-by-one calculation in add()",
        stack_summary="Python 3.11 / Pytest"
    )
    assert cryst_res["status"] == "crystallized"

    cryst_dec = project_crystallizer.crystallize_decision(
        project_name="PhenomCore",
        root_path=repo_path,
        title="Zero-Tolerance Test Gate",
        decision="Every math routine must be covered by exact equality unit tests.",
        rationale="Eliminates silent calculation regressions."
    )
    assert cryst_dec["status"] == "crystallized"

    note_text = project_crystallizer.read_project_knowledge("PhenomCore")
    assert note_text is not None
    assert "# Project: PhenomCore" in note_text
    assert "[[Daily Notes/" in note_text
    assert "AssertionError" in note_text
    assert "Zero-Tolerance Test Gate" in note_text

    # =========================================================================
    # Step 7: Unified Dual-Presence Guardian Kill Switch (< 25ms SLA) (SAF-02)
    # =========================================================================
    guardian.resume()
    assert guardian.is_halted is False

    t0 = time.perf_counter()
    guardian.trigger("Emergency E2E remote halt")
    t1 = time.perf_counter()
    halt_latency_ms = (t1 - t0) * 1000

    assert guardian.is_halted is True
    assert halt_latency_ms < 25.0

    # Verify all subsystems strictly reject operations while halted
    assert workspace_sentinel.is_halted is True
    assert build_sentinel.is_halted is True
    assert project_crystallizer.is_halted is True

    with pytest.raises(PermissionError):
        project_crystallizer.crystallize_decision("PhenomCore", repo_path, "Title", "Decision")

    guardian.resume()
    assert guardian.is_halted is False
