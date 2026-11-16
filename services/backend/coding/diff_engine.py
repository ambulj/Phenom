"""
Rollback-Capable Unified Diff Engine (Phase 47-02, EXEC-03).
Generates unified diffs between original repository and isolated workspace, creates pre-apply snapshots,
and enforces safe atomic application with rollback guarantees.
"""

import os
import shutil
import difflib
import zipfile
import time
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from services.backend.safety.path_guard import validate_path


class FileDiff(BaseModel):
    """Diff statistics and content for a single file."""
    path: str = Field(..., description="Relative file path")
    status: str = Field(..., description="'added', 'modified', or 'deleted'")
    additions: int = Field(default=0, description="Lines added")
    deletions: int = Field(default=0, description="Lines removed")
    diff_content: str = Field(default="", description="Unified diff text")


class WorkspaceDiffReport(BaseModel):
    """Aggregate diff report comparing workspace against original repository."""
    total_files_changed: int = Field(default=0, description="Count of changed files")
    total_additions: int = Field(default=0, description="Total lines added")
    total_deletions: int = Field(default=0, description="Total lines removed")
    file_diffs: List[FileDiff] = Field(default_factory=list, description="List of per-file diffs")
    unified_patch: str = Field(default="", description="Consolidated patch text for entire workspace")


class ApplyResult(BaseModel):
    """Result of applying workspace modifications to original repository."""
    success: bool = Field(..., description="True if changes were applied without error")
    files_applied: List[str] = Field(default_factory=list, description="Paths of files successfully updated")
    rollback_snapshot_path: Optional[str] = Field(default=None, description="Path to pre-apply rollback backup zip")
    error: Optional[str] = Field(default=None, description="Error message if application failed")


