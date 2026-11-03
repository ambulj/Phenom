"""
Developer Workspace Sentinel Schemas and Secret Sanitization.
Part of Phenom 8.0 Dual-Presence Developer Co-Pilot (DEV-01).
"""

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
import os
import re
import time

SECRET_FILE_PATTERNS: List[re.Pattern] = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r".*credentials.*", re.IGNORECASE),
    re.compile(r".*secret.*", re.IGNORECASE),
    re.compile(r".*\.(pem|key|pfx|p12|pkcs12)$", re.IGNORECASE),
    re.compile(r"^id_(rsa|ecdsa|ed25519)(\..+)?$", re.IGNORECASE),
    re.compile(r".*token.*", re.IGNORECASE),
    re.compile(r".*password.*", re.IGNORECASE),
]


def sanitize_workspace_file_path(path: str) -> Tuple[str, bool]:
    """
    Check if a file matches sensitive/secret patterns.
    If matched, return masked path string and True; otherwise original path and False.
    """
    filename = os.path.basename(path)
    for pattern in SECRET_FILE_PATTERNS:
        if pattern.match(filename) or pattern.match(path):
            return f"***{filename} (masked)***", True
    return path, False


class WorkspaceFileChange(BaseModel):
    path: str = Field(description="Relative path of file in repository")
    status: str = Field(description="Git status code: M, A, D, ??, etc.")
    lines_added: int = Field(default=0, description="Lines inserted")
    lines_deleted: int = Field(default=0, description="Lines removed")
    is_staged: bool = Field(default=False, description="True if staged in git index")
    is_secret: bool = Field(default=False, description="True if file matches secret pattern")


class DeveloperWorkspaceState(BaseModel):
    name: str = Field(..., description="Workspace folder name")
    root_path: str = Field(..., description="Absolute filesystem directory")
    ide_name: str = Field(..., description="Active IDE: vscode, cursor, windsurf, visual_studio, etc.")
    is_git: bool = Field(default=False, description="True if directory is a git repository")
    branch: Optional[str] = Field(default=None, description="Active branch or detached SHA")
    is_dirty: bool = Field(default=False, description="True if unstaged or staged modifications exist")
    lines_added: int = Field(default=0, description="Total worktree lines added")
    lines_deleted: int = Field(default=0, description="Total worktree lines deleted")
    untracked_count: int = Field(default=0, description="Number of untracked files")
    modified_files: List[WorkspaceFileChange] = Field(default_factory=list, description="Sanitized file change list")
    is_private: bool = Field(default=False, description="True if workspace contains confidential data")
    is_focused: bool = Field(default=True, description="True if IDE window is currently foreground")
    last_updated: float = Field(default_factory=time.time, description="Timestamp of last evaluation")
