"""
Phenom Obsidian Vault Manager
Operates on the Obsidian vault directory outside the code repository.
Default path: %USERPROFILE%\\Documents\\Phenom\\vault (configured in config.toml).
Writes notes, lecture summaries, and daily logs as plain Markdown.
Includes git versioning, nightly auto-push to private remote, collision refusal with code repo,
and one-time migration from legacy inside-repo vault.
"""

import os
import sys
import shutil
import hashlib
import tomllib
import subprocess
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

def find_repo_root() -> str:
    """Returns absolute path to Phenom repository root."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

def find_config_path() -> Optional[str]:
    """Locates config.toml."""
    env_cfg = os.environ.get("PHENOM_CONFIG")
    if env_cfg and os.path.exists(env_cfg):
        return os.path.abspath(env_cfg)
    repo_cfg = os.path.join(find_repo_root(), "config.toml")
    if os.path.exists(repo_cfg):
        return os.path.abspath(repo_cfg)
    cwd_cfg = os.path.join(os.getcwd(), "config.toml")
    if os.path.exists(cwd_cfg):
        return os.path.abspath(cwd_cfg)
    return None

def load_config() -> Dict[str, Any]:
    """Loads config.toml safely using tomllib."""
    cfg_path = find_config_path()
    if cfg_path and os.path.exists(cfg_path):
        try:
            with open(cfg_path, "rb") as f:
                return tomllib.load(f)
        except Exception:
            return {}
    return {}

def update_config_value(section: str, key: str, value: str) -> bool:
    """Updates a single key in config.toml while preserving comments and structure."""
    cfg_path = find_config_path() or os.path.join(find_repo_root(), "config.toml")
    try:
        lines = []
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        target_section = f"[{section}]"
        in_section = False
        key_found = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if stripped == target_section:
                    in_section = True
                else:
                    if in_section and not key_found:
                        new_lines.append(f'{key} = "{value}"\n')
                        key_found = True
                    in_section = False
            elif in_section and stripped.startswith(f"{key} ") or (in_section and stripped.startswith(f"{key}=")):
                line = f'{key} = "{value}"\n'
                key_found = True
            new_lines.append(line)

        if not key_found:
            if not any(l.strip() == target_section for l in lines):
                new_lines.append(f"\n{target_section}\n{key} = \"{value}\"\n")
            elif in_section:
                new_lines.append(f'{key} = "{value}"\n')

        with open(cfg_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    except Exception:
        return False

def get_configured_vault_path() -> str:
    """
    Returns the absolute path to the vault folder outside the code repo.
    Reads from config.toml, expands environment variables, never uses cwd.
    """
    cfg = load_config()
    raw_path = cfg.get("vault", {}).get("vault_path")
    if not raw_path:
        raw_path = os.environ.get("PHENOM_VAULT_PATH", "%USERPROFILE%\\Documents\\Phenom\\vault")
    expanded = os.path.expandvars(os.path.expanduser(raw_path))
    # Never use relative to cwd; ensure absolute path
    if not os.path.isabs(expanded):
        user_home = os.path.expanduser("~")
        expanded = os.path.join(user_home, "Documents", "Phenom", "vault")
    return os.path.abspath(os.path.realpath(expanded))

def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def get_legacy_vault_path() -> str:
    """Returns absolute path to legacy in-repo vault folder."""
    return os.path.abspath(os.path.join(find_repo_root(), "vault"))

def check_and_migrate_legacy_vault(
    old_path: Optional[str] = None,
    new_path: Optional[str] = None,
    remove_old: bool = False
) -> Dict[str, Any]:
    """
    One-time migration helper:
    Copies files from legacy in-repo vault to external vault.
    Verifies file counts and SHA-256 hashes of each file.
    Only removes old copy if remove_old is True.
    """
    src_dir = os.path.abspath(old_path or get_legacy_vault_path())
    dst_dir = os.path.abspath(new_path or get_configured_vault_path())

    if not os.path.exists(src_dir) or src_dir == dst_dir:
        return {
            "needed": False,
            "migrated": 0,
            "verified": True,
            "message": "No legacy vault migration needed."
        }

    # Gather files
    files_to_copy = []
    for root, _, files in os.walk(src_dir):
        for file in files:
            full_src = os.path.join(root, file)
            rel = os.path.relpath(full_src, src_dir)
            files_to_copy.append((full_src, rel))

    if not files_to_copy:
        return {
            "needed": False,
            "migrated": 0,
            "verified": True,
            "message": "Legacy vault exists but is empty."
        }

    os.makedirs(dst_dir, exist_ok=True)
    migrated_count = 0
    verified_hashes = {}

    for src_file, rel_path in files_to_copy:
        dst_file = os.path.join(dst_dir, rel_path)
        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
        shutil.copy2(src_file, dst_file)
        
        # Verify SHA-256 match
        src_hash = compute_file_sha256(src_file)
        dst_hash = compute_file_sha256(dst_file)
        if src_hash != dst_hash:
            raise ValueError(f"Checksum mismatch migrating {rel_path}: {src_hash} != {dst_hash}")
        verified_hashes[rel_path] = src_hash
        migrated_count += 1

    old_removed = False
    if remove_old:
        shutil.rmtree(src_dir)
        old_removed = True

    return {
        "needed": True,
        "migrated": migrated_count,
        "verified": True,
        "old_removed": old_removed,
        "hashes": verified_hashes,
        "message": f"Successfully migrated {migrated_count} files to {dst_dir}."
    }

class ObsidianVaultManager:
    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = os.path.abspath(os.path.realpath(vault_path or get_configured_vault_path()))
        os.makedirs(self.vault_path, exist_ok=True)
        os.makedirs(os.path.join(self.vault_path, "Daily Logs"), exist_ok=True)
        os.makedirs(os.path.join(self.vault_path, "Summaries"), exist_ok=True)
        os.makedirs(os.path.join(self.vault_path, "Notes"), exist_ok=True)
        self.ensure_git_repo()

    def ensure_git_repo(self) -> bool:
        """Initializes a separate git repository inside the vault folder if missing."""
        git_dir = os.path.join(self.vault_path, ".git")
        if not os.path.exists(git_dir):
            try:
                subprocess.run(
                    ["git", "init", "-b", "main"],
                    cwd=self.vault_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                # Create initial commit if empty
                gitignore = os.path.join(self.vault_path, ".gitignore")
                if not os.path.exists(gitignore):
                    with open(gitignore, "w", encoding="utf-8") as f:
                        f.write(".obsidian/workspace*\n*.tmp\n")
                subprocess.run(["git", "add", "."], cwd=self.vault_path, capture_output=True, check=False)
                subprocess.run(
                    ["git", "commit", "-m", "init: phenom vault repository"],
                    cwd=self.vault_path,
                    capture_output=True,
                    check=False
                )
                return True
            except Exception:
                return False
        return True

    def get_code_repo_url(self) -> Optional[str]:
        """Gets remote URL of the Phenom code repository for collision checks."""
        try:
            repo_root = find_repo_root()
            res = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return None

    def is_code_repo_collision(self, remote_url: str) -> bool:
        """
        Refuses if remote URL points to the Phenom code repository.
        Checks against current code repo remote origin, repo path, and known slug.
        """
        if not remote_url:
            return False
        clean_url = remote_url.strip().lower()
        if clean_url.endswith(".git"):
            clean_url = clean_url[:-4]

        # Check against Phenom code repo origin URL
        code_origin = self.get_code_repo_url()
        if code_origin:
            clean_code_origin = code_origin.strip().lower()
            if clean_code_origin.endswith(".git"):
                clean_code_origin = clean_code_origin[:-4]
            if clean_url == clean_code_origin:
                return True

        # Check against known repository indicators
        if "ambulj/phenom" in clean_url or "github.com/ambulj/phenom" in clean_url:
            return True

        # Check if remote_url is a local path to the code repo
        try:
            expanded = os.path.abspath(os.path.realpath(os.path.expandvars(remote_url)))
            code_root = os.path.abspath(os.path.realpath(find_repo_root()))
            if expanded == code_root or expanded.startswith(code_root + os.sep):
                return True
        except Exception:
            pass

        return False

    def get_remote_url(self) -> Optional[str]:
        """Returns remote origin URL of the vault git repository."""
        try:
            res = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                check=False
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        cfg = load_config()
        return cfg.get("vault", {}).get("remote_url", "")

    def set_remote_url(self, url: str) -> None:
        """
        Sets remote URL for the vault git repository.
        Refuses to push/set if the URL points to the Phenom code repository.
        """
        if self.is_code_repo_collision(url):
            raise ValueError(
                f"Refusing to configure remote URL: '{url}' points to the Phenom code repository. "
                "The vault must be backed up to a separate private repository."
            )

        self.ensure_git_repo()
        # Remove existing origin if set
        subprocess.run(["git", "remote", "remove", "origin"], cwd=self.vault_path, capture_output=True, check=False)
        if url.strip():
            subprocess.run(
                ["git", "remote", "add", "origin", url.strip()],
                cwd=self.vault_path,
                capture_output=True,
                check=True
            )
            update_config_value("vault", "remote_url", url.strip())

    def get_vault_token(self) -> Optional[str]:
        """
        Reads fine-grained token from Windows Credential Manager under 'Phenom/vault-git-token',
        or fallback to PHENOM_VAULT_GIT_TOKEN environment variable.
        """
        # Try Windows Credential Manager
        if sys.platform == "win32":
            try:
                import win32cred
                creds = win32cred.CredRead("Phenom/vault-git-token", win32cred.CRED_TYPE_GENERIC, 0)
                if creds and "CredentialBlob" in creds:
                    blob = creds["CredentialBlob"]
                    if isinstance(blob, bytes):
                        return blob.decode("utf-8")
                    return str(blob)
            except Exception:
                pass
        return os.environ.get("PHENOM_VAULT_GIT_TOKEN")

    def set_vault_token(self, token: str) -> bool:
        """Saves token into Windows Credential Manager under 'Phenom/vault-git-token'."""
        if not token:
            return False
        if sys.platform == "win32":
            try:
                import win32cred
                target = "Phenom/vault-git-token"
                credential = {
                    "Type": win32cred.CRED_TYPE_GENERIC,
                    "TargetName": target,
                    "UserName": "vault-backup",
                    "CredentialBlob": token.encode("utf-8"),
                    "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE
                }
                win32cred.CredWrite(credential, 0)
                return True
            except Exception:
                pass
        os.environ["PHENOM_VAULT_GIT_TOKEN"] = token
        return True

    def sanitize_text(self, text: str, token: Optional[str] = None) -> str:
        """Sanitizes sensitive tokens or credentials from output and log strings."""
        sanitized = text
        active_token = token or self.get_vault_token()
        if active_token and active_token in sanitized:
            sanitized = sanitized.replace(active_token, "[REDACTED_TOKEN]")
        import re
        sanitized = re.sub(r":([a-zA-Z0-9_\-\.]{15,})@", r":[REDACTED]@\g<0>", sanitized)
        sanitized = re.sub(r"ghp_[a-zA-Z0-9]{30,}", "[REDACTED_GH_TOKEN]", sanitized)
        sanitized = re.sub(r"github_pat_[a-zA-Z0-9_]{30,}", "[REDACTED_GH_PAT]", sanitized)
        return sanitized

    def test_remote_connection(self, remote_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Tests connection to the vault's remote git repository.
        Never logs the token; sanitizes all output.
        """
        url = remote_url or self.get_remote_url()
        if not url:
            return {"status": "error", "message": "No remote URL configured for vault."}

        if self.is_code_repo_collision(url):
            return {
                "status": "error",
                "message": "Collision detected: remote URL matches Phenom code repository."
            }

        token = self.get_vault_token()
        auth_url = url
        if token and ("github.com" in url or "gitlab.com" in url):
            if url.startswith("https://"):
                auth_url = f"https://oauth2:{token}@{url[8:]}"

        try:
            # Run ls-remote with 10s timeout
            res = subprocess.run(
                ["git", "ls-remote", "--heads", auth_url],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            sanitized_err = self.sanitize_text(res.stderr, token)
            if res.returncode == 0:
                return {"status": "success", "message": "Connection to vault remote succeeded."}
            else:
                return {
                    "status": "error",
                    "message": f"Connection failed (code {res.returncode}): {sanitized_err.strip()}"
                }
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Connection timed out after 10 seconds."}
        except Exception as e:
            sanitized_msg = self.sanitize_text(str(e), token)
            return {"status": "error", "message": f"Error testing remote connection: {sanitized_msg}"}

    def sync_vault_git(self, commit_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Stages all changes, creates a timestamped commit, and pushes to remote.
        Refuses if remote is Phenom code repo. Never logs the token.
        """
        self.ensure_git_repo()
        remote_url = self.get_remote_url()

        if remote_url and self.is_code_repo_collision(remote_url):
            raise PermissionError("Refusing to push: vault remote URL points to the Phenom code repository.")

        # Stage changes
        subprocess.run(["git", "add", "-A"], cwd=self.vault_path, capture_output=True, check=True)

        # Check if changes exist
        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.vault_path,
            capture_output=True,
            text=True,
            check=True
        )

        committed = False
        if status_res.stdout.strip():
            msg = commit_message or f"Phenom Vault Backup: {datetime.now(timezone.utc).isoformat()}"
            commit_res = subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                check=False
            )
            committed = (commit_res.returncode == 0)

        # Push if remote configured
        pushed = False
        push_output = ""
        token = self.get_vault_token()
        if remote_url:
            auth_url = remote_url
            if token and ("github.com" in remote_url or "gitlab.com" in remote_url):
                if remote_url.startswith("https://"):
                    auth_url = f"https://oauth2:{token}@{remote_url[8:]}"

            # Get current branch
            branch_res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                check=False
            )
            branch = branch_res.stdout.strip() or "main"

            try:
                push_res = subprocess.run(
                    ["git", "push", "-u", auth_url, branch],
                    cwd=self.vault_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False
                )
                pushed = (push_res.returncode == 0)
                raw_out = (push_res.stdout + " " + push_res.stderr).strip()
                push_output = self.sanitize_text(raw_out, token)
            except Exception as e:
                push_output = self.sanitize_text(str(e), token)

        return {
            "status": "success" if (committed or not status_res.stdout.strip()) else "warning",
            "committed": committed,
            "has_changes": bool(status_res.stdout.strip()),
            "pushed": pushed,
            "remote_url": remote_url or None,
            "output": push_output
        }

    def write_note(self, title: str, content: str, subfolder: str = "Notes") -> str:
        """Writes or updates a plain Markdown note in the vault."""
        clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
        if not clean_title.endswith(".md"):
            clean_title += ".md"

        target_dir = os.path.join(self.vault_path, subfolder)
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, clean_title)

        # Prepend YAML frontmatter if not present
        if not content.startswith("---"):
            now_iso = datetime.now(timezone.utc).isoformat()
            frontmatter = f"---\ntitle: {title}\ncreated: {now_iso}\nauthor: Phenom\n---\n\n"
            content = frontmatter + content

        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        return target_file

    def append_daily_log(self, entry: str) -> str:
        """Appends a timestamped log entry to today's daily log file."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        daily_file = os.path.join(self.vault_path, "Daily Logs", f"{date_str}.md")
        
        # If new file, initialize header
        if not os.path.exists(daily_file):
            header = f"# Daily Log: {date_str}\n\n"
            with open(daily_file, "w", encoding="utf-8") as f:
                f.write(header)

        entry_line = f"### [{time_str}]\n{entry.strip()}\n\n"
        with open(daily_file, "a", encoding="utf-8") as f:
            f.write(entry_line)

        return daily_file

    def read_note(self, title_or_path: str) -> str:
        """Reads note from the vault."""
        if os.path.isabs(title_or_path) and os.path.exists(title_or_path):
            with open(title_or_path, "r", encoding="utf-8") as f:
                return f.read()

        # Search by title
        target_name = title_or_path if title_or_path.endswith(".md") else f"{title_or_path}.md"
        for root, _, files in os.walk(self.vault_path):
            if target_name in files:
                with open(os.path.join(root, target_name), "r", encoding="utf-8") as f:
                    return f.read()

        raise FileNotFoundError(f"Note '{title_or_path}' not found in vault.")

    def list_notes(self) -> List[Dict[str, Any]]:
        """Lists all notes in the vault."""
        notes = []
        for root, _, files in os.walk(self.vault_path):
            # Skip .git directory
            if ".git" in root.split(os.sep):
                continue
            for file in files:
                if file.endswith(".md"):
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, self.vault_path)
                    notes.append({
                        "filename": file,
                        "rel_path": rel_p,
                        "size_bytes": os.path.getsize(full_p),
                        "mtime": os.path.getmtime(full_p)
                    })
        return notes

# Default vault path constant (evaluated at import time without cwd)
DEFAULT_VAULT_PATH = get_configured_vault_path()

# Global vault manager instance
vault_manager = ObsidianVaultManager()
