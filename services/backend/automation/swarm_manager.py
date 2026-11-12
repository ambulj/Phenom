import threading
"""
Phenom Worker Swarm Manager
Coordinates parallel background autonomous workers (headless browser, CLI subprocesses)
and supervised foreground GUI automation with checkpointing and Guardian killswitch hooks.
"""

import uuid
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable

from services.backend.automation.headless_worker import HeadlessBrowserWorker, SubprocessCLIWorker, BLOCKED_PAYMENT_KEYWORDS
from services.backend.automation.swarm_store import SwarmCheckpointStore, swarm_store as default_swarm_store
from services.backend.safety.guardian import guardian
from services.backend.safety.action_log import action_log

logger = logging.getLogger("phenom.swarm_manager")

EventBroadcasterFn = Callable[[str, Dict[str, Any]], Awaitable[None]]


class WorkerSwarmManager:
    """
    Central orchestrator for the Phenom autonomous worker swarm.
    Manages concurrency bounds, step checkpointing, and instant Guardian halts.
    """

    def __init__(
        self,
        max_concurrency: int = 3,
        store: Optional[SwarmCheckpointStore] = None
    ):
        self.max_concurrency = max_concurrency
        self.store = store or default_swarm_store
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.active_workers: Dict[str, Any] = {}
        self._broadcaster: Optional[EventBroadcasterFn] = None

    def set_broadcaster(self, broadcaster: EventBroadcasterFn):
        self._broadcaster = broadcaster

    async def _emit(self, event_type: str, payload: Dict[str, Any]):
        if self._broadcaster:
            try:
                await self._broadcaster(event_type, payload)
            except Exception as e:
                logger.debug(f"Swarm broadcaster error ({event_type}): {e}")

    def get_active_count(self) -> int:
        return len([t for t in self.active_tasks.values() if t.get("status") == "running"])

    def get_swarm_status(self) -> Dict[str, Any]:
        """Returns overview of current swarm workers, queue, and completed tasks."""
        active = []
        for tid, t in self.active_tasks.items():
            active.append({
                "task_id": tid,
                "worker_id": t.get("worker_id"),
                "worker_type": t.get("worker_type"),
                "status": t.get("status"),
                "current_step": t.get("current_step", 0),
                "total_steps": t.get("total_steps", 1)
            })

        return {
            "active_count": self.get_active_count(),
            "max_concurrency": self.max_concurrency,
            "tasks": active,
            "guardian_halted": guardian.is_halted
        }

    async def dispatch_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches a new task to the swarm.
        task_type: 'headless_browser' | 'subprocess_cli' | 'foreground_gui'
        """
        if guardian.is_halted:
            raise PermissionError("Swarm dispatch blocked: Guardian kill switch is active.")

        if self.get_active_count() >= self.max_concurrency:
            raise RuntimeError(f"Swarm concurrency limit reached ({self.max_concurrency} active workers).")

        tid = task_id or f"task-swm-{uuid.uuid4().hex[:8]}"
        wid = f"worker-{task_type[:3]}-{uuid.uuid4().hex[:6]}"

        task_record = {
            "task_id": tid,
            "worker_id": wid,
            "worker_type": task_type,
            "status": "running",
            "current_step": 0,
            "total_steps": 1,
            "history": []
        }
        self.active_tasks[tid] = task_record

        # Initial checkpoint
        self.store.save_checkpoint(
            task_id=tid,
            worker_id=wid,
            worker_type=task_type,
            current_step=0,
            total_steps=1,
            status="running",
            history=[]
        )

        await self._emit("swarm.worker_spawned", {
            "task_id": tid,
            "worker_id": wid,
            "worker_type": task_type
        })

        if task_type == "headless_browser":
            return await self._run_headless_browser_task(tid, wid, payload)
        elif task_type == "subprocess_cli":
            return await self._run_subprocess_cli_task(tid, wid, payload)
        elif task_type == "foreground_gui":
            return await self._run_foreground_gui_task(tid, wid, payload)
        else:
            task_record["status"] = "failed"
            raise ValueError(f"Unsupported task_type '{task_type}'")

    async def _run_headless_browser_task(
        self,
        task_id: str,
        worker_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executes headless browser scraping and workflows."""
        steps = payload.get("steps", [])
        url = payload.get("url")
        if url:
            steps = [{"action": "navigate", "target": url}]

        # Rule 8 Pre-Flight Check
        for s in steps:
            target_str = f"{s.get('action', '')} {s.get('target', '')}".lower()
            for kw in BLOCKED_PAYMENT_KEYWORDS:
                if kw in target_str:
                    self.active_tasks[task_id]["status"] = "blocked_rule8"
                    self.store.save_checkpoint(task_id, worker_id, "headless_browser", 0, len(steps), "blocked_rule8", [])
                    action_log.log_action(
                        tool="swarm_headless_browser",
                        tier=3,
                        args=payload,
                        decision="blocked",
                        result_status="BLOCKED",
                        error=f"Rule 8 Violation: Payment keyword '{kw}' detected."
                    )
                    raise PermissionError(f"Payment action '{kw}' strictly prohibited by Rule 8.")

        worker = HeadlessBrowserWorker(worker_id=worker_id)
        self.active_workers[task_id] = worker
        self.active_tasks[task_id]["total_steps"] = len(steps)

        history = []
        try:
            for idx, step in enumerate(steps):
                if guardian.is_halted or self.active_tasks[task_id].get("status") == "aborted":
                    worker.abort()
                    self.active_tasks[task_id]["status"] = "aborted"
                    self.store.save_checkpoint(task_id, worker_id, "headless_browser", idx, len(steps), "aborted", history)
                    return {"status": "aborted", "task_id": task_id}

                action = step.get("action", "navigate")
                target = step.get("target", "")

                if action == "navigate":
                    step_res = await worker.scrape_page(target, selectors=step.get("selectors"))
                else:
                    step_res = await worker.execute_steps([step])

                history.append(step_res)
                self.active_tasks[task_id]["current_step"] = idx + 1
                self.active_tasks[task_id]["history"] = history

                self.store.save_checkpoint(
                    task_id=task_id,
                    worker_id=worker_id,
                    worker_type="headless_browser",
                    current_step=idx + 1,
                    total_steps=len(steps),
                    status="running" if idx + 1 < len(steps) else "completed",
                    history=history
                )

                await self._emit("swarm.step_progress", {
                    "task_id": task_id,
                    "worker_id": worker_id,
                    "step": idx + 1,
                    "total_steps": len(steps)
                })

            self.active_tasks[task_id]["status"] = "completed"
            await self._emit("swarm.worker_finished", {
                "task_id": task_id,
                "status": "completed",
                "results": history
            })
            return {"status": "completed", "task_id": task_id, "results": history}

        finally:
            await worker.close()
            self.active_workers.pop(task_id, None)

    async def _run_subprocess_cli_task(
        self,
        task_id: str,
        worker_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executes a detached background CLI task."""
        command = payload.get("command", "")
        cwd = payload.get("cwd")
        timeout_sec = float(payload.get("timeout_sec", 30.0))

        worker = SubprocessCLIWorker(worker_id=worker_id)
        self.active_workers[task_id] = worker

        try:
            res = await worker.execute_command(command, cwd=cwd, timeout_sec=timeout_sec)
            status = res.get("status", "completed")
            self.active_tasks[task_id]["status"] = status
            self.store.save_checkpoint(
                task_id=task_id,
                worker_id=worker_id,
                worker_type="subprocess_cli",
                current_step=1,
                total_steps=1,
                status=status,
                history=[res]
            )
            await self._emit("swarm.worker_finished", {
                "task_id": task_id,
                "status": status,
                "result": res
            })
            return res
        finally:
            self.active_workers.pop(task_id, None)

    async def _run_foreground_gui_task(
        self,
        task_id: str,
        worker_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Dispatches an interactive GUI workflow through the autonomous execution engine."""
        from services.backend.automation.goal_planner import AutonomousGoalPlanner
        from services.backend.automation.autonomous_engine import autonomous_engine

        goal = payload.get("goal", "")
        planner = AutonomousGoalPlanner()
        plan = planner.plan_goal(goal)

        self.active_tasks[task_id]["total_steps"] = len(plan.steps)
        exec_res = await autonomous_engine.execute_plan(plan)

        status = exec_res.get("status", "completed")
        self.active_tasks[task_id]["status"] = status
        self.store.save_checkpoint(
            task_id=task_id,
            worker_id=worker_id,
            worker_type="foreground_gui",
            current_step=exec_res.get("steps_executed", len(plan.steps)),
            total_steps=len(plan.steps),
            status=status,
            history=exec_res.get("results", [])
        )
        return exec_res

    def abort_task(self, task_id: str) -> bool:
        """Aborts a specific active task."""
        worker = self.active_workers.get(task_id)
        if worker and hasattr(worker, "abort"):
            worker.abort()
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = "aborted"
            self.store.save_checkpoint(
                task_id=task_id,
                worker_id=self.active_tasks[task_id].get("worker_id", "unknown"),
                worker_type=self.active_tasks[task_id].get("worker_type", "unknown"),
                current_step=self.active_tasks[task_id].get("current_step", 0),
                total_steps=self.active_tasks[task_id].get("total_steps", 1),
                status="aborted",
                history=self.active_tasks[task_id].get("history", [])
            )
            return True
        return False

    def abort_all(self, reason: str = "guardian_halt") -> int:
        """
        Synchronously aborts all active workers immediately.
        Guarantees sub-millisecond execution for the Guardian kill switch.
        """
        aborted_count = 0
        for tid, worker in list(self.active_workers.items()):
            try:
                if hasattr(worker, "abort"):
                    worker.abort()
                aborted_count += 1
            except Exception:
                pass

        for tid, task in list(self.active_tasks.items()):
            task["status"] = "aborted"
            try:
                threading.Thread(
                    target=self.store.save_checkpoint,
                    kwargs={
                        "task_id": tid,
                        "worker_id": task.get("worker_id", "unknown"),
                        "worker_type": task.get("worker_type", "unknown"),
                        "current_step": task.get("current_step", 0),
                        "total_steps": task.get("total_steps", 1),
                        "status": "aborted",
                        "history": task.get("history", []),
                    },
                    daemon=True,
                ).start()
            except Exception:
                pass

        logger.info(f"SwarmManager: Aborted {aborted_count} active workers ({reason}).")
        return aborted_count


# Global singleton
swarm_manager = WorkerSwarmManager()
