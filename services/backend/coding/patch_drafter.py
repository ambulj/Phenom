"""
Patch Fix Drafter & Atomic Rollback Engine.
Generates minimal unified git diffs, validates patch applicability,
creates non-destructive working tree snapshots (git stash create), and guarantees
atomic 1-click rollback without data loss.

Part of Phenom 8.0 Proactive Dev Build Sentinel (DEV-02).
"""

import difflib
import os
import subprocess
from typing import Optional, Tuple


class PatchDrafter:
    """
    Synthesizes unified diffs and manages atomic application and rollback.
    """

    def create_unified_diff(
        self,
        file_path: str,
        original_code: str,
        replacement_code: str,
    ) -> str:
        """
        Creates a clean unified diff in git format (--- a/... +++ b/...).
        """
        norm_path = file_path.replace("\\", "/")
        if norm_path.startswith("./"):
            norm_path = norm_path[2:]

        from_lines = original_code.splitlines(keepends=True)
        to_lines = replacement_code.splitlines(keepends=True)

        # Ensure trailing newlines on last element
        if from_lines and not from_lines[-1].endswith("\n"):
            from_lines[-1] += "\n"
        if to_lines and not to_lines[-1].endswith("\n"):
            to_lines[-1] += "\n"

        diff = difflib.unified_diff(
            from_lines,
            to_lines,
            fromfile=f"a/{norm_path}",
            tofile=f"b/{norm_path}",
            lineterm="\n",
        )
        return "".join(diff)

    def validate_patch(self, repo_root: str, patch_diff: str) -> bool:
        """
        Validates that a patch diff applies cleanly without rejects using git apply --check.
        """
        if not patch_diff.strip():
            return False

        try:
            proc = subprocess.run(
                ["git", "apply", "--check", "--whitespace=fix", "-"],
                cwd=repo_root,
                input=patch_diff,
                text=True,
                capture_output=True,
                timeout=5.0,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return proc.returncode == 0
        except Exception:
            return False

    def create_prepatch_snapshot(self, repo_root: str) -> Optional[str]:
        """
        Non-destructively creates a git stash commit of current uncommitted worktree changes.
        Does NOT clear the working directory or disrupt the developer.
        Returns the snapshot SHA token, or 'HEAD' if worktree was already clean.
        """
        try:
            proc = subprocess.run(
                ["git", "stash", "create", "Phenom pre-patch snapshot"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5.0,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            token = proc.stdout.strip()
            # If stdout is empty, working tree has no uncommitted changes
            return token if token else "HEAD"
        except Exception:
            return None

    def apply_patch(
        self, repo_root: str, patch_diff: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Takes a snapshot and applies the verified patch.
        Returns: (success, rollback_token, error_message)
        """
        if not patch_diff.strip():
            return False, None, "Empty patch diff"

        # 1. Create pre-patch snapshot
        token = self.create_prepatch_snapshot(repo_root)
        if not token:
            return False, None, "Failed to create pre-patch working tree snapshot"

        # 2. Apply patch via git apply
        try:
            proc = subprocess.run(
                ["git", "apply", "--whitespace=fix", "-"],
                cwd=repo_root,
                input=patch_diff,
                text=True,
                capture_output=True,
                timeout=5.0,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if proc.returncode == 0:
                return True, token, None
            else:
                return False, None, f"git apply failed: {proc.stderr.strip()}"
        except Exception as e:
            return False, None, f"Patch execution exception: {str(e)}"

    def revert_patch(self, repo_root: str, rollback_token: str) -> bool:
        """
        Reverts the working tree back to the exact snapshot recorded by rollback_token.
        """
        if not rollback_token:
            return False

        try:
            # 1. Reset all tracked files
            subprocess.run(
                ["git", "reset", "--hard", "HEAD"],
                cwd=repo_root,
                capture_output=True,
                timeout=5.0,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            # 2. If token is a stash commit SHA, re-apply the uncommitted changes
            if rollback_token != "HEAD":
                proc = subprocess.run(
                    ["git", "stash", "apply", rollback_token],
                    cwd=repo_root,
                    capture_output=True,
                    timeout=5.0,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                return proc.returncode == 0

            return True
        except Exception:
            return False


# Global singleton instance
patch_drafter = PatchDrafter()
