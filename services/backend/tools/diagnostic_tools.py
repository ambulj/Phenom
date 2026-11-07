"""
Safety-Wrapped Autonomous Diagnostic & Self-Healing Worktree Tools.
Registers tools with ToolRegistry for ephemeral worktree management, test execution,
and self-healing diagnostic repair missions (Phase 20-02 DEV-02.1 / DEV-02.2 / MIS-02.1).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.coding.worktree_manager import worktree_manager
from services.backend.coding.test_runner_daemon import test_runner_daemon
from services.backend.coding.diagnostic_agent import diagnostic_mission_agent, MissionRequest


# ==========================================
# 1. Create Worktree Sandbox (Tier 1)
# ==========================================

class CreateWorktreeSandboxArgs(BaseModel):
    commit_ish: Optional[str] = Field(default="HEAD", description="Git commit or branch to branch from.")
    sandbox_id: Optional[str] = Field(default=None, description="Optional custom sandbox identifier.")

def create_worktree_sandbox_preview(args: Dict[str, Any]) -> str:
    commit = args.get("commit_ish", "HEAD")
    sid = args.get("sandbox_id", "auto-generated")
    return f"Create isolated git worktree sandbox '{sid}' from commit '{commit}' under .phenom_worktrees/."

@registry.register(
    name="create_worktree_sandbox",
    tier=1,
    description="Creates an isolated ephemeral git worktree sandbox for testing without touching working tree.",
    args_schema=CreateWorktreeSandboxArgs,
    preview_fn=create_worktree_sandbox_preview,
    can_remember_per_folder=False
)
def handle_create_worktree_sandbox(commit_ish: str = "HEAD", sandbox_id: Optional[str] = None) -> Dict[str, Any]:
    sb = worktree_manager.create_worktree(commit_ish=commit_ish, sandbox_id=sandbox_id)
    return sb.model_dump()


# ==========================================
# 2. Remove Worktree Sandbox (Tier 1)
# ==========================================

class RemoveWorktreeSandboxArgs(BaseModel):
    sandbox_id: str = Field(..., description="Sandbox identifier to remove.")
    force: Optional[bool] = Field(default=True, description="Force remove worktree directory and branch.")

def remove_worktree_sandbox_preview(args: Dict[str, Any]) -> str:
    sid = args.get("sandbox_id", "")
    return f"Remove isolated worktree sandbox '{sid}' and clean up ephemeral branch."

@registry.register(
    name="remove_worktree_sandbox",
    tier=1,
    description="Deletes an isolated git worktree sandbox and cleans up the associated ephemeral branch.",
    args_schema=RemoveWorktreeSandboxArgs,
    preview_fn=remove_worktree_sandbox_preview,
    can_remember_per_folder=False
)
def handle_remove_worktree_sandbox(sandbox_id: str, force: bool = True) -> Dict[str, Any]:
    removed = worktree_manager.remove_worktree(sandbox_id=sandbox_id, force=force)
    return {"sandbox_id": sandbox_id, "removed": removed}


# ==========================================
# 3. Run Isolated Tests (Tier 1)
# ==========================================

class RunIsolatedTestsArgs(BaseModel):
    target_path: Optional[str] = Field(default=None, description="Test file or directory to run.")
    working_dir: Optional[str] = Field(default=None, description="Execution directory (e.g. worktree path).")
    runner: Optional[str] = Field(default="pytest", description="Runner to invoke: pytest or tsc.")
    timeout_seconds: Optional[int] = Field(default=60, description="Max execution duration.")

def run_isolated_tests_preview(args: Dict[str, Any]) -> str:
    runner = args.get("runner", "pytest")
    target = args.get("target_path", "all tests")
    cwd = args.get("working_dir", "workspace")
    return f"Execute '{runner}' on target '{target}' inside directory '{cwd}'."

@registry.register(
    name="run_isolated_tests",
    tier=1,
    description="Executes a test or compiler suite asynchronously, capturing structured diagnostics.",
    args_schema=RunIsolatedTestsArgs,
    preview_fn=run_isolated_tests_preview,
    can_remember_per_folder=False
)
async def handle_run_isolated_tests(
    target_path: Optional[str] = None,
    working_dir: Optional[str] = None,
    runner: str = "pytest",
    timeout_seconds: int = 60
) -> Dict[str, Any]:
    if runner == "tsc":
        result = await test_runner_daemon.run_tsc(working_dir=working_dir, timeout_seconds=timeout_seconds)
    else:
        result = await test_runner_daemon.run_pytest(target_path=target_path, working_dir=working_dir, timeout_seconds=timeout_seconds)
    return result.model_dump()


# ==========================================
# 4. Diagnose and Heal Failure (Tier 2)
# ==========================================

class DiagnoseAndHealFailureArgs(BaseModel):
    test_path: str = Field(..., description="Path to failing test file or test node.")
    target_file: Optional[str] = Field(default=None, description="Target source file to patch.")
    patch_code: Optional[str] = Field(default=None, description="Replacement source code content.")
    search_target: Optional[str] = Field(default=None, description="Substring target to replace.")
    replacement_target: Optional[str] = Field(default=None, description="Replacement content.")
    max_retries: Optional[int] = Field(default=2, description="Max retry attempts.")

def diagnose_and_heal_failure_preview(args: Dict[str, Any]) -> str:
    test_path = args.get("test_path", "")
    target = args.get("target_file", "inferred from failure diagnostic")
    return (
        f"Initiate autonomous self-healing diagnostic mission in isolated worktree for test '{test_path}' "
        f"targeting file '{target}'. Executes baseline test, applies patch in sandbox, verifies pass status, "
        f"and rolls back automatically if regression occurs."
    )

@registry.register(
    name="diagnose_and_heal_failure",
    tier=2,
    description="Executes full autonomous self-healing loop in an isolated worktree sandbox.",
    args_schema=DiagnoseAndHealFailureArgs,
    preview_fn=diagnose_and_heal_failure_preview,
    can_remember_per_folder=False
)
async def handle_diagnose_and_heal_failure(
    test_path: str,
    target_file: Optional[str] = None,
    patch_code: Optional[str] = None,
    search_target: Optional[str] = None,
    replacement_target: Optional[str] = None,
    max_retries: int = 2
) -> Dict[str, Any]:
    req = MissionRequest(
        test_path=test_path,
        target_file=target_file,
        patch_code=patch_code,
        search_target=search_target,
        replacement_target=replacement_target,
        max_retries=max_retries
    )
    report = await diagnostic_mission_agent.execute_mission(req)
    return report.model_dump()


# ==========================================
# 5. Prune Worktrees (Tier 1)
# ==========================================

class PruneWorktreesArgs(BaseModel):
    max_age_seconds: Optional[int] = Field(default=3600, description="Max age in seconds before purging.")

def prune_worktrees_preview(args: Dict[str, Any]) -> str:
    age = args.get("max_age_seconds", 3600)
    return f"Prune stale isolated worktrees older than {age} seconds from .phenom_worktrees/."

@registry.register(
    name="prune_worktrees",
    tier=1,
    description="Prunes expired or orphaned worktrees from .phenom_worktrees/.",
    args_schema=PruneWorktreesArgs,
    preview_fn=prune_worktrees_preview,
    can_remember_per_folder=False
)
def handle_prune_worktrees(max_age_seconds: int = 3600) -> Dict[str, Any]:
    pruned = worktree_manager.prune_worktrees(max_age_seconds=max_age_seconds)
    return {"pruned_count": pruned}
