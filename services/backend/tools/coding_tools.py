"""
Phenom Coding Tools
Safety-wrapped tools for coding agent operations:
- Workspace isolation and pre-execution snapshots
- Diff generation for human review
- Offline test execution with hard runtime caps and Guardian tracking
- Typosquatting verification before package installation
- Confirmed application of changes to original repositories
"""

import os
import psutil
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.coding.workspace import workspace_manager, IsolatedWorkspace
from services.backend.coding.typosquat_guard import typosquat_guard, PackageSecurityReport
from services.backend.coding.runner import code_runner, ExecutionResult

# Store active workspaces by ID
_ACTIVE_WORKSPACES: Dict[str, IsolatedWorkspace] = {}

# ==========================================
# Coding Workspace Creation (Tier 1)
# ==========================================

class CreateWorkspaceArgs(BaseModel):
    project_path: str = Field(description="Path to target project to isolate.")
    task_description: Optional[str] = Field(default=None, description="Optional task name or description.")

def create_workspace_preview(args: Dict[str, Any]) -> str:
    return f"Create isolated coding workspace for project '{args.get('project_path')}'"

@registry.register(
    name="coding_create_workspace",
    tier=1,
    description="Creates an isolated workspace copy of a project with pre-execution snapshotting.",
    args_schema=CreateWorkspaceArgs,
    preview_fn=create_workspace_preview,
    can_remember_per_folder=True
)
def handle_create_workspace(project_path: str, task_description: Optional[str] = None) -> Dict[str, Any]:
    ws = workspace_manager.create_isolated_workspace(project_path, task_name=task_description)
    _ACTIVE_WORKSPACES[ws.workspace_id] = ws
    return {
        "status": "created",
        "workspace_id": ws.workspace_id,
        "isolated_path": ws.isolated_workspace_path,
        "original_path": ws.original_project_path,
        "snapshot_path": ws.snapshot_path
    }

# ==========================================
# Diff Review (Tier 0 - Read Only)
# ==========================================

class GetDiffArgs(BaseModel):
    workspace_id: str = Field(description="ID of the isolated workspace.")

@registry.register(
    name="coding_get_diff",
    tier=0,
    description="Inspects differences between isolated workspace and original project directory.",
    args_schema=GetDiffArgs,
    preview_fn=lambda a: f"Generate unified diff for workspace: {a.get('workspace_id')}"
)
def handle_get_diff(workspace_id: str) -> Dict[str, Any]:
    ws = _ACTIVE_WORKSPACES.get(workspace_id)
    if not ws:
        raise ValueError(f"Workspace '{workspace_id}' not found.")
    return workspace_manager.get_diff(ws)

# ==========================================
# Typosquat Package Verification (Tier 0 / Tier 2 resolver)
# ==========================================

class VerifyPackageArgs(BaseModel):
    package_name: str = Field(description="Name of package to verify before installation.")
    version: Optional[str] = Field(default="latest", description="Version of package.")

def verify_package_preview(args: Dict[str, Any]) -> str:
    pkg = args.get("package_name", "")
    return f"Analyze package '{pkg}' for typosquatting vulnerabilities"

@registry.register(
    name="coding_verify_package",
    tier=0,
    description="Validates a package name against popular package registries to detect typosquatting.",
    args_schema=VerifyPackageArgs,
    preview_fn=verify_package_preview
)
def handle_verify_package(package_name: str, version: str = "latest") -> Dict[str, Any]:
    report = typosquat_guard.evaluate_package(package_name, version=version)
    return report.model_dump()

# ==========================================
# Execute in Workspace (Tier 1)
# ==========================================

class RunInWorkspaceArgs(BaseModel):
    workspace_id: str = Field(description="ID of the isolated workspace.")
    command: List[str] = Field(description="Command and arguments to execute.")
    timeout_sec: float = Field(default=120.0, description="Execution timeout cap (max 120s).")
    allow_network: bool = Field(default=False, description="Whether outbound network is permitted.")

def run_in_workspace_preview(args: Dict[str, Any]) -> str:
    cmd_str = " ".join(args.get("command") or [])
    ws_id = args.get("workspace_id", "")
    return f"Execute command '{cmd_str}' in isolated workspace '{ws_id}' (offline: {not args.get('allow_network', False)})"

