"""
Phenom Swarm Checkpoint Store
Manages durable task checkpoints for background worker swarms in SQLite.
Enables instant recovery and resumption after restarts or unexpected interruptions.
Thread-safe for concurrent operations across worker threads.
"""

import os
import time
import json
import sqlite3
import threading
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("phenom.swarm_store")


class SwarmCheckpointStore:
    """
    SQLite persistence layer for swarm worker task checkpoints.
    Thread-safe.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(base_dir, "swarm_checkpoints.db")
        else:
            self.db_path = db_path

        self._conn = None
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self):
        if self._conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._conn = conn
        return self._conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS swarm_checkpoints (
                        task_id TEXT PRIMARY KEY,
                        worker_id TEXT NOT NULL,
                        worker_type TEXT NOT NULL,
                        current_step INTEGER NOT NULL,
                        total_steps INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        history_json TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_swarm_status ON swarm_checkpoints(status);")

    def save_checkpoint(
        self,
        task_id: str,
        worker_id: str,
        worker_type: str,
        current_step: int,
        total_steps: int,
        status: str,
        history: List[Dict[str, Any]]
    ) -> bool:
        """Saves or updates a worker task checkpoint."""
        now = time.time()
        history_str = json.dumps(history)
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    INSERT INTO swarm_checkpoints (
                        task_id, worker_id, worker_type, current_step, total_steps, status, history_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        worker_id = excluded.worker_id,
                        current_step = excluded.current_step,
                        total_steps = excluded.total_steps,
                        status = excluded.status,
                        history_json = excluded.history_json,
                        updated_at = excluded.updated_at;
                """, (task_id, worker_id, worker_type, current_step, total_steps, status, history_str, now, now))
        return True

    def get_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves checkpoint by task_id."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT task_id, worker_id, worker_type, current_step, total_steps, status, history_json, created_at, updated_at
                FROM swarm_checkpoints
                WHERE task_id = ?;
            """, (task_id,))
            row = cursor.fetchone()
            if not row:
                return None

            history = []
            try:
                history = json.loads(row["history_json"]) if row["history_json"] else []
            except Exception:
                pass

            return {
                "task_id": row["task_id"],
                "worker_id": row["worker_id"],
                "worker_type": row["worker_type"],
                "current_step": row["current_step"],
                "total_steps": row["total_steps"],
                "status": row["status"],
                "history": history,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    def list_checkpoints(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists checkpoints with optional status filter."""
        with self._lock:
            conn = self._get_connection()
            if status_filter:
                cursor = conn.execute("SELECT * FROM swarm_checkpoints WHERE status = ? ORDER BY updated_at DESC;", (status_filter,))
            else:
                cursor = conn.execute("SELECT * FROM swarm_checkpoints ORDER BY updated_at DESC;")

            results = []
            for row in cursor.fetchall():
                results.append({
                    "task_id": row["task_id"],
                    "worker_id": row["worker_id"],
                    "worker_type": row["worker_type"],
                    "current_step": row["current_step"],
                    "total_steps": row["total_steps"],
                    "status": row["status"],
                    "updated_at": row["updated_at"]
                })
            return results

    def delete_checkpoint(self, task_id: str) -> bool:
        """Deletes checkpoint on final task completion."""
        with self._lock:
            conn = self._get_connection()
            with conn:
                cursor = conn.execute("DELETE FROM swarm_checkpoints WHERE task_id = ?;", (task_id,))
                return cursor.rowcount > 0

    def close(self):
        with self._lock:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None


# Global singleton
swarm_store = SwarmCheckpointStore()
