"""
Phenom Git Tools
Allows git operations on repositories.
Safety enforcement:
- Vault repo operations are Tier 0 (auto-approved).
- Code repo (and any other repo) operations are Tier 2 (require confirmation).
"""

import os
import re
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

class GitPrePushArgs(BaseModel):
    repo_path: str = Field(..., description="Path to the repository to audit before push.")
    target_branch: Optional[str] = Field(default="main", description="Target base branch for PR.")

def git_pre_push_preview(args: Dict[str, Any]) -> str:
    repo = args.get("repo_path", "")
    target = args.get("target_branch", "main")
    return f"Execute autonomous pre-push quality gate and draft PR description for repo '{repo}' targeting '{target}'."

def run_pre_push_gate(repo_path: str, target_branch: str = "main") -> Dict[str, Any]:
    resolved = os.path.abspath(os.path.realpath(os.path.expandvars(os.path.expanduser(repo_path))))
    if not os.path.exists(os.path.join(resolved, ".git")):
        raise ValueError(f"Path '{resolved}' is not a valid git repository.")

    branch_res = subprocess.run(["git", "branch", "--show-current"], cwd=resolved, capture_output=True, text=True, check=False)
    current_branch = branch_res.stdout.strip() or "HEAD"

    status_res = subprocess.run(["git", "status", "--porcelain"], cwd=resolved, capture_output=True, text=True, check=False)
    uncommitted = [line for line in status_res.stdout.splitlines() if line.strip()]

    log_res = subprocess.run(["git", "log", "-n", "5", "--oneline"], cwd=resolved, capture_output=True, text=True, check=False)
    commits = [c.strip() for c in log_res.stdout.splitlines() if c.strip()]

    diff_res = subprocess.run(["git", "diff", f"{target_branch}...HEAD"], cwd=resolved, capture_output=True, text=True, check=False)
    diff_text = diff_res.stdout if diff_res.returncode == 0 else ""
    
    secret_findings = []
    suspicious_patterns = [
        r"(?i)api[_-]?key\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
        r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}",
        r"-----BEGIN (RSA|EC|PRIVATE) KEY-----"
    ]
    for pat in suspicious_patterns:
        if re.search(pat, diff_text):
            secret_findings.append(f"Suspicious pattern matched: {pat}")

    quality_passed = len(secret_findings) == 0
    commit_bullets = "\n".join(f"- {c}" for c in commits) if commits else "- Minor modifications"
    check_secrets = "x" if quality_passed else " "
    check_tree = "x" if not uncommitted else " "
    verdict_text = "PASS - Ready for review & push" if quality_passed else "BLOCKED - Resolve security findings before push"

    pr_description = f"""## Pull Request: `{current_branch}` -> `{target_branch}`

### Summary of Changes
{commit_bullets}

### Quality Checklist
- [{check_secrets}] Zero Secrets Detected ({len(secret_findings)} findings)
- [{check_tree}] Working tree clean ({len(uncommitted)} uncommitted changes)
- [x] Automated pre-push validation completed

### Pre-Push Gate Verdict
**{verdict_text}**
"""

    return {
        "verdict": "PASS" if quality_passed else "BLOCKED",
        "current_branch": current_branch,
        "target_branch": target_branch,
        "uncommitted_count": len(uncommitted),
        "recent_commits": commits,
        "secret_findings": secret_findings,
        "pr_markdown": pr_description
    }

@registry.register(
    name="git_pre_push_gate",
    tier=2,
    description="Runs autonomous pre-push quality gate (secret scanning, diff audit) and generates structured PR description.",
    args_schema=GitPrePushArgs,
    preview_fn=git_pre_push_preview,
    can_remember_per_folder=False
)
def handle_git_pre_push_gate(repo_path: str, target_branch: Optional[str] = "main") -> Dict[str, Any]:
    return run_pre_push_gate(repo_path, target_branch or "main")
