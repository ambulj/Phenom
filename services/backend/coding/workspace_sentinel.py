"""
Developer Workspace Sentinel Core Engine.
Ambiently monitors active developer IDEs, resolves workspace root paths,
and tracks Git state (branch, dirty files, line diffs) using microsecond
stat timestamp caching.

Part of Phenom 8.0 Dual-Presence Developer Co-Pilot (DEV-01).
"""

import asyncio
import os
import re
import subprocess
import time
from typing import Dict, List, Optional, Tuple, Callable

import psutil

try:
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

from services.backend.schemas.workspace import (
    DeveloperWorkspaceState,
    WorkspaceFileChange,
    sanitize_workspace_file_path,
)

IDE_EXECUTABLES: Dict[str, str] = {
    "code.exe": "vscode",
    "cursor.exe": "cursor",
    "windsurf.exe": "windsurf",
    "devenv.exe": "visual_studio",
    "pycharm64.exe": "pycharm",
    "pycharm.exe": "pycharm",
    "antigravity.exe": "antigravity",
}


class DeveloperWorkspaceSentinel:
    """
    Non-invasive ambient developer workspace sensor and Git state tracker.
    Uses Win32 foreground window and process detection without requiring
    editor extensions, caching Git stat timestamps to minimize CPU overhead.
    """

    def __init__(
        self,
        known_roots: Optional[List[str]] = None,
        poll_interval_active: float = 3.0,
        poll_interval_idle: float = 30.0,
        on_update_callback: Optional[Callable[[DeveloperWorkspaceState], None]] = None,
    ):
        self.known_roots: List[str] = [
            os.path.abspath(r) for r in (known_roots or ["C:\\Phenom"])
        ]
        self.poll_interval_active = poll_interval_active
        self.poll_interval_idle = poll_interval_idle
        self.on_update_callback = on_update_callback

        self._halted: bool = False
        self._last_state: Optional[DeveloperWorkspaceState] = None
        self._cached_stat_key: Optional[Tuple[int, int, int, int]] = None
        self._cached_git_state: Optional[Dict] = None
        self._loop_task: Optional[asyncio.Task] = None

    def halt(self) -> None:
        """Synchronously halts all sentinel polling (< 25ms SLA)."""
        self._halted = True
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()

    def reset(self) -> None:
        """Resets the sentinel to resume polling."""
        self._halted = False

    @property
    def is_halted(self) -> bool:
        return self._halted

    def get_current_state(self) -> Optional[DeveloperWorkspaceState]:
        return self._last_state

    def detect_active_ide_window(self) -> Optional[Tuple[str, str, int]]:
        """
        Detects if the foreground window belongs to a supported developer IDE.
        Returns: (ide_name, window_title, pid) or None if not an IDE window.
        """
        if not HAS_WIN32:
            return None

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid <= 0:
                return None

            proc = psutil.Process(pid)
            proc_name = proc.name().lower()

            if proc_name not in IDE_EXECUTABLES:
                return None

            ide_name = IDE_EXECUTABLES[proc_name]
            window_title = win32gui.GetWindowText(hwnd) or ""
            return ide_name, window_title, pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            return None

    def resolve_workspace_root(
        self, ide_name: str, window_title: str, pid: int
    ) -> Optional[str]:
        """
        Multi-tier resolution cascade to find the project root directory:
        Tier 1: Explicit directory in window title.
        Tier 2: Process CWD via psutil.
        Tier 3: Known configured project roots match.
        """
        # Tier 1: Parse title
        clean_title = window_title.strip()
        # Remove dirty indicator dot
        if clean_title.startswith("● ") or clean_title.startswith("* "):
            clean_title = clean_title[2:].strip()

        # Check for paths in title segments
        title_parts = [p.strip() for p in clean_title.split(" - ")]
        for part in title_parts:
            # Check if this part is an existing folder
            candidate = os.path.abspath(part)
            if os.path.isdir(candidate):
                return candidate

            # Check if part matches a known folder name inside known_roots
            for root in self.known_roots:
                if os.path.basename(root).lower() == part.lower():
                    return root
                sub_candidate = os.path.join(root, part)
                if os.path.isdir(sub_candidate):
                    return sub_candidate

        # Tier 2: Process CWD
        try:
            proc = psutil.Process(pid)
            cwd = proc.cwd()
            if cwd and os.path.isdir(cwd):
                # Avoid system / application installation directories
                cwd_lower = cwd.lower()
                if not any(
                    x in cwd_lower
                    for x in ["appdata", "system32", "program files", "windows"]
                ):
                    return os.path.abspath(cwd)
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            pass

        # Tier 3: Known project roots fallback
        for root in self.known_roots:
            if os.path.isdir(root):
                return root

        return None

    def _get_git_stat_key(self, repo_root: str) -> Optional[Tuple[int, int, int, int]]:
        """
        Microsecond stat of .git/HEAD and .git/index to detect repository modifications.
        Returns: (head_mtime_ns, head_size, index_mtime_ns, index_size) or None.
        """
        git_dir = os.path.join(repo_root, ".git")
        if not os.path.exists(git_dir):
            return None

        # Handle git submodule file pointer: "gitdir: ../../.git/modules/<name>"
        actual_git_dir = git_dir
        if os.path.isfile(git_dir):
            try:
                with open(git_dir, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content.startswith("gitdir:"):
                    rel_path = content.split(":", 1)[1].strip()
                    actual_git_dir = os.path.abspath(os.path.join(repo_root, rel_path))
            except Exception:
                actual_git_dir = git_dir

        head_path = os.path.join(actual_git_dir, "HEAD")
        index_path = os.path.join(actual_git_dir, "index")

        try:
            head_stat = os.stat(head_path) if os.path.exists(head_path) else None
            index_stat = os.stat(index_path) if os.path.exists(index_path) else None

            head_mtime = head_stat.st_mtime_ns if head_stat else 0
            head_size = head_stat.st_size if head_stat else 0
            index_mtime = index_stat.st_mtime_ns if index_stat else 0
            index_size = index_stat.st_size if index_stat else 0

            return head_mtime, head_size, index_mtime, index_size
        except OSError:
            return None

    def _execute_git_status_and_diff(self, repo_root: str) -> Dict:
        """
        Executes git status --porcelain=v1 -b and git diff --numstat to parse
        branch, dirty status, untracked counts, and line modifications.
        """
        branch = "unknown"
        is_dirty = False
        untracked_count = 0
        modified_files_dict: Dict[str, Dict] = {}

        try:
            # 1. Branch and status codes
            status_proc = subprocess.run(
                ["git", "status", "--porcelain=v1", "-b"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=3.0,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if status_proc.returncode == 0:
                lines = status_proc.stdout.splitlines()
                if lines:
                    header = lines[0]
                    if header.startswith("## "):
                        spec = header[3:].strip()
                        if "..." in spec:
                            branch = spec.split("...", 1)[0].strip()
                        elif "HEAD (no branch)" in spec:
                            # Detached HEAD: get short SHA
                            try:
                                sha_proc = subprocess.run(
                                    ["git", "rev-parse", "--short", "HEAD"],
                                    cwd=repo_root,
                                    capture_output=True,
                                    text=True,
                                    timeout=1.0,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                                )
                                branch = f"detached ({sha_proc.stdout.strip()})"
                            except Exception:
                                branch = "detached"
                        elif "Initial commit on" in spec:
                            branch = spec.split("Initial commit on", 1)[1].strip()
                        else:
                            branch = spec.split()[0].strip()

                    # Process file changes
                    for line in lines[1:]:
                        if not line or len(line) < 3:
                            continue
                        code = line[:2]
                        rel_path = line[3:].strip()
                        if " -> " in rel_path:
                            rel_path = rel_path.split(" -> ")[1].strip()

                        is_dirty = True
                        if code == "??":
                            untracked_count += 1
                        else:
                            is_staged = code[0] not in (" ", "?")
                            modified_files_dict[rel_path] = {
                                "status": code.strip(),
                                "is_staged": is_staged,
                                "lines_added": 0,
                                "lines_deleted": 0,
                            }

            # 2. Worktree line diffs
            diff_proc = subprocess.run(
                ["git", "diff", "--numstat"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=3.0,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if diff_proc.returncode == 0:
                for line in diff_proc.stdout.splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        added, deleted, path = parts[0].strip(), parts[1].strip(), parts[2].strip()
                        add_cnt = int(added) if added.isdigit() else 0
                        del_cnt = int(deleted) if deleted.isdigit() else 0
                        if path in modified_files_dict:
                            modified_files_dict[path]["lines_added"] += add_cnt
                            modified_files_dict[path]["lines_deleted"] += del_cnt
                        else:
                            modified_files_dict[path] = {
                                "status": "M",
                                "is_staged": False,
                                "lines_added": add_cnt,
                                "lines_deleted": del_cnt,
                            }
                        is_dirty = True

            # 3. Staged line diffs
            staged_proc = subprocess.run(
                ["git", "diff", "--cached", "--numstat"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=3.0,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if staged_proc.returncode == 0:
                for line in staged_proc.stdout.splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        added, deleted, path = parts[0].strip(), parts[1].strip(), parts[2].strip()
                        add_cnt = int(added) if added.isdigit() else 0
                        del_cnt = int(deleted) if deleted.isdigit() else 0
                        if path in modified_files_dict:
                            modified_files_dict[path]["lines_added"] += add_cnt
                            modified_files_dict[path]["lines_deleted"] += del_cnt
                            modified_files_dict[path]["is_staged"] = True
                        else:
                            modified_files_dict[path] = {
                                "status": "A",
                                "is_staged": True,
                                "lines_added": add_cnt,
                                "lines_deleted": del_cnt,
                            }
                        is_dirty = True

        except Exception:
            pass

        # Build sanitized file changes list
        total_added = 0
        total_deleted = 0
        changes: List[WorkspaceFileChange] = []

        for p, info in modified_files_dict.items():
            total_added += info["lines_added"]
            total_deleted += info["lines_deleted"]
            sanitized_p, is_sec = sanitize_workspace_file_path(p)
            changes.append(
                WorkspaceFileChange(
                    path=sanitized_p,
                    status=info["status"],
                    lines_added=info["lines_added"],
                    lines_deleted=info["lines_deleted"],
                    is_staged=info["is_staged"],
                    is_secret=is_sec,
                )
            )

        return {
            "branch": branch,
            "is_dirty": is_dirty or untracked_count > 0,
            "lines_added": total_added,
            "lines_deleted": total_deleted,
            "untracked_count": untracked_count,
            "modified_files": changes,
        }

    def inspect_workspace(
        self,
        workspace_path: str,
        ide_name: str = "vscode",
        is_focused: bool = True,
    ) -> DeveloperWorkspaceState:
        """
        Inspects a given workspace path, using stat timestamp caching for Git repos
        or cleanly returning basic directory state for non-Git workspaces.
        """
        name = os.path.basename(os.path.normpath(workspace_path)) or workspace_path
        git_dir = os.path.join(workspace_path, ".git")
        is_git = os.path.exists(git_dir)

        # Check for private repo / vault classification
        is_private = "vault" in workspace_path.lower() or "secret" in workspace_path.lower()

        if not is_git:
            return DeveloperWorkspaceState(
                name=name,
                root_path=workspace_path,
                ide_name=ide_name,
                is_git=False,
                branch=None,
                is_dirty=False,
                lines_added=0,
                lines_deleted=0,
                untracked_count=0,
                modified_files=[],
                is_private=is_private,
                is_focused=is_focused,
                last_updated=time.time(),
            )

        # Two-stage stat caching for Git workspaces
        stat_key = self._get_git_stat_key(workspace_path)
        if (
            stat_key is not None
            and self._cached_stat_key == stat_key
            and self._cached_git_state is not None
            and self._last_state is not None
            and self._last_state.root_path == workspace_path
        ):
            git_data = self._cached_git_state
        else:
            git_data = self._execute_git_status_and_diff(workspace_path)
            self._cached_stat_key = stat_key
            self._cached_git_state = git_data

        state = DeveloperWorkspaceState(
            name=name,
            root_path=workspace_path,
            ide_name=ide_name,
            is_git=True,
            branch=git_data["branch"],
            is_dirty=git_data["is_dirty"],
            lines_added=git_data["lines_added"],
            lines_deleted=git_data["lines_deleted"],
            untracked_count=git_data["untracked_count"],
            modified_files=git_data["modified_files"],
            is_private=is_private,
            is_focused=is_focused,
            last_updated=time.time(),
        )
        self._last_state = state
        return state

    def poll_once(self) -> Optional[DeveloperWorkspaceState]:
        """
        Runs one evaluation tick of the Developer Workspace Sentinel.
        """
        if self._halted:
            return None

        detection = self.detect_active_ide_window()
        if detection:
            ide_name, title, pid = detection
            root_path = self.resolve_workspace_root(ide_name, title, pid)
            if root_path:
                state = self.inspect_workspace(root_path, ide_name=ide_name, is_focused=True)
                if self.on_update_callback:
                    self.on_update_callback(state)
                return state

        # If not focused on an IDE window, mark current state as not focused if exists
        if self._last_state:
            self._last_state.is_focused = False
            return self._last_state

        return None

    async def run_sentinel_loop(self) -> None:
        """
        Background asyncio loop that continuously monitors developer workspace
        and adapts polling frequency based on focus and idle state.
        """
        while not self._halted:
            try:
                state = self.poll_once()
                interval = (
                    self.poll_interval_active
                    if (state and state.is_focused)
                    else self.poll_interval_idle
                )
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(self.poll_interval_active)


# Global singleton instance
workspace_sentinel = DeveloperWorkspaceSentinel()
