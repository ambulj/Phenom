"""
Phenom Action Log
Maintains an immutable record of every tool execution, security tier, confirmation decision,
and outcome. Ensures privacy by automatically redacting sensitive argument values.
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from services.backend.schemas.protocol import RiskTier, DecisionType

SENSITIVE_KEYS = {"password", "secret", "token", "key", "api_key", "credential", "auth", "body", "content"}

def redact_arguments(args: Dict[str, Any]) -> str:
    """Recursively redacts confidential information from logged tool arguments."""
    redacted = {}
    for k, v in args.items():
        if any(sens in k.lower() for sens in SENSITIVE_KEYS):
            redacted[k] = "[REDACTED]"
        elif isinstance(v, str) and len(v) > 250:
            redacted[k] = v[:100] + f"... [TRUNCATED {len(v)} chars]"
        elif isinstance(v, dict):
            redacted[k] = json.loads(redact_arguments(v))
        else:
            redacted[k] = v
    return json.dumps(redacted)

class ActionLogManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.abspath("services/backend/data/phenom.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS action_log (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                tool TEXT NOT NULL,
                tier INTEGER NOT NULL,
                arguments_redacted TEXT NOT NULL,
                decision TEXT NOT NULL,
                result_status TEXT NOT NULL,
                error TEXT,
                undo_token TEXT
            );
            """)
            conn.commit()

    def log_action(
        self,
        tool: str,
        tier: RiskTier,
        args: Dict[str, Any],
        decision: DecisionType,
        result_status: str,
        source: str = "desktop",
        error: Optional[str] = None,
        undo_token: Optional[str] = None,
        log_id: Optional[str] = None
    ) -> Dict[str, Any]:
        entry_id = log_id or str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        redacted_args_str = redact_arguments(args)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            INSERT INTO action_log (id, timestamp, source, tool, tier, arguments_redacted, decision, result_status, error, undo_token)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (entry_id, ts, source, tool, tier, redacted_args_str, decision, result_status, error, undo_token))
            conn.commit()

        return {
            "log_id": entry_id,
            "timestamp": ts,
            "source": source,
            "tool": tool,
            "tier": tier,
            "arguments_redacted": redacted_args_str,
            "decision": decision,
            "result_status": result_status,
            "error": error,
            "undo_token": undo_token
        }

    def list_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM action_log ORDER BY timestamp DESC LIMIT ?;", (limit,))
            return [dict(row) for row in cursor.fetchall()]

# Global Action Log instance
action_log = ActionLogManager()
