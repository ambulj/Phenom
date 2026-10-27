"""
Phenom Learned Rules Manager
Stores, lists, edits, and deletes learned rules.
Rules can be extracted from user corrections or added directly.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from services.backend.memory.db import encrypted_db

class LearnedRulesManager:
    def __init__(self, db=None):
        self.db = db or encrypted_db

    def add_rule(self, rule_text: str, rule_id: Optional[str] = None) -> Dict[str, Any]:
        r_id = rule_id or str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        conn = self.db.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO learned_rules (id, rule_text, created_at, enabled) VALUES (?, ?, ?, 1);",
                (r_id, rule_text.strip(), ts)
            )
        conn.close()
        return {"id": r_id, "rule_text": rule_text.strip(), "created_at": ts, "enabled": True}

    def list_rules(self, active_only: bool = False) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        query = "SELECT id, rule_text, created_at, enabled FROM learned_rules"
        if active_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY created_at DESC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "rule_text": r[1], "created_at": r[2], "enabled": bool(r[3])}
            for r in rows
        ]

    def edit_rule(self, rule_id: str, new_text: str, enabled: Optional[bool] = None) -> bool:
        conn = self.db.get_connection()
        with conn:
            if enabled is not None:
                cursor = conn.execute(
                    "UPDATE learned_rules SET rule_text = ?, enabled = ? WHERE id = ?;",
                    (new_text.strip(), 1 if enabled else 0, rule_id)
                )
            else:
                cursor = conn.execute(
                    "UPDATE learned_rules SET rule_text = ? WHERE id = ?;",
                    (new_text.strip(), rule_id)
                )
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def delete_rule(self, rule_id: str) -> bool:
        conn = self.db.get_connection()
        with conn:
            cursor = conn.execute("DELETE FROM learned_rules WHERE id = ?;", (rule_id,))
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def format_rules_for_prompt(self) -> str:
        rules = self.list_rules(active_only=True)
        if not rules:
            return ""
        return "\n".join([f"- {r['rule_text']}" for r in rules])

learned_rules = LearnedRulesManager()
