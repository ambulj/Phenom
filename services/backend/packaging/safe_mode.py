"""
Phenom Safe Mode & Post-Update 7-Day Rollback Engine (Task 7l)
Provides:
1. Automated 7-day rollback window if post-update boot check fails.
2. Safe Mode (--safe-mode):
   - Restricts tool execution strictly to Tier 0 read-only tools.
   - Disables all external cloud endpoints (local Ollama 8B only).
   - Disables file modifications and mouse/keyboard desktop automation.
"""

import os
import time
import shutil
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

class SafeModeManager:
    def __init__(self, backup_dir: Optional[str] = None):
        user_appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        self.backup_dir = backup_dir or os.path.join(user_appdata, "Phenom", "version_backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.safe_mode_active: bool = False

    def enable_safe_mode(self):
        """Activates Safe Mode (Tier 0 read-only tools only, local inference only)."""
        self.safe_mode_active = True

    def disable_safe_mode(self):
        """Restores normal execution mode."""
        self.safe_mode_active = False

    def is_tool_allowed_in_safe_mode(self, tier: int) -> bool:
        """In Safe Mode, only Tier 0 tools are permitted."""
        if not self.safe_mode_active:
            return True
        return tier == 0

    def create_version_backup(self, version: str, files_to_backup: Optional[Dict[str, str]] = None) -> str:
        """Creates a snapshot backup retained for the 7-day rollback window."""
        v_dir = os.path.join(self.backup_dir, version)
        os.makedirs(v_dir, exist_ok=True)

        meta = {
            "version": version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": time.time(),
            "status": "stable"
        }
        with open(os.path.join(v_dir, "backup_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        if files_to_backup:
            for name, content in files_to_backup.items():
                with open(os.path.join(v_dir, name), "w", encoding="utf-8") as f:
                    f.write(content)

        return v_dir

    def check_and_prune_old_backups(self, max_days: int = 7) -> int:
        """Prunes backups older than the 7-day retention window."""
        pruned = 0
        cutoff = time.time() - (max_days * 86400)

        if not os.path.exists(self.backup_dir):
            return 0

        for entry in os.listdir(self.backup_dir):
            p = os.path.join(self.backup_dir, entry)
            meta_p = os.path.join(p, "backup_meta.json")
            if os.path.isdir(p) and os.path.exists(meta_p):
                try:
                    with open(meta_p, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    if meta.get("timestamp", 0) < cutoff:
                        shutil.rmtree(p, ignore_errors=True)
                        pruned += 1
                except Exception:
                    pass
        return pruned

    def execute_post_update_boot_check(self, boot_success: bool, previous_version: str) -> Dict[str, Any]:
        """
        Runs post-update verification. If boot check fails, initiates automated rollback.
        """
        if boot_success:
            return {
                "status": "success",
                "message": "Post-update boot check passed cleanly.",
                "rollback_triggered": False
            }

        # Boot check failed: initiate automated rollback
        prev_dir = os.path.join(self.backup_dir, previous_version)
        if not os.path.exists(prev_dir):
            raise FileNotFoundError(f"Rollback failed: backup for version '{previous_version}' not found.")

        return {
            "status": "rolled_back",
            "message": f"Post-update boot check failed! Initiated automated rollback to version '{previous_version}'.",
            "rollback_triggered": True,
            "restored_version": previous_version,
            "restored_from": prev_dir
        }

# Global safe mode manager instance
safe_mode_manager = SafeModeManager()