@registry.register(
    name="coding_run_in_workspace",
    tier=1,
    description="Runs tests, builds, or scripts in an isolated workspace with Guardian kill switch tracking.",
    args_schema=RunInWorkspaceArgs,
    preview_fn=run_in_workspace_preview
)
def handle_run_in_workspace(
    workspace_id: str,
    command: List[str],
    timeout_sec: float = 120.0,
    allow_network: bool = False
) -> Dict[str, Any]:
    ws = _ACTIVE_WORKSPACES.get(workspace_id)
    if not ws:
        raise ValueError(f"Workspace '{workspace_id}' not found.")
    result = code_runner.execute_in_workspace(
        command=command,
        cwd=ws.isolated_workspace_path,
        timeout_seconds=timeout_sec,
        allow_network=allow_network
    )
    return result.model_dump()

# ==========================================
# Apply Changes to Original Repository (Tier 2 - Requires Confirmation)
# ==========================================

class ApplyChangesArgs(BaseModel):
    workspace_id: str = Field(description="ID of the isolated workspace.")

def apply_changes_preview(args: Dict[str, Any]) -> str:
    ws_id = args.get("workspace_id", "")
    return f"Apply approved isolated changes from workspace '{ws_id}' to original repository"

@registry.register(
    name="coding_apply_changes",
    tier=2,
    description="Applies approved code changes from isolated workspace back to original repository with rollback snapshot.",
    args_schema=ApplyChangesArgs,
    preview_fn=apply_changes_preview
)
def handle_apply_changes(workspace_id: str) -> Dict[str, Any]:
    ws = _ACTIVE_WORKSPACES.get(workspace_id)
    if not ws:
        raise ValueError(f"Workspace '{workspace_id}' not found.")
    return workspace_manager.apply_to_original(ws, confirmed=True)

# ==========================================
# Port Conflict Inspection & Resolution (Rounds 40 & 50)
# ==========================================

class InspectPortArgs(BaseModel):
    port: int = Field(..., description="TCP port number to inspect for EADDRINUSE conflict.")

def inspect_port_preview(args: Dict[str, Any]) -> str:
    return f"Inspect TCP port {args.get('port')} conflict status."

