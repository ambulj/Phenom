"""
Workspace Cloner & Sandbox Lifecycle Manager (Phase 47-02, EXEC-01).
Ensures coding operations occur strictly inside an isolated copy of the target repository:
%USERPROFILE%\\Projects\\.workspaces\\<project_name>_<timestamp>\\

Invariants:
1. Original repository remains 100% pristine and untouched during execution.
2. Pre-execution snapshot zip taken prior to any code modification.
3. Excludes heavy/sensitive dependencies (.git, node_modules, venv, __pycache__).
4. Reversible cleanup and lifecycle management.
"""

import os
import shutil
import time
import zipfile
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.path_guard import validate_path, PathSecurityViolation


class IsolatedWorkspaceContext(BaseModel):
    """Encapsulates metadata and paths for an isolated coding workspace."""
    workspace_id: str = Field(..., description="Unique workspace identifier")
    project_name: str = Field(..., description="Target project name")
    original_project_path: str = Field(..., description="Canonical path to source repository")
    isolated_workspace_path: str = Field(..., description="Path to active isolated workspace clone")
    snapshot_path: str = Field(..., description="Path to pre-execution backup zip snapshot")
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")
    files_manifest: Dict[str, float] = Field(default_factory=dict, description="Relative file paths and modification times")


class WorkspaceCloner:
    """Clones repositories into isolated sandbox directories for autonomous execution."""

    DEFAULT_WORKSPACES_ROOT = os.path.join(
        os.environ.get("USERPROFILE") or os.path.expanduser("~"),
        "Projects",
        ".workspaces"
    )

    IGNORE_PATTERNS = {
        ".git", ".venv", "venv", "__pycache__", "node_modules",
        ".pytest_cache", ".mypy_cache", ".coverage", "dist", "build",
        ".workspaces", ".idea", ".vscode"
    }

    def __init__(self, workspaces_root: Optional[str] = None):
        self.workspaces_root = os.path.abspath(workspaces_root or self.DEFAULT_WORKSPACES_ROOT)
        self.snapshots_root = os.path.join(self.workspaces_root, "_snapshots")
        os.makedirs(self.workspaces_root, exist_ok=True)
        os.makedirs(self.snapshots_root, exist_ok=True)
        self._workspaces: Dict[str, IsolatedWorkspaceContext] = {}

    def _should_ignore(self, path: str) -> bool:
        parts = os.path.normpath(path).split(os.sep)
        return any(part in self.IGNORE_PATTERNS for part in parts)

    def _create_snapshot(self, source_path: str, safe_name: str, timestamp_str: str) -> str:
        """Creates a compressed pre-execution zip snapshot of the source project."""
        snapshot_filename = f"{safe_name}_{timestamp_str}_snapshot.zip"
        snapshot_file_path = os.path.join(self.snapshots_root, snapshot_filename)

        with zipfile.ZipFile(snapshot_file_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
            for root, dirs, files in os.walk(source_path):
                # Filter out ignored directories in-place
                dirs[:] = [d for d in dirs if not self._should_ignore(os.path.join(root, d))]
                for f in files:
                    full_p = os.path.join(root, f)
                    if not self._should_ignore(full_p):
                        rel_p = os.path.relpath(full_p, source_path)
                        zip_f.write(full_p, arcname=rel_p)

        return snapshot_file_path

    def clone_project(
        self,
        target_project_path: str,
        task_name: Optional[str] = None
    ) -> IsolatedWorkspaceContext:
        """
        Clones target project into an isolated workspace directory.
        Takes a snapshot of the original project first.
        """
        # 1. Validate target path
        canonical_target = os.path.abspath(os.path.realpath(target_project_path))
        if not os.path.exists(canonical_target) or not os.path.isdir(canonical_target):
            raise FileNotFoundError(f"Target project directory does not exist: '{canonical_target}'")

        validate_path(canonical_target, mode="read")

        project_name = os.path.basename(canonical_target.rstrip(r"\/")) or "project"
        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", project_name)
        timestamp_str = str(int(time.time() * 1000))
        workspace_id = f"ws_{safe_name}_{timestamp_str}"

        # 2. Pre-execution snapshot
        snapshot_path = self._create_snapshot(canonical_target, safe_name, timestamp_str)

        # 3. Create isolated workspace directory
        isolated_dir = os.path.join(self.workspaces_root, f"{safe_name}_{timestamp_str}")
        os.makedirs(isolated_dir, exist_ok=True)

        # 4. Copy files while observing ignore patterns
        files_manifest: Dict[str, float] = {}
        for root, dirs, files in os.walk(canonical_target):
            dirs[:] = [d for d in dirs if not self._should_ignore(os.path.join(root, d))]
            for f in files:
                src_file = os.path.join(root, f)
                if not self._should_ignore(src_file):
                    rel_p = os.path.relpath(src_file, canonical_target)
                    dest_file = os.path.join(isolated_dir, rel_p)
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copy2(src_file, dest_file)
                    try:
                        files_manifest[rel_p] = os.path.getmtime(dest_file)
                    except OSError:
                        files_manifest[rel_p] = time.time()

        ctx = IsolatedWorkspaceContext(
            workspace_id=workspace_id,
            project_name=project_name,
            original_project_path=canonical_target,
            isolated_workspace_path=isolated_dir,
            snapshot_path=snapshot_path,
            created_at=time.time(),
            files_manifest=files_manifest
        )

        self._workspaces[workspace_id] = ctx
        return ctx

    def get_workspace(self, workspace_id: str) -> Optional[IsolatedWorkspaceContext]:
        """Retrieves an active workspace context by ID."""
        return self._workspaces.get(workspace_id)

    def list_workspaces(self) -> List[IsolatedWorkspaceContext]:
        """Lists all active isolated workspaces."""
        return list(self._workspaces.values())

    def cleanup_workspace(self, workspace_id: str) -> bool:
        """Removes the isolated workspace directory from disk."""
        ctx = self._workspaces.pop(workspace_id, None)
        if not ctx:
            return False

        if os.path.exists(ctx.isolated_workspace_path):
            shutil.rmtree(ctx.isolated_workspace_path, ignore_errors=True)

        return True

    def cleanup_all_workspaces(self) -> int:
        """Cleans up all tracked workspaces."""
        count = 0
        wids = list(self._workspaces.keys())
        for wid in wids:
            if self.cleanup_workspace(wid):
                count += 1
        return count


# Global singleton instance
workspace_cloner = WorkspaceCloner()
