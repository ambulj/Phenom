"""
Phenom Obsidian Vault Manager
Operates on the 'vault/' directory inside the project folder.
Writes notes, lecture summaries, and daily logs as plain Markdown.
"""

import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DEFAULT_VAULT_PATH = os.path.abspath("vault")

class ObsidianVaultManager:
    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = vault_path or DEFAULT_VAULT_PATH
        os.makedirs(self.vault_path, exist_ok=True)
        os.makedirs(os.path.join(self.vault_path, "Daily Logs"), exist_ok=True)
        os.makedirs(os.path.join(self.vault_path, "Summaries"), exist_ok=True)
        os.makedirs(os.path.join(self.vault_path, "Notes"), exist_ok=True)

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

vault_manager = ObsidianVaultManager()