@registry.register(
    name="coding_inspect_port",
    tier=0,
    description="Inspects active TCP port to identify which PID or process is holding it on EADDRINUSE.",
    args_schema=InspectPortArgs,
    preview_fn=inspect_port_preview
)
def handle_inspect_port(port: int) -> Dict[str, Any]:
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == port and conn.status == "LISTEN":
                pid = conn.pid
                if pid:
                    try:
                        p = psutil.Process(pid)
                        return {
                            "status": "in_use",
                            "port": port,
                            "pid": pid,
                            "process_name": p.name(),
                            "cmdline": " ".join(p.cmdline()[:5]),
                            "username": p.username() if hasattr(p, "username") else None
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        return {
                            "status": "in_use",
                            "port": port,
                            "pid": pid,
                            "process_name": "unknown",
                            "cmdline": ""
                        }
        return {"status": "free", "port": port}
    except Exception as e:
        return {"status": "error", "port": port, "error": str(e)}

class ResolvePortConflictArgs(BaseModel):
    port: int = Field(..., description="TCP port number to resolve.")
    terminate: bool = Field(default=False, description="Whether to kill the process holding the port (Tier 2).")

def resolve_port_tier(args: Dict[str, Any]) -> int:
    return 2 if args.get("terminate", False) else 0

def resolve_port_preview(args: Dict[str, Any]) -> str:
    port = args.get("port")
    if args.get("terminate", False):
        return f"Terminate process holding TCP port {port} (Tier 2 confirmation required)."
    return f"Check resolution status for TCP port {port}."

@registry.register(
    name="coding_resolve_port_conflict",
    tier=resolve_port_tier,
    description="Resolves EADDRINUSE port conflicts by identifying holding process and optionally terminating it.",
    args_schema=ResolvePortConflictArgs,
    preview_fn=resolve_port_preview
)
def handle_resolve_port_conflict(port: int, terminate: bool = False) -> Dict[str, Any]:
    info = handle_inspect_port(port)
    if info.get("status") == "in_use" and terminate:
        pid = info.get("pid")
        if pid:
            killed = code_runner.terminate_process_tree(pid)
            return {
                "port": port,
                "action": "terminated",
                "pid": pid,
                "processes_killed": killed,
                "previous_process": info.get("process_name")
            }
    return info


# ==========================================
# Developer Workspace State (Tier 0 - Read Only)
# ==========================================

from services.backend.coding.workspace_sentinel import workspace_sentinel

class GetWorkspaceStateArgs(BaseModel):
    workspace_path: Optional[str] = Field(default=None, description="Optional path of workspace to inspect. If omitted, uses active foreground IDE workspace.")

@registry.register(
    name="coding_get_workspace_state",
    tier=0,
    description="Inspects active developer workspace, git branch, dirty status, and lines added/deleted with microsecond stat caching.",
    args_schema=GetWorkspaceStateArgs,
    preview_fn=lambda a: f"Inspect developer workspace state{' for ' + a.get('workspace_path') if a.get('workspace_path') else ''}"
)
def handle_get_workspace_state(workspace_path: Optional[str] = None) -> Dict[str, Any]:
    if workspace_path:
        state = workspace_sentinel.inspect_workspace(workspace_path)
    else:
        state = workspace_sentinel.poll_once() or workspace_sentinel.get_current_state()
        if not state:
            state = workspace_sentinel.inspect_workspace("C:\\Phenom")
    return state.model_dump()


# ==========================================
# Proactive Dev Build Sentinel Tools (DEV-02)
# ==========================================

from services.backend.coding.build_sentinel import build_sentinel

class DiagnoseBuildFailureArgs(BaseModel):
    log_output: str = Field(..., description="Raw build, test, or compiler log output.")
    workspace_path: Optional[str] = Field(default=None, description="Optional target workspace path.")

@registry.register(
    name="coding_diagnose_build_failure",
    tier=0,
    description="Parses build or test failure output and extracts structured diagnostics (pytest, vitest, tsc, cargo, python).",
    args_schema=DiagnoseBuildFailureArgs,
    preview_fn=lambda a: "Diagnose build or test failure from log output"
)
def handle_diagnose_build_failure(log_output: str, workspace_path: Optional[str] = None) -> Dict[str, Any]:
    diag = build_sentinel.diagnose_output(log_output, workspace_path=workspace_path)
    if not diag:
        return {"status": "unrecognized", "message": "No recognized build failure detected in log output."}
    return {"status": "diagnosed", "diagnostic": diag.model_dump()}


class DraftPatchArgs(BaseModel):
    failing_file: str = Field(..., description="Path of file to fix.")
    replacement_code: str = Field(..., description="Full corrected content of the file.")
    workspace_path: Optional[str] = Field(default=None, description="Optional target workspace path.")

@registry.register(
    name="coding_draft_patch",
    tier=0,
    description="Synthesizes a minimal unified git diff patch for a target file.",
    args_schema=DraftPatchArgs,
    preview_fn=lambda a: f"Draft minimal unified diff patch for {a.get('failing_file')}"
)
def handle_draft_patch(failing_file: str, replacement_code: str, workspace_path: Optional[str] = None) -> Dict[str, Any]:
    diff = build_sentinel.draft_patch(failing_file, replacement_code, workspace_path=workspace_path)
    if not diff:
        return {"status": "error", "message": f"Could not generate diff for {failing_file}."}
    return {"status": "drafted", "patch_diff": diff}


class ApplyPatchArgs(BaseModel):
    patch_diff: str = Field(..., description="Unified git diff to apply.")
    workspace_path: Optional[str] = Field(default=None, description="Optional target workspace path.")
    resolution_notes: Optional[str] = Field(default=None, description="Optional resolution note for Obsidian debug log.")

@registry.register(
    name="coding_apply_patch",
    tier=1,
    description="Applies a unified git diff patch to the workspace after creating a non-destructive rollback snapshot.",
    args_schema=ApplyPatchArgs,
    preview_fn=lambda a: "Apply unified git diff patch with pre-patch working tree snapshot"
)
def handle_apply_patch(patch_diff: str, workspace_path: Optional[str] = None, resolution_notes: Optional[str] = None) -> Dict[str, Any]:
    success, token, err = build_sentinel.apply_patch_fix(
        patch_diff,
        workspace_path=workspace_path,
        resolution_notes=resolution_notes,
    )
    if not success:
        return {"status": "failed", "error": err}
    return {"status": "applied", "rollback_token": token}


class RevertPatchArgs(BaseModel):
    rollback_token: str = Field(..., description="Rollback token SHA returned during patch application.")
    workspace_path: Optional[str] = Field(default=None, description="Optional target workspace path.")

@registry.register(
    name="coding_revert_patch",
    tier=1,
    description="Reverts the workspace to the exact working tree state prior to patch application.",
    args_schema=RevertPatchArgs,
    preview_fn=lambda a: f"Revert workspace to pre-patch snapshot {a.get('rollback_token')}"
)
def handle_revert_patch(rollback_token: str, workspace_path: Optional[str] = None) -> Dict[str, Any]:
    success = build_sentinel.revert_patch_fix(rollback_token, workspace_path=workspace_path)
    if not success:
        return {"status": "failed", "message": f"Failed to revert using rollback token {rollback_token}."}
    return {"status": "reverted", "rollback_token": rollback_token}


