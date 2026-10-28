"""
Phenom Git Tools
Allows git operations on repositories.
Safety enforcement:
- Vault repo operations are Tier 0 (auto-approved).
- Code repo (and any other repo) operations are Tier 2 (require confirmation).
"""

import os
import subprocess
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from services.backend.schemas.protocol import RiskTier
from services.backend.safety.registry import registry
from services.backend.memory.vault import vault_manager

class GitCommandArgs(BaseModel):
    repo_path: str = Field(..., description="Absolute or relative path to the git repository.")
    command: str = Field(..., description="Git command to run (e.g. status, diff, log, add, commit).")
    args: Optional[List[str]] = Field(default=None, description="Optional command-line arguments.")

def git_command_preview(args: Dict[str, Any]) -> str:
    repo = args.get("repo_path", "")
    cmd = args.get("command", "")
    extra = " ".join(args.get("args") or [])
    full = f"git {cmd} {extra}".strip()
    return f"Execute git operation: '{full}' in repository '{repo}'"

def git_command_tier(args: Dict[str, Any]) -> RiskTier:
    """
    Dynamic Tier Resolver:
    - Vault repository is Tier 0 (auto-approved).
    - Phenom code repository or any other location is Tier 2 (requires confirmation).
    """
    raw_path = args.get("repo_path", "")
    if not raw_path:
        return 2

    try:
        resolved = os.path.abspath(os.path.realpath(os.path.expandvars(os.path.expanduser(raw_path))))
        vault_resolved = os.path.abspath(os.path.realpath(vault_manager.vault_path))
        if resolved == vault_resolved or resolved.startswith(vault_resolved + os.sep):
            return 0  # Tier 0 for vault repo
    except Exception:
        pass

    return 2  # Tier 2 for code repo or any external repo

def run_git_command(repo_path: str, command: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
    resolved = os.path.abspath(os.path.realpath(os.path.expandvars(os.path.expanduser(repo_path))))
    if not os.path.exists(os.path.join(resolved, ".git")):
        raise ValueError(f"Path '{resolved}' is not a valid git repository.")

    clean_cmd = command.strip().lower()
    cmd_list = ["git", clean_cmd]
    if args:
        cmd_list.extend([str(a) for a in args])

    res = subprocess.run(
        cmd_list,
        cwd=resolved,
        capture_output=True,
        text=True,
        timeout=30,
        check=False
    )
    return {
        "command": " ".join(cmd_list),
        "exit_code": res.returncode,
        "stdout": vault_manager.sanitize_text(res.stdout),
        "stderr": vault_manager.sanitize_text(res.stderr)
    }

@registry.register(
    name="git_command",
    tier=git_command_tier,
    description="Executes a git command. Tier 0 for Phenom vault repository; Tier 2 for code repository and other locations.",
    args_schema=GitCommandArgs,
    preview_fn=git_command_preview,
    can_remember_per_folder=False
)
def handle_git_command(repo_path: str, command: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
    return run_git_command(repo_path, command, args)
