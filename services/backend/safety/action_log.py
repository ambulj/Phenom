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
                undo_token TEXT,
                model TEXT
            );
            """)
            # Schema migration: check if model column exists
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(action_log);")
            columns = [row[1] for row in cursor.fetchall()]
            if "model" not in columns:
                conn.execute("ALTER TABLE action_log ADD COLUMN model TEXT;")
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
        log_id: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        entry_id = log_id or str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        redacted_args_str = redact_arguments(args)

        # Tag every action-log entry produced in security mode with the specialist model name (Task 6D)
        active_model = model
        if not active_model:
            try:
                from services.backend.modes.mode_manager import mode_manager
                if mode_manager.is_security_mode_active:
                    active_model = mode_manager.active_specialist_model or "hf.co/tinyopsec/Qwen3.5-4B-Uncensored-Aggressive-GGUF:Q4_K_M"
            except Exception:
                pass

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            INSERT INTO action_log (id, timestamp, source, tool, tier, arguments_redacted, decision, result_status, error, undo_token, model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (entry_id, ts, source, tool, tier, redacted_args_str, decision, result_status, error, undo_token, active_model))
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
            "undo_token": undo_token,
            "model": active_model
        }

    def list_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM action_log ORDER BY timestamp DESC LIMIT ?;", (limit,))
            return [dict(row) for row in cursor.fetchall()]

# Global Action Log instance
action_log = ActionLogManager()
