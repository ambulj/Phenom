r"""
Phenom Workspace Isolation & Snapshot Pipeline (Task 7i)
Ensures coding agent modifications, compilation, and testing occur strictly inside
an isolated directory (%USERPROFILE%\Projects\.workspaces\project_copy\).

Safety Invariants:
1. Pre-execution snapshot taken before any code modification.
2. Original repository remains 100% pristine and untouched during execution.
3. Clean unified diff generated for human review.
4. Applying changes to original repo is a Tier 2/3 action requiring explicit confirmation.
"""

import os
import shutil
import time
import zipfile
import difflib
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field

from services.backend.safety.path_guard import validate_path, PathSecurityViolation
from services.backend.resource.storage_manager import storage_manager

class IsolatedWorkspace(BaseModel):
    workspace_id: str
    original_project_path: str
    isolated_workspace_path: str
    snapshot_path: str
    created_at: float
    files_manifest: Dict[str, float] = Field(default_factory=dict)

class WorkspaceManager:
    DEFAULT_WORKSPACES_ROOT = os.path.join(
        os.environ.get("USERPROFILE") or os.path.expanduser("~"),
        "Projects",
        ".workspaces"
    )

    IGNORE_PATTERNS = {
        ".git", ".venv", "venv", "__pycache__", "node_modules",
        ".pytest_cache", ".mypy_cache", ".coverage", "dist", "build"
    }

    def __init__(self, workspaces_root: Optional[str] = None):
        self.workspaces_root = os.path.abspath(workspaces_root or self.DEFAULT_WORKSPACES_ROOT)
        os.makedirs(self.workspaces_root, exist_ok=True)

    def create_isolated_workspace(
        self,
        target_project_path: str,
        task_name: Optional[str] = None
    ) -> IsolatedWorkspace:
        """
        Creates an isolated workspace copy of the target project.
        Takes a snapshot of the original project first.
        """
        # 1. Validate target path
        canonical_target = os.path.abspath(os.path.realpath(target_project_path))
        if not os.path.exists(canonical_target) or not os.path.isdir(canonical_target):
            raise FileNotFoundError(f"Target project directory does not exist: '{canonical_target}'")

        validate_path(canonical_target, mode="read")

        project_name = os.path.basename(canonical_target.rstrip("\\/")) or "project"
        timestamp_str = str(int(time.time() * 1000))
        workspace_id = f"{project_name}_copy_{timestamp_str}"
        isolated_path = os.path.join(self.workspaces_root, workspace_id)

        # 2. Capture initial file manifest of original project
        manifest = self._build_manifest(canonical_target)

        # 3. Take pre-execution snapshot zip file
        snapshot_dir = storage_manager.snapshots_dir
        os.makedirs(snapshot_dir, exist_ok=True)
        snapshot_filename = f"snapshot_{workspace_id}.zip"
        snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
        self._create_snapshot_zip(canonical_target, snapshot_path)

        # 4. Copy project files into isolated workspace
        os.makedirs(isolated_path, exist_ok=True)
        self._copy_project_tree(canonical_target, isolated_path)

        return IsolatedWorkspace(
            workspace_id=workspace_id,
            original_project_path=canonical_target,
            isolated_workspace_path=isolated_path,
            snapshot_path=snapshot_path,
            created_at=time.time(),
            files_manifest=manifest
        )

    def _build_manifest(self, root_dir: str) -> Dict[str, float]:
        """Maps relative file paths to their modification timestamps."""
        manifest = {}
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_PATTERNS]
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_dir)
                try:
                    manifest[rel_path] = os.path.getmtime(full_path)
                except OSError:
                    pass
        return manifest

    def _create_snapshot_zip(self, source_dir: str, zip_path: str) -> None:
        """Creates a compressed archive snapshot of the source directory."""
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(source_dir):
                dirs[:] = [d for d in dirs if d not in self.IGNORE_PATTERNS]
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, source_dir)
                    zf.write(full_path, arcname=rel_path)

    def _copy_project_tree(self, src: str, dst: str) -> None:
        """Copies project tree excluding ignored directories."""
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_PATTERNS]
            rel_root = os.path.relpath(root, src)
            target_root = os.path.join(dst, rel_root) if rel_root != "." else dst
            os.makedirs(target_root, exist_ok=True)

            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_root, file)
                shutil.copy2(src_file, dst_file)

    def verify_original_untouched(self, workspace: IsolatedWorkspace) -> bool:
        """
        Verifies that the original project directory has not been altered
        since the isolated workspace was spawned.
        """
        current_manifest = self._build_manifest(workspace.original_project_path)
        if set(current_manifest.keys()) != set(workspace.files_manifest.keys()):
            return False

        for rel_path, mtime in workspace.files_manifest.items():
            if rel_path not in current_manifest:
                return False
            # Verify modification time matches original recorded timestamp
            if abs(current_manifest[rel_path] - mtime) > 0.001:
                return False

        return True

    def get_diff(self, workspace: IsolatedWorkspace) -> Dict[str, Any]:
        """
        Calculates unified diff between original project and isolated workspace.
        """
        orig_root = workspace.original_project_path
        iso_root = workspace.isolated_workspace_path

        orig_manifest = self._build_manifest(orig_root)
        iso_manifest = self._build_manifest(iso_root)

        all_files = sorted(set(orig_manifest.keys()) | set(iso_manifest.keys()))

        files_added = []
        files_modified = []
        files_deleted = []
        diff_lines = []

        for rel_path in all_files:
            orig_file = os.path.join(orig_root, rel_path)
            iso_file = os.path.join(iso_root, rel_path)

            if rel_path in iso_manifest and rel_path not in orig_manifest:
                # File added
                files_added.append(rel_path)
                with open(iso_file, "r", encoding="utf-8", errors="replace") as f:
                    iso_content = f.readlines()
                diff = difflib.unified_diff(
                    [], iso_content,
                    fromfile=f"a/{rel_path} (nonexistent)",
                    tofile=f"b/{rel_path}"
                )
                diff_lines.extend(diff)

            elif rel_path in orig_manifest and rel_path not in iso_manifest:
                # File deleted
                files_deleted.append(rel_path)
                with open(orig_file, "r", encoding="utf-8", errors="replace") as f:
                    orig_content = f.readlines()
                diff = difflib.unified_diff(
                    orig_content, [],
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path} (deleted)"
                )
                diff_lines.extend(diff)

            else:
                # File exists in both - compare content
                with open(orig_file, "r", encoding="utf-8", errors="replace") as f:
                    orig_content = f.readlines()
                with open(iso_file, "r", encoding="utf-8", errors="replace") as f:
                    iso_content = f.readlines()

                if orig_content != iso_content:
                    files_modified.append(rel_path)
                    diff = difflib.unified_diff(
                        orig_content, iso_content,
                        fromfile=f"a/{rel_path}",
                        tofile=f"b/{rel_path}"
                    )
                    diff_lines.extend(diff)

        diff_text = "".join(diff_lines)
        return {
            "diff_text": diff_text,
            "files_added": files_added,
            "files_modified": files_modified,
            "files_deleted": files_deleted,
            "total_changes": len(files_added) + len(files_modified) + len(files_deleted)
        }

    def apply_to_original(
        self,
        workspace: IsolatedWorkspace,
        confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Applies approved isolated workspace changes back to the original repository.
        Requires explicit confirmation (Tier 2/3 action).
        Takes a secondary rollback snapshot before writing.
        """
        if not confirmed:
            raise PermissionError(
                "Applying isolated workspace changes to the original repository requires explicit confirmation."
            )

        orig_root = workspace.original_project_path
        iso_root = workspace.isolated_workspace_path

        # 1. Take a pre-apply rollback snapshot of the original project
        snapshot_dir = storage_manager.snapshots_dir
        rollback_filename = f"rollback_pre_apply_{workspace.workspace_id}.zip"
        rollback_path = os.path.join(snapshot_dir, rollback_filename)
        self._create_snapshot_zip(orig_root, rollback_path)

        # 2. Get diff to determine changes
        diff_info = self.get_diff(workspace)

        # 3. Apply additions and modifications
        for rel_path in diff_info["files_added"] + diff_info["files_modified"]:
            src_file = os.path.join(iso_root, rel_path)
            dst_file = os.path.join(orig_root, rel_path)
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            shutil.copy2(src_file, dst_file)

        # 4. Apply deletions
        for rel_path in diff_info["files_deleted"]:
            dst_file = os.path.join(orig_root, rel_path)
            if os.path.exists(dst_file):
                os.remove(dst_file)

        return {
            "status": "applied",
            "rollback_snapshot": rollback_path,
            "applied_changes": diff_info["total_changes"],
            "files_added": diff_info["files_added"],
            "files_modified": diff_info["files_modified"],
            "files_deleted": diff_info["files_deleted"]
        }

    def cleanup_workspace(self, workspace: IsolatedWorkspace) -> bool:
        """Removes the isolated workspace directory."""
        if os.path.exists(workspace.isolated_workspace_path):
            shutil.rmtree(workspace.isolated_workspace_path, ignore_errors=True)
            return True
        return False

# Global workspace manager
workspace_manager = WorkspaceManager()
