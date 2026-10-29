#!/usr/bin/env python3
"""
Phenom Commit Guard & Secret Scanner
Blocks staging/committing of sensitive files and credentials:
- Blocked paths: vault/, Documents/Phenom/, user_data/, *.db, *.sqlite*, *.env, .env*, crash_logs/
- Secret patterns:
    * NVIDIA API Keys (nvapi-...)
    * Google API Keys (AIza...)
    * GitHub Tokens (ghp_..., github_pat_...)
    * Telegram Bot Tokens ([0-9]{8,10}:...)
    * Private Key Headers (-----BEGIN ... PRIVATE KEY-----)
Never outputs secret values to console or logs.
"""

import os
import sys
import re
import fnmatch
import subprocess
from typing import List, Tuple, Dict, Any, Optional

# Forbidden file and path patterns (case-insensitive)
BLOCKED_PATH_PATTERNS = [
    "vault/*",
    "*/vault/*",
    "vault",
    "Documents/Phenom/*",
    "*/Documents/Phenom/*",
    "user_data/*",
    "*/user_data/*",
    "*.db",
    "*.db-shm",
    "*.db-wal",
    "*.sqlite*",
    ".env",
    ".env*",
    "*.env",
    "*/.env",
    "*/.env*",
    "*/*.env",
    "crash_logs/*",
    "*/crash_logs/*"
]

# Regex patterns for detecting secrets
SECRET_PATTERNS = [
    ("NVIDIA API Key", re.compile(r"\bnvapi-[A-Za-z0-9_-]{20,}\b")),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z-_]{35}\b")),
    ("GitHub Personal Access Token", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("GitHub Fine-Grained Token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("Telegram Bot Token", re.compile(r"\b[0-9]{8,10}:[a-zA-Z0-9_-]{35}\b")),
    ("Private Key Header", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"))
]

# Files excluded from content scanning (e.g. scanner itself and scanner/privacy tests)
EXCLUDED_SCAN_FILES = {
    "scripts/scan_secrets.py",
    "services/backend/tests/test_secret_scan.py",
    "scripts/evaluate_privacy_router.py",
    "services/backend/tests/test_router_privacy_and_cascade.py"
}

def normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip()

def check_file_path(path: str) -> Optional[str]:
    """Returns violation reason if path matches a blocked pattern, else None."""
    norm = normalize_path(path)
    # Check exact basename or path matching blocked patterns
    basename = os.path.basename(norm)
    for pat in BLOCKED_PATH_PATTERNS:
        if fnmatch.fnmatch(norm, pat) or fnmatch.fnmatch(basename, pat):
            return f"Blocked file/directory pattern matched: '{pat}'"
        # Check components
        parts = norm.split("/")
        if any(fnmatch.fnmatch(p, pat.strip("/*")) for p in parts if p):
            return f"Blocked directory matched: '{pat}'"
    return None

def check_content(content: str, filename: str = "") -> List[Dict[str, Any]]:
    """Scans content for secret patterns. Returns list of matches with line numbers."""
    norm_fn = normalize_path(filename)
    if any(norm_fn.endswith(excluded) for excluded in EXCLUDED_SCAN_FILES):
        return []

    violations = []
    lines = content.splitlines()
    for idx, line in enumerate(lines, 1):
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                violations.append({
                    "line": idx,
                    "pattern_name": name,
                    "filename": filename
                })
    return violations

def is_binary_string(bytes_data: bytes) -> bool:
    return bool(b"\x00" in bytes_data[:1024])

def scan_file_on_disk(filepath: str) -> List[str]:
    """Scans a single file on disk for path and secret violations."""
    violations = []
    path_err = check_file_path(filepath)
    if path_err:
        violations.append(f"FORBIDDEN FILE: '{filepath}' ({path_err})")

    if not os.path.exists(filepath) or os.path.isdir(filepath):
        return violations

    try:
        with open(filepath, "rb") as f:
            data = f.read(5 * 1024 * 1024) # 5MB limit
        if is_binary_string(data):
            return violations

        text = data.decode("utf-8", errors="ignore")
        content_violations = check_content(text, filepath)
        for v in content_violations:
            violations.append(
                f"SECRET DETECTED: {v['pattern_name']} in '{v['filename']}' at line {v['line']} (value redacted)"
            )
    except Exception as e:
        violations.append(f"ERROR reading '{filepath}': {e}")

    return violations

def get_staged_files() -> List[str]:
    """Gets list of files currently staged in git index."""
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACM"],
            capture_output=True,
            check=True
        )
        return [f.decode("utf-8") for f in res.stdout.split(b"\0") if f]
    except Exception:
        return []

def scan_staged() -> int:
    """Scans staged files in git index before commit."""
    staged = get_staged_files()
    if not staged:
        return 0

    all_violations = []
    for filepath in staged:
        path_err = check_file_path(filepath)
        if path_err:
            all_violations.append(f"FORBIDDEN FILE: '{filepath}' ({path_err})")

        # Get staged content from git index
        try:
            res = subprocess.run(
                ["git", "show", f":{filepath}"],
                capture_output=True,
                check=False
            )
            if res.returncode == 0:
                data = res.stdout
                if not is_binary_string(data):
                    text = data.decode("utf-8", errors="ignore")
                    content_violations = check_content(text, filepath)
                    for v in content_violations:
                        all_violations.append(
                            f"SECRET DETECTED: {v['pattern_name']} in staged '{v['filename']}' at line {v['line']}"
                        )
        except Exception as e:
            all_violations.append(f"Error checking staged file '{filepath}': {e}")

    if all_violations:
        print("\n[PHENOM COMMIT GUARD] Commit rejected! Found sensitive files or secrets:")
        for v in all_violations:
            print(f"  [X] {v}")
        print("\nPlease remove the sensitive data or file from git staging before committing.\n")
        return 1

    return 0

def scan_all() -> int:
    """Scans all tracked files in git repository."""
    try:
        res = subprocess.run(
            ["git", "ls-files", "-z"],
            capture_output=True,
            check=True
        )
        files = [f.decode("utf-8") for f in res.stdout.split(b"\0") if f]
    except Exception as e:
        print(f"Error listing git files: {e}")
        return 1

    all_violations = []
    for filepath in files:
        violations = scan_file_on_disk(filepath)
        all_violations.extend(violations)

    if all_violations:
        print("\n[PHENOM SECRET SCANNER] Scan failed! Found sensitive files or secrets:")
        for v in all_violations:
            print(f"  [X] {v}")
        return 1

    print(f"[PHENOM SECRET SCANNER] SUCCESS: Scanned {len(files)} tracked files. No secrets or blocked files found.")
    return 0

def scan_file_list(files: List[str]) -> int:
    """Scans an explicit list of files (called by pre-commit framework)."""
    all_violations = []
    for filepath in files:
        violations = scan_file_on_disk(filepath)
        all_violations.extend(violations)

    if all_violations:
        print("\n[PHENOM COMMIT GUARD] Commit rejected! Found sensitive files or secrets:")
        for v in all_violations:
            print(f"  [X] {v}")
        return 1
    return 0

def main():
    if len(sys.argv) == 1 or "--staged" in sys.argv:
        sys.exit(scan_staged())
    elif "--all" in sys.argv:
        sys.exit(scan_all())
    else:
        # File list passed
        files = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
        sys.exit(scan_file_list(files))

if __name__ == "__main__":
    main()
