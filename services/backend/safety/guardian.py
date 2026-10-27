"""
Phenom Guardian Kill Switch
The ultimate safety override. Halts all running operations immediately,
force-terminates child processes, cancels generation streams, and freezes Phenom
in the 'halted' state until explicitly resumed by the user.
"""

import os
import sys
import threading
import asyncio
from typing import Set, Callable, Optional, List
import psutil
from services.backend.safety.action_log import action_log

class GuardianKillSwitch:
    def __init__(self):
        self._halted: bool = False
        self._tracked_pids: Set[int] = set()
        self._tracked_tasks: Set[asyncio.Task] = set()
        self._callbacks: List[Callable[[str], None]] = []
        self._lock = threading.Lock()
        self._hotkey_hook = None

    @property
    def is_halted(self) -> bool:
        return self._halted

    def add_state_callback(self, cb: Callable[[str], None]):
        self._callbacks.append(cb)

    def track_pid(self, pid: int):
        with self._lock:
            self._tracked_pids.add(pid)

    def untrack_pid(self, pid: int):
        with self._lock:
            self._tracked_pids.discard(pid)

    def track_task(self, task: asyncio.Task):
        with self._lock:
            self._tracked_tasks.add(task)

    def untrack_task(self, task: asyncio.Task):
        with self._lock:
            self._tracked_tasks.discard(task)

    def trigger(self, reason: str = "manual_killswitch") -> int:
        """Immediately halts all execution. Thread-safe."""
        with self._lock:
            self._halted = True
            killed_processes = 0

            # 1. Cancel all tracked asyncio tasks
            for task in list(self._tracked_tasks):
                if not task.done():
                    task.cancel()
            self._tracked_tasks.clear()

            # 2. Force terminate all tracked processes
            for pid in list(self._tracked_pids):
                try:
                    p = psutil.Process(pid)
                    for child in p.children(recursive=True):
                        child.kill()
                    p.kill()
                    killed_processes += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self._tracked_pids.clear()

        # 3. Log killswitch activation
        action_log.log_action(
            tool="guardian_killswitch",
            tier=3,
            args={"reason": reason, "processes_killed": killed_processes},
            decision="auto",
            result_status="HALTED",
            source="system"
        )

        # 4. Notify UI / orchestrator callbacks
        for cb in self._callbacks:
            try:
                cb("halted")
            except Exception:
                pass

        return killed_processes

    def resume(self):
        """Resumes Phenom from halted state."""
        with self._lock:
            self._halted = False

        action_log.log_action(
            tool="guardian_resume",
            tier=0,
            args={"action": "user_resume"},
            decision="approved",
            result_status="RESUMED",
            source="desktop"
        )

        for cb in self._callbacks:
            try:
                cb("idle")
            except Exception:
                pass

    def setup_global_hotkey(self, hotkey: str = "ctrl+alt+pause"):
        """Configures global system-wide hotkey listener."""
        try:
            import keyboard
            keyboard.add_hotkey(hotkey, lambda: self.trigger(f"global_hotkey_{hotkey}"))
        except Exception as e:
            # On non-elevated or background headless runs, graceful notification
            pass

# Global Guardian Instance
guardian = GuardianKillSwitch()
