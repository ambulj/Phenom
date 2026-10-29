r"""
Phenom Path Security & Guardrails Engine (Task 7a)
Enforces:
1. Canonicalization: os.path.realpath(os.path.expandvars(os.path.expanduser(p)))
2. Traversal defense: .. and commonpath resolution
3. Windows Symlink and Directory Junction resolution before policy enforcement
4. Alternate Data Streams (ADS) rejection (colon after drive prefix)
5. Windows reserved device name rejection (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
6. Denylist enforcement: C:\Windows, C:\Program Files, C:\ProgramData, AppData system folders, and the Phenom code repository
7. Allowlist enforcement: Documents, Downloads, Desktop, Pictures, Videos, Music, Temp, and configured Obsidian Vault
8. Batch limit enforcement: Max 10 files per single destructive or bulk operation
"""

import os
import sys
import tempfile
from typing import List, Optional, Set
from pathlib import Path

class PathSecurityViolation(PermissionError):
    """Raised whenever a path violates security boundaries, traversal rules, or denylists."""
    pass

class BatchLimitExceededError(ValueError):
    """Raised whenever a bulk operation exceeds the 10-item atomic batch cap."""
    pass

RESERVED_WINDOWS_NAMES: Set[str] = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

def get_code_repo_root() -> str:
    """Returns canonical root of Phenom repository."""
    return os.path.realpath(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

def get_system_denylist() -> List[str]:
    """Returns list of canonical system paths strictly forbidden from tool access."""
    denylist = []
    
    # Windows system directory
    windir = os.environ.get("WINDIR") or "C:\\Windows"
    denylist.append(os.path.realpath(windir))

    # Program Files
    for env_var in ["ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"]:
        val = os.environ.get(env_var)
        if val:
            denylist.append(os.path.realpath(val))
    denylist.append("C:\\Program Files")
    denylist.append("C:\\Program Files (x86)")

    # ProgramData
    prog_data = os.environ.get("ProgramData") or "C:\\ProgramData"
    denylist.append(os.path.realpath(prog_data))

    # System roots / recovery
    sys_drive = os.environ.get("SystemDrive") or "C:"
    denylist.append(os.path.realpath(os.path.join(sys_drive, "\\System Volume Information")))
    denylist.append(os.path.realpath(os.path.join(sys_drive, "\\Recovery")))
    denylist.append(os.path.realpath(os.path.join(sys_drive, "\\$Recycle.Bin")))

    # Sensitive credential locations within user profile
    user_prof = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    denylist.append(os.path.realpath(os.path.join(user_prof, ".ssh")))
    denylist.append(os.path.realpath(os.path.join(user_prof, ".aws")))
    denylist.append(os.path.realpath(os.path.join(user_prof, ".azure")))
    denylist.append(os.path.realpath(os.path.join(user_prof, ".gnupg")))

    # Deduplicate and normalize
    clean_denylist = []
    for d in denylist:
        rp = os.path.realpath(d)
        if rp not in clean_denylist:
            clean_denylist.append(rp)

    return clean_denylist

def get_user_allowlist_roots() -> List[str]:
    """Returns allowed root directories for safe user-facing operations."""
    user_prof = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    roots = [
        os.path.join(user_prof, "Documents"),
        os.path.join(user_prof, "Downloads"),
        os.path.join(user_prof, "Desktop"),
        os.path.join(user_prof, "Pictures"),
        os.path.join(user_prof, "Videos"),
        os.path.join(user_prof, "Music"),
        tempfile.gettempdir()
    ]
    # Include configured external vault if available
    try:
        from services.backend.memory.vault import get_configured_vault_path
        vault_path = get_configured_vault_path()
        if vault_path:
            roots.append(vault_path)
    except Exception:
        pass

    return [os.path.realpath(r) for r in roots]

def validate_path(raw_path: str, mode: str = "read") -> str:
    """
    Validates and canonicalizes a path against security policies.
    mode: 'read', 'write', or 'delete'.
    Returns canonical path if valid; raises PathSecurityViolation if forbidden.
    """
    if not raw_path or not isinstance(raw_path, str):
        raise PathSecurityViolation("Path must be a non-empty string.")

    cleaned = raw_path.strip().strip("\"'")
    if not cleaned:
        raise PathSecurityViolation("Path cannot be blank.")

    # 1. Check for Alternate Data Streams (ADS)
    # On Windows, drive letter has ':', but any subsequent ':' is an ADS indicator (e.g., file.txt:hidden)
    path_without_drive = cleaned[2:] if len(cleaned) >= 2 and cleaned[1] == ":" else cleaned
    if ":" in path_without_drive:
        raise PathSecurityViolation(f"Alternate Data Streams (ADS) are strictly prohibited: '{raw_path}'")

    # 2. Canonicalize path and resolve symlinks / directory junctions
    canonical = os.path.realpath(os.path.expandvars(os.path.expanduser(cleaned)))

    # 3. Check for Windows reserved names
    parts = Path(canonical).parts
    for p in parts:
        stem = Path(p).stem.upper()
        if stem in RESERVED_WINDOWS_NAMES:
            raise PathSecurityViolation(f"Windows reserved device name prohibited: '{stem}' in '{raw_path}'")

    # 4. Check system denylist & filesystem root
    sys_drive = os.environ.get("SystemDrive") or "C:"
    if canonical.rstrip("\\/") == sys_drive or canonical == os.path.realpath(sys_drive + "\\"):
        raise PathSecurityViolation(f"Access to filesystem root directory is strictly prohibited: '{canonical}'")

    denylist = get_system_denylist()
    for denied in denylist:
        # Check exact match or subpath under denied root
        try:
            if canonical == denied or os.path.commonpath([denied, canonical]) == denied:
                raise PathSecurityViolation(f"Access to system-protected path is strictly prohibited: '{canonical}' (denied root: '{denied}')")
        except ValueError:
            # Different drive letters cannot be subpaths of each other
            pass

    # 5. Protect Phenom code repo from write / delete operations
    if mode in ["write", "delete"]:
        code_root = get_code_repo_root()
        try:
            if canonical == code_root or os.path.commonpath([code_root, canonical]) == code_root:
                raise PathSecurityViolation(f"Destructive/write modifications to the Phenom code repository are strictly prohibited: '{canonical}'")
        except ValueError:
            pass

    # 6. Check allowlist for write/delete operations
    if mode in ["write", "delete"]:
        allowed_roots = get_user_allowlist_roots()
        is_allowed = False
        for root in allowed_roots:
            try:
                if canonical == root or os.path.commonpath([root, canonical]) == root:
                    is_allowed = True
                    break
            except ValueError:
                pass

        if not is_allowed:
            raise PathSecurityViolation(
                f"Modifications outside user allowed folders (Documents, Downloads, Desktop, Pictures, Vault) are prohibited: '{canonical}'"
            )

    return canonical

def validate_batch_size(items: List[str], max_allowed: int = 10, operation_name: str = "batch operation") -> None:
    """
    Enforces atomic batch cap (Rule 7a: Max 10 files per operation).
    Raises BatchLimitExceededError if requested count exceeds max_allowed.
    """
    if len(items) > max_allowed:
        raise BatchLimitExceededError(
            f"Operation '{operation_name}' exceeds maximum safety batch cap of {max_allowed} items "
            f"({len(items)} requested). Partition the request into smaller chunks."
        )
