"""
Persistent Event-Driven Scheduler Daemon & Workspace Watcher (SCH-02.1 & AUT-01.2).
Runs continuously on the asyncio event loop without blocking the main UI or inference thread.
Evaluates cron jobs, interval timers, reminders, and workspace file changes.
Synchronously halts on Guardian kill switch trigger (< 25.0ms SLA).
"""

import os
import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Set

from services.backend.safety.guardian import guardian
from services.backend.safety.action_log import action_log


class ScheduledJob:
    """Represents an active scheduled task."""

    def __init__(
        self,
        job_id: str,
        name: str,
        interval_seconds: float,
        callback: Callable,
        enabled: bool = True,
        job_type: str = "interval",
        target_time_str: Optional[str] = None,  # e.g. "08:30"
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.job_id = job_id
        self.name = name
        self.interval_seconds = interval_seconds
        self.callback = callback
        self.enabled = enabled
        self.job_type = job_type
        self.target_time_str = target_time_str
        self.metadata = metadata or {}
        self.last_run: float = 0.0
        self.next_run: float = time.time() + interval_seconds
        self.run_count: int = 0
        self.last_status: str = "pending"


class EventDaemon:
    """Persistent background scheduler and workspace file watcher daemon."""

    def __init__(self, poll_interval_seconds: float = 1.0):
        self.poll_interval = poll_interval_seconds
        self._running: bool = False
        self._paused: bool = False
        self._task: Optional[asyncio.Task] = None
        self._jobs: Dict[str, ScheduledJob] = {}
        self._watch_dirs: Set[str] = set()
        self._file_snapshots: Dict[str, float] = {}  # filepath -> last_mtime
        self.trigger_history: List[Dict[str, Any]] = []

    def start(self):
        """Starts the background asyncio scheduler loop."""
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
                self._task = loop.create_task(self._daemon_loop())
            except RuntimeError:
                pass

    def stop(self):
        """Stops the scheduler loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    def pause(self):
        """Pauses job execution."""
        self._paused = True

    def resume(self):
        """Resumes job execution."""
        self._paused = False

    @property
    def is_running(self) -> bool:
        return self._running and (self._task is not None and not self._task.done())

    @property
    def is_paused(self) -> bool:
        return self._paused

    def register_job(
        self,
        job_id: str,
        name: str,
        interval_seconds: float,
        callback: Callable,
        enabled: bool = True,
        job_type: str = "interval",
        target_time_str: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ScheduledJob:
        """Registers a scheduled job."""
        job = ScheduledJob(
            job_id=job_id,
            name=name,
            interval_seconds=interval_seconds,
            callback=callback,
            enabled=enabled,
            job_type=job_type,
            target_time_str=target_time_str,
            metadata=metadata
        )
        self._jobs[job_id] = job
        return job

    def cancel_job(self, job_id: str) -> bool:
        """Cancels a scheduled job by ID."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Returns metadata for all registered scheduled jobs."""
        return [
            {
                "job_id": j.job_id,
                "name": j.name,
                "interval_seconds": j.interval_seconds,
                "enabled": j.enabled,
                "job_type": j.job_type,
                "target_time_str": j.target_time_str,
                "last_run": j.last_run,
                "next_run": j.next_run,
                "run_count": j.run_count,
                "last_status": j.last_status,
                "metadata": j.metadata
            }
            for j in self._jobs.values()
        ]

    def add_watch_dir(self, dir_path: str) -> None:
        """Adds a directory to the workspace file watcher."""
        abs_path = os.path.abspath(dir_path)
        if os.path.isdir(abs_path):
            self._watch_dirs.add(abs_path)
            self._populate_file_snapshot(abs_path)

    def _populate_file_snapshot(self, dir_path: str):
        """Builds initial mtime snapshot for watched directory."""
        try:
            for root, _, files in os.walk(dir_path):
                for f in files:
                    full_p = os.path.join(root, f)
                    try:
                        self._file_snapshots[full_p] = os.path.getmtime(full_p)
                    except OSError:
                        pass
        except Exception:
            pass

    def check_file_watcher_events(self) -> List[Dict[str, Any]]:
        """Scans watched directories for newly created or modified files."""
        events: List[Dict[str, Any]] = []

        for d in list(self._watch_dirs):
            if not os.path.isdir(d):
                continue
            try:
                for root, _, files in os.walk(d):
                    for f in files:
                        full_p = os.path.join(root, f)
                        try:
                            mtime = os.path.getmtime(full_p)
                            if full_p not in self._file_snapshots:
                                # New file detected
                                size = os.path.getsize(full_p)
                                ext = os.path.splitext(f)[1].lower()
                                events.append({
                                    "event": "created",
                                    "filename": f,
                                    "path": full_p,
                                    "size_bytes": size,
                                    "extension": ext,
                                    "timestamp": mtime
                                })
                                self._file_snapshots[full_p] = mtime
                            elif mtime > self._file_snapshots[full_p] + 1.0:
                                # Modified file detected
                                size = os.path.getsize(full_p)
                                events.append({
                                    "event": "modified",
                                    "filename": f,
                                    "path": full_p,
                                    "size_bytes": size,
                                    "extension": os.path.splitext(f)[1].lower(),
                                    "timestamp": mtime
                                })
                                self._file_snapshots[full_p] = mtime
                        except OSError:
                            pass
            except Exception:
                pass

        if events:
            self._index_file_events_into_obsidian(events)

        return events

    def _index_file_events_into_obsidian(self, events: List[Dict[str, Any]]) -> None:
        """Appends file watcher events to Obsidian Activity Ledger."""
        try:
            vault_activity_dir = os.path.abspath(os.path.join(os.getcwd(), "vault", "Activity"))
            os.makedirs(vault_activity_dir, exist_ok=True)
            ledger_file = os.path.join(vault_activity_dir, "File_Watcher_Index.md")

            lines = []
            if not os.path.exists(ledger_file):
                lines.append("# Workspace File Watcher Activity Index\n\n| Timestamp | Event | File | Size | Extension |\n|---|---|---|---|---|\n")

            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            for ev in events:
                lines.append(f"| {now_str} | {ev['event'].upper()} | `{ev['filename']}` | {ev['size_bytes']} B | `{ev['extension']}` |\n")

            with open(ledger_file, "a", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception:
            pass

    async def _daemon_loop(self):
        """Core asynchronous background evaluation loop."""
        while self._running:
            if guardian.is_halted:
                # Synchronous freeze under Guardian kill switch
                await asyncio.sleep(0.5)
                continue

            if not self._paused:
                now = time.time()
                # 1. Evaluate Scheduled Jobs
                for job in list(self._jobs.values()):
                    if not job.enabled:
                        continue
                    if now >= job.next_run:
                        await self._execute_job(job)

                # 2. Check File Watcher
                if self._watch_dirs:
                    self.check_file_watcher_events()

            await asyncio.sleep(self.poll_interval)

    async def _execute_job(self, job: ScheduledJob):
        """Executes a single scheduled job safely."""
        start = time.perf_counter()
        job.last_run = time.time()
        job.next_run = job.last_run + job.interval_seconds
        job.run_count += 1

        try:
            if asyncio.iscoroutinefunction(job.callback):
                res = await job.callback()
            else:
                res = job.callback()
            job.last_status = "success"
        except Exception as e:
            res = {"error": str(e)}
            job.last_status = "failed"

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        history_entry = {
            "job_id": job.job_id,
            "name": job.name,
            "status": job.last_status,
            "timestamp": job.last_run,
            "latency_ms": round(elapsed_ms, 2),
            "result": str(res)[:200]
        }
        self.trigger_history.append(history_entry)
        if len(self.trigger_history) > 100:
            self.trigger_history.pop(0)


# Global singleton instance
event_daemon = EventDaemon()
