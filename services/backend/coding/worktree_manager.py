"""
Ephemeral Git Worktree Manager for Isolated Diagnostics & Self-Healing.
Creates temporary worktree sandboxes under .phenom_worktrees/ with zero risk
of dirtying the user's primary working directory.

Part of Phenom 20.0 Sovereign Autonomous Developer (DEV-02.1, SAF-01, SAF-02).
"""

import os
import shutil
import subprocess
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.coding.worktree")


class WorktreeSandbox(BaseModel):
    sandbox_id: str = Field(..., description="Unique sandbox identifier")
    branch_name: str = Field(..., description="Git branch attached to this worktree")
    path: str = Field(..., description="Absolute path to isolated worktree filesystem")
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")
    commit_ish: str = Field(default="HEAD", description="Source commit/branch")
    is_active: bool = Field(default=True, description="Whether worktree is currently active")
    is_git_worktree: bool = Field(default=True, description="Whether created via git worktree or filesystem mirror")


class WorktreeManager:
    """
    Manages isolated git worktrees for safe test execution and diagnostic self-healing.
    Guarantees user working directory isolation under Rule 1 and Rule 7.
    """

    def __init__(self, repo_root: Optional[str] = None):
        if repo_root is None:
            # Default to repo root (c:\Phenom)
            self.repo_root = Path(__file__).resolve().parent.parent.parent.parent
        else:
            self.repo_root = Path(repo_root).resolve()

        self.worktree_base_dir = self.repo_root / ".phenom_worktrees"
        self._sandboxes: Dict[str, WorktreeSandbox] = {}
        self._ensure_base_dir()

    def _ensure_base_dir(self) -> None:
        try:
            self.worktree_base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create worktree base directory: {e}")

    def create_worktree(
        self,
        commit_ish: str = "HEAD",
        sandbox_id: Optional[str] = None,
        branch_name: Optional[str] = None,
    ) -> WorktreeSandbox:
        """
        Creates an isolated git worktree attached to a new ephemeral branch.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Worktree operation halted.")

        sid = sandbox_id or f"wt_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        bname = branch_name or f"phenom-wt-{sid}"
        target_path = self.worktree_base_dir / sid

        # Check if already registered
        if sid in self._sandboxes and self._sandboxes[sid].is_active:
            return self._sandboxes[sid]

        # Ensure base directory exists
        self._ensure_base_dir()

        is_git = True
        try:
            # Attempt git worktree add
            cmd = ["git", "worktree", "add", "-b", bname, str(target_path), commit_ish]
            res = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=20,
            )
            if res.returncode != 0:
                logger.warning(f"git worktree add returned non-zero ({res.stderr.strip()}). Falling back to directory mirror.")
                is_git = False
        except Exception as e:
            logger.warning(f"git worktree creation failed ({e}). Falling back to directory mirror.")
            is_git = False

        if not is_git:
            # Filesystem mirror fallback (for bare environments or detached tests)
            target_path.mkdir(parents=True, exist_ok=True)
            # Copy backend services and config files
            for item in ["services", "apps", "package.json", "tsconfig.json", "vite.config.ts"]:
                src = self.repo_root / item
                dst = target_path / item
                if src.is_dir():
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "node_modules", ".git", ".phenom_*"))
                elif src.is_file():
                    shutil.copy2(src, dst)

        sandbox = WorktreeSandbox(
            sandbox_id=sid,
            branch_name=bname,
            path=str(target_path.resolve()),
            created_at=time.time(),
            commit_ish=commit_ish,
            is_active=True,
            is_git_worktree=is_git,
        )
        self._sandboxes[sid] = sandbox
        return sandbox

    def remove_worktree(self, sandbox_id: str, force: bool = True) -> bool:
        """
        Safely removes a worktree sandbox and cleans up its ephemeral branch.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Worktree operation halted.")

        sandbox = self._sandboxes.get(sandbox_id)
        target_path = Path(sandbox.path) if sandbox else self.worktree_base_dir / sandbox_id

        if not target_path.exists() and sandbox is None:
            return False

        is_git = sandbox.is_git_worktree if sandbox else True
        success = True

        if is_git:
            try:
                cmd = ["git", "worktree", "remove", "--force", str(target_path)]
                subprocess.run(cmd, cwd=str(self.repo_root), capture_output=True, timeout=15)
            except Exception as e:
                logger.warning(f"git worktree remove failed: {e}")
                success = False

            # Delete branch if specified
            if sandbox and sandbox.branch_name:
                try:
                    subprocess.run(
                        ["git", "branch", "-D", sandbox.branch_name],
                        cwd=str(self.repo_root),
                        capture_output=True,
                        timeout=10,
                    )
                except Exception:
                    pass

        # Cleanup residual directory if still present
        if target_path.exists():
            try:
                shutil.rmtree(target_path, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Residual directory cleanup error: {e}")

        # Update in-memory registry
        if sandbox_id in self._sandboxes:
            self._sandboxes[sandbox_id].is_active = False
            del self._sandboxes[sandbox_id]

        return success

    def list_worktrees(self) -> List[WorktreeSandbox]:
        """
        Lists all active worktrees.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Worktree operation halted.")
        return [sb for sb in self._sandboxes.values() if sb.is_active]

    def get_worktree(self, sandbox_id: str) -> Optional[WorktreeSandbox]:
        """
        Retrieves a worktree sandbox by ID.
        """
        return self._sandboxes.get(sandbox_id)

    def prune_worktrees(self, max_age_seconds: int = 3600) -> int:
        """
        Prunes all expired or orphaned worktrees older than max_age_seconds.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Worktree operation halted.")
        now = time.time()
        pruned_count = 0

        # Prune known tracked sandboxes
        to_prune = [
            sid for sid, sb in self._sandboxes.items()
            if (now - sb.created_at) > max_age_seconds
        ]
        for sid in to_prune:
            if self.remove_worktree(sid, force=True):
                pruned_count += 1

        # Check for untracked leftover directories
        if self.worktree_base_dir.exists():
            for child in self.worktree_base_dir.iterdir():
                if child.is_dir() and child.name not in self._sandboxes:
                    try:
                        mtime = child.stat().st_mtime
                        if (now - mtime) > max_age_seconds:
                            shutil.rmtree(child, ignore_errors=True)
                            pruned_count += 1
                    except Exception:
                        pass

        # Run git worktree prune
        try:
            subprocess.run(["git", "worktree", "prune"], cwd=str(self.repo_root), capture_output=True, timeout=10)
        except Exception:
            pass

        return pruned_count


# Global singleton
worktree_manager = WorktreeManager()
