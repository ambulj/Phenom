"""
Phenom Background Scheduler (Phase 5)
Handles recurring tasks and timed reminders.
Persists across restarts in encrypted SQLCipher DB.
Records execution logs for every run.
Powers the Dashboard tab and Mini Overlay next-task indicator.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable
from services.backend.memory.db import encrypted_db

class BackgroundScheduler:
    def __init__(self, db_manager=None):
        self.db = db_manager or encrypted_db
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: Dict[str, Callable] = {}
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    def register_callback(self, action_type: str, fn: Callable):
        """Registers a handler for a specific action type (e.g. notify, check_alerts)."""
        self._callbacks[action_type] = fn

    def add_listener(self, fn: Callable[[Dict[str, Any]], None]):
        """Listener invoked when a reminder or event triggers (e.g. for WebSocket broadcast)."""
        self._listeners.append(fn)

    def add_reminder(self, title: str, delay_seconds: Optional[int] = None, due_at: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Creates a one-time reminder."""
        job_id = f"rem_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        if delay_seconds is not None:
            run_time = now + timedelta(seconds=delay_seconds)
            run_time_str = run_time.isoformat()
        elif due_at:
            run_time_str = due_at
        else:
            raise ValueError("Either delay_seconds or due_at must be provided.")

        payload_data = payload or {}
        payload_data["title"] = title
        payload_json = json.dumps(payload_data)
        now_str = now.isoformat()

        conn = self.db.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO scheduled_jobs (id, title, schedule_type, schedule_expr, action_type, payload_json, enabled, next_run_at, created_at) "
                "VALUES (?, ?, 'once', ?, 'notify', ?, 1, ?, ?);",
                (job_id, title, run_time_str, payload_json, run_time_str, now_str)
            )
        conn.close()

        return {
            "id": job_id,
            "title": title,
            "schedule_type": "once",
            "next_run_at": run_time_str,
            "enabled": True
        }

    def add_recurring_job(self, title: str, interval_seconds: int, action_type: str = "notify", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Creates a recurring interval job."""
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        next_run = now + timedelta(seconds=interval_seconds)
        next_run_str = next_run.isoformat()
        payload_json = json.dumps(payload or {})
        now_str = now.isoformat()

        conn = self.db.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO scheduled_jobs (id, title, schedule_type, schedule_expr, action_type, payload_json, enabled, next_run_at, created_at) "
                "VALUES (?, ?, 'interval', ?, ?, ?, 1, ?, ?);",
                (job_id, title, str(interval_seconds), action_type, payload_json, next_run_str, now_str)
            )
        conn.close()

        return {
            "id": job_id,
            "title": title,
            "schedule_type": "interval",
            "interval_seconds": interval_seconds,
            "next_run_at": next_run_str,
            "enabled": True
        }

    def cancel_job(self, job_id: str) -> bool:
        """Disables or cancels a scheduled job."""
        conn = self.db.get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE scheduled_jobs SET enabled = 0 WHERE id = ?;", (job_id,))
            affected = cursor.rowcount > 0
        conn.close()
        return affected

    def list_jobs(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        query = "SELECT id, title, schedule_type, schedule_expr, action_type, payload_json, enabled, next_run_at, created_at FROM scheduled_jobs"
        if not include_disabled:
            query += " WHERE enabled = 1"
        query += " ORDER BY next_run_at ASC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        jobs = []
        for r in rows:
            jobs.append({
                "id": r[0],
                "title": r[1],
                "schedule_type": r[2],
                "schedule_expr": r[3],
                "action_type": r[4],
                "payload": json.loads(r[5]) if r[5] else {},
                "enabled": bool(r[6]),
                "next_run_at": r[7],
                "created_at": r[8]
            })
        return jobs

    def get_next_scheduled_item(self) -> Optional[Dict[str, Any]]:
        """Returns the single next scheduled item (for the Mini Overlay)."""
        jobs = self.list_jobs(include_disabled=False)
        return jobs[0] if jobs else None

    def log_run(self, job_id: str, status: str, duration_ms: float, result_summary: str = "", error: str = ""):
        now_str = datetime.now(timezone.utc).isoformat()
        conn = self.db.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO job_run_logs (job_id, run_at, status, duration_ms, result_summary, error) "
                "VALUES (?, ?, ?, ?, ?, ?);",
                (job_id, now_str, status, duration_ms, result_summary, error)
            )
        conn.close()

    def get_run_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, job_id, run_at, status, duration_ms, result_summary, error FROM job_run_logs "
            "ORDER BY run_at DESC LIMIT ?;",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "job_id": r[1],
                "run_at": r[2],
                "status": r[3],
                "duration_ms": r[4],
                "result_summary": r[5],
                "error": r[6]
            }
            for r in rows
        ]

    async def execute_due_jobs(self) -> int:
        """Finds and executes any due jobs. Returns count of executed jobs."""
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, schedule_type, schedule_expr, action_type, payload_json FROM scheduled_jobs "
            "WHERE enabled = 1 AND next_run_at <= ?;",
            (now_str,)
        )
        due_jobs = cursor.fetchall()
        conn.close()

        executed = 0
        for job_row in due_jobs:
            job_id, title, stype, sexpr, action, p_json = job_row
            payload = json.loads(p_json) if p_json else {}
            start_t = time.perf_counter()
            status = "success"
            err_msg = ""
            summary = f"Executed {action} for '{title}'"

            try:
                # Trigger callback or broadcast
                if action in self._callbacks:
                    handler = self._callbacks[action]
                    if asyncio.iscoroutinefunction(handler):
                        await handler(payload)
                    else:
                        handler(payload)
                
                # Notify listeners
                event_data = {
                    "type": "scheduled_reminder",
                    "job_id": job_id,
                    "title": title,
                    "action": action,
                    "payload": payload,
                    "timestamp": now_str
                }
                for listener in self._listeners:
                    try:
                        if asyncio.iscoroutinefunction(listener):
                            await listener(event_data)
                        else:
                            listener(event_data)
                    except Exception as le:
                        print(f"[Scheduler] Listener error: {le}")

            except Exception as e:
                status = "error"
                err_msg = str(e)
                summary = f"Failed to execute {action}: {e}"

            elapsed_ms = (time.perf_counter() - start_t) * 1000.0
            self.log_run(job_id, status, elapsed_ms, summary, err_msg)
            executed += 1

            # Update next run time or disable if one-time
            conn_up = self.db.get_connection()
            with conn_up:
                if stype == "once":
                    conn_up.execute("UPDATE scheduled_jobs SET enabled = 0, next_run_at = NULL WHERE id = ?;", (job_id,))
                elif stype == "interval":
                    interval = int(sexpr)
                    next_run = now + timedelta(seconds=interval)
                    conn_up.execute("UPDATE scheduled_jobs SET next_run_at = ? WHERE id = ?;", (next_run.isoformat(), job_id))
            conn_up.close()

        return executed

    async def _run_loop(self):
        while self._running:
            try:
                await self.execute_due_jobs()
            except Exception as e:
                print(f"[Scheduler] Error in loop: {e}")
            await asyncio.sleep(1.0)

    def start(self):
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
                self._task = loop.create_task(self._run_loop())
            except RuntimeError:
                pass

    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

# Global background scheduler instance
background_scheduler = BackgroundScheduler()
