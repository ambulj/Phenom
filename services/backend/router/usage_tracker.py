"""
Phenom Multi-Provider Usage Tracker & Analytics Engine (Task 7k)
Tracks token consumption, latency, rate limits, and provider routing history in SQLCipher.

Features:
- Encrypted storage in `provider_usage_history` table.
- Daily & Monthly aggregation with quota limit estimation.
- Rate-limit encounter logging (HTTP 429).
- Rolling 90-day retention pruning.
"""

import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from services.backend.memory.db import encrypted_db

class ProviderUsageTracker:
    def __init__(self, db_manager=None):
        self.db = db_manager or encrypted_db
        self._init_table()

    def _init_table(self):
        conn = self.db.get_connection()
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS provider_usage_history (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                latency_ms REAL DEFAULT 0.0,
                status_code INTEGER DEFAULT 200,
                error_message TEXT DEFAULT '',
                timestamp TEXT NOT NULL,
                date_str TEXT NOT NULL,
                month_str TEXT NOT NULL
            );
            """)
        conn.close()

    def record_usage(
        self,
        provider: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        status_code: int = 200,
        error_message: str = ""
    ) -> Dict[str, Any]:
        """Records an inference call into SQLCipher."""
        entry_id = f"usage_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        ts_str = now.isoformat()
        date_str = now.strftime("%Y-%m-%d")
        month_str = now.strftime("%Y-%m")
        total_tokens = prompt_tokens + completion_tokens

        conn = self.db.get_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO provider_usage_history (
                    id, provider, model, prompt_tokens, completion_tokens,
                    total_tokens, latency_ms, status_code, error_message,
                    timestamp, date_str, month_str
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    entry_id, provider, model, prompt_tokens, completion_tokens,
                    total_tokens, latency_ms, status_code, error_message,
                    ts_str, date_str, month_str
                )
            )
        conn.close()

        return {
            "id": entry_id,
            "provider": provider,
            "model": model,
            "total_tokens": total_tokens,
            "latency_ms": latency_ms,
            "status_code": status_code,
            "timestamp": ts_str
        }

    def get_daily_summary(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Aggregates calls, tokens, latency, and rate limits for a given day."""
        target_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Overall totals
        cursor.execute(
            """
            SELECT COUNT(*), SUM(prompt_tokens), SUM(completion_tokens), SUM(total_tokens), AVG(latency_ms)
            FROM provider_usage_history WHERE date_str = ?;
            """,
            (target_date,)
        )
        row = cursor.fetchone()
        call_count = row[0] or 0
        prompt_tokens = row[1] or 0
        completion_tokens = row[2] or 0
        total_tokens = row[3] or 0
        avg_latency = round(row[4] or 0.0, 2)

        # Per-provider breakdown
        cursor.execute(
            """
            SELECT provider, COUNT(*), SUM(total_tokens),
                   SUM(CASE WHEN status_code = 429 THEN 1 ELSE 0 END),
                   AVG(latency_ms)
            FROM provider_usage_history WHERE date_str = ?
            GROUP BY provider;
            """,
            (target_date,)
        )
        providers_breakdown = {}
        total_rate_limits = 0
        for r in cursor.fetchall():
            p_name, p_calls, p_toks, p_429, p_lat = r
            providers_breakdown[p_name] = {
                "calls": p_calls,
                "total_tokens": p_toks or 0,
                "rate_limits_429": p_429 or 0,
                "avg_latency_ms": round(p_lat or 0.0, 2)
            }
            total_rate_limits += (p_429 or 0)

        conn.close()
        return {
            "date": target_date,
            "total_calls": call_count,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "avg_latency_ms": avg_latency,
            "total_rate_limits_429": total_rate_limits,
            "providers": providers_breakdown
        }

    def get_monthly_summary(self, month_str: Optional[str] = None) -> Dict[str, Any]:
        """Aggregates calls, tokens, and quota estimations for a given month."""
        target_month = month_str or datetime.now(timezone.utc).strftime("%Y-%m")
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*), SUM(total_tokens),
                   SUM(CASE WHEN status_code = 429 THEN 1 ELSE 0 END)
            FROM provider_usage_history WHERE month_str = ?;
            """,
            (target_month,)
        )
        row = cursor.fetchone()
        call_count = row[0] or 0
        total_tokens = row[1] or 0
        rate_limits = row[2] or 0

        # Provider breakdown
        cursor.execute(
            """
            SELECT provider, COUNT(*), SUM(total_tokens)
            FROM provider_usage_history WHERE month_str = ?
            GROUP BY provider;
            """,
            (target_month,)
        )
        breakdown = {r[0]: {"calls": r[1], "tokens": r[2] or 0} for r in cursor.fetchall()}
        conn.close()

        return {
            "month": target_month,
            "total_calls": call_count,
            "total_tokens": total_tokens,
            "rate_limits_429": rate_limits,
            "providers": breakdown
        }

    def get_recent_load_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent call history for UI usage panel."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, provider, model, total_tokens, latency_ms, status_code, timestamp
            FROM provider_usage_history
            ORDER BY timestamp DESC LIMIT ?;
            """,
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "provider": r[1],
                "model": r[2],
                "total_tokens": r[3],
                "latency_ms": r[4],
                "status_code": r[5],
                "timestamp": r[6]
            }
            for r in rows
        ]

    def prune_old_records(self, retention_days: int = 90) -> int:
        """Enforces rolling 90-day retention pruning."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        conn = self.db.get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM provider_usage_history WHERE timestamp < ?;", (cutoff,))
            pruned = cursor.rowcount
        conn.close()
        return pruned

# Global usage tracker instance
usage_tracker = ProviderUsageTracker()