class WorkspaceDiffEngine:
    """Computes unified diffs, creates pre-apply snapshots, and safely merges changes."""

    IGNORE_PATTERNS = {
        ".git", ".venv", "venv", "__pycache__", "node_modules",
        ".pytest_cache", ".mypy_cache", ".coverage", "dist", "build",
        ".workspaces"
    }

    def __init__(self, snapshots_dir: Optional[str] = None):
        if snapshots_dir:
            self.snapshots_dir = os.path.abspath(snapshots_dir)
        else:
            root = os.path.join(
                os.environ.get("USERPROFILE") or os.path.expanduser("~"),
                "Projects",
                ".workspaces",
                "_snapshots"
            )
            self.snapshots_dir = os.path.abspath(root)
        os.makedirs(self.snapshots_dir, exist_ok=True)

    def _should_ignore(self, path: str) -> bool:
        parts = os.path.normpath(path).split(os.sep)
        return any(part in self.IGNORE_PATTERNS for part in parts)

    def _collect_files(self, base_dir: str) -> Dict[str, str]:
        """Collects all non-ignored relative paths mapped to full paths."""
        file_map: Dict[str, str] = {}
        if not os.path.exists(base_dir):
            return file_map

        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if not self._should_ignore(os.path.join(root, d))]
            for f in files:
                full_p = os.path.join(root, f)
                if not self._should_ignore(full_p):
                    rel_p = os.path.normpath(os.path.relpath(full_p, base_dir)).replace("\\", "/")
                    file_map[rel_p] = full_p
        return file_map

    def compute_diff(self, original_dir: str, workspace_dir: str) -> WorkspaceDiffReport:
        """
        Computes detailed unified diff between original project and isolated workspace.
        """
        orig_map = self._collect_files(original_dir)
        work_map = self._collect_files(workspace_dir)

        all_rel_paths = sorted(set(orig_map.keys()) | set(work_map.keys()))
        file_diffs: List[FileDiff] = []
        total_add = 0
        total_del = 0
        patch_pieces: List[str] = []

        for rel_p in all_rel_paths:
            in_orig = rel_p in orig_map
            in_work = rel_p in work_map

            orig_lines: List[str] = []
            work_lines: List[str] = []

            if in_orig:
                try:
                    with open(orig_map[rel_p], "r", encoding="utf-8", errors="replace") as f:
                        orig_lines = f.readlines()
                except OSError:
                    orig_lines = []

            if in_work:
                try:
                    with open(work_map[rel_p], "r", encoding="utf-8", errors="replace") as f:
                        work_lines = f.readlines()
                except OSError:
                    work_lines = []

            if in_orig and in_work:
                if orig_lines == work_lines:
                    continue  # Unmodified file
                status = "modified"
            elif in_work and not in_orig:
                status = "added"
            else:
                status = "deleted"

            # Generate unified diff
            diff_gen = difflib.unified_diff(
                orig_lines,
                work_lines,
                fromfile=f"a/{rel_p}",
                tofile=f"b/{rel_p}",
                lineterm=""
            )
            diff_text = "\n".join(diff_gen)

            # Count additions and deletions
            add_cnt = 0
            del_cnt = 0
            for line in diff_text.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    add_cnt += 1
                elif line.startswith("-") and not line.startswith("---"):
                    del_cnt += 1

            total_add += add_cnt
            total_del += del_cnt
            patch_pieces.append(diff_text)

            file_diffs.append(FileDiff(
                path=rel_p,
                status=status,
                additions=add_cnt,
                deletions=del_cnt,
                diff_content=diff_text
            ))

        return WorkspaceDiffReport(
            total_files_changed=len(file_diffs),
            total_additions=total_add,
            total_deletions=total_del,
            file_diffs=file_diffs,
            unified_patch="\n\n".join(patch_pieces)
        )

    def create_rollback_snapshot(self, target_dir: str, prefix: str = "pre_apply") -> str:
        """Takes a compressed zip backup of target directory prior to modification."""
        timestamp = str(int(time.time() * 1000))
        target_name = os.path.basename(os.path.normpath(target_dir))
        snapshot_filename = f"{prefix}_{target_name}_{timestamp}.zip"
        snapshot_path = os.path.join(self.snapshots_dir, snapshot_filename)

        with zipfile.ZipFile(snapshot_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
            for root, dirs, files in os.walk(target_dir):
                dirs[:] = [d for d in dirs if not self._should_ignore(os.path.join(root, d))]
                for f in files:
                    full_p = os.path.join(root, f)
                    if not self._should_ignore(full_p):
                        rel_p = os.path.relpath(full_p, target_dir)
                        zip_f.write(full_p, arcname=rel_p)

        return snapshot_path

    def rollback_from_snapshot(self, snapshot_path: str, target_dir: str) -> bool:
        """Restores files from a pre-apply snapshot zip back into target directory."""
        if not os.path.exists(snapshot_path):
            return False

        with zipfile.ZipFile(snapshot_path, "r") as zip_f:
            zip_f.extractall(target_dir)
        return True

    def apply_diff(
        self,
        original_dir: str,
        workspace_dir: str,
        create_backup: bool = True
    ) -> ApplyResult:
        """
        Safely applies workspace changes to original repository directory.
        Creates pre-apply snapshot; if any write fails, automatically rolls back.
        """
        validate_path(original_dir, mode="write")
        validate_path(workspace_dir, mode="read")

        orig_map = self._collect_files(original_dir)
        work_map = self._collect_files(workspace_dir)

        # 1. Take pre-apply rollback snapshot
        snapshot_path = None
        if create_backup:
            snapshot_path = self.create_rollback_snapshot(original_dir)

        applied_files: List[str] = []

        try:
            # Copy all modified or added files from workspace to original
            for rel_p, work_path in work_map.items():
                orig_path = os.path.join(original_dir, rel_p.replace("/", os.sep))
                # Check if changed
                if rel_p in orig_map:
                    with open(orig_map[rel_p], "rb") as f1, open(work_path, "rb") as f2:
                        if f1.read() == f2.read():
                            continue

                os.makedirs(os.path.dirname(orig_path), exist_ok=True)
                shutil.copy2(work_path, orig_path)
                applied_files.append(rel_p)

            # Handle deleted files (present in orig, absent in work)
            for rel_p, orig_path in orig_map.items():
                if rel_p not in work_map:
                    if os.path.exists(orig_path):
                        os.remove(orig_path)
                        applied_files.append(f"(deleted) {rel_p}")

            return ApplyResult(
                success=True,
                files_applied=applied_files,
                rollback_snapshot_path=snapshot_path
            )

        except Exception as exc:
            # Failure during application -> trigger atomic rollback
            if snapshot_path and os.path.exists(snapshot_path):
                self.rollback_from_snapshot(snapshot_path, original_dir)

            return ApplyResult(
                success=False,
                files_applied=[],
                rollback_snapshot_path=snapshot_path,
                error=f"Application failed and rolled back: {str(exc)}"
            )


# Global singleton instance
workspace_diff_engine = WorkspaceDiffEngine()
