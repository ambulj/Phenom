"""
Phenom Remembered Approvals Manager
Allows remembering Tier 1 user approvals per specific folder.
Strict Safety Invariants:
1. Never applies to Tier 2 (destructive/external) or Tier 3 (blocked).
2. Never applies outside the explicitly approved folder path.
3. User can list and revoke remembered choices at any time.
"""

import os
import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from services.backend.schemas.protocol import RiskTier

class ApprovalManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.abspath("services/backend/data/phenom.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS approvals_remembered (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool TEXT NOT NULL,
                folder_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(tool, folder_path)
            );
            """)
            conn.commit()

    def is_remembered(self, tool: str, tier: RiskTier, target_path: Optional[str]) -> bool:
        """Returns True only if the tool is Tier 1 and the folder is remembered."""
        if tier != 1 or not target_path:
            return False

        norm_target = os.path.abspath(target_path)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT folder_path FROM approvals_remembered WHERE tool = ?;", (tool,))
            for (folder,) in cursor.fetchall():
                norm_folder = os.path.abspath(folder)
                if norm_target == norm_folder or norm_target.startswith(norm_folder + os.sep):
                    return True
        return False

    def remember(self, tool: str, tier: RiskTier, folder_path: str):
        if tier != 1:
            raise PermissionError(f"Cannot remember choices for Tier {tier}. Only Tier 1 is allowed.")
        norm_folder = os.path.abspath(folder_path)
        ts = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            INSERT OR REPLACE INTO approvals_remembered (tool, folder_path, created_at)
            VALUES (?, ?, ?);
            """, (tool, norm_folder, ts))
            conn.commit()

    def revoke(self, approval_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM approvals_remembered WHERE id = ?;", (approval_id,))
            conn.commit()

    def list_all(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM approvals_remembered ORDER BY created_at DESC;")
            return [dict(row) for row in cursor.fetchall()]

# Global Approvals Manager instance
approvals = ApprovalManager()
