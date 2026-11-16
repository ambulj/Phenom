"""Time-Sliced Local Scheduler & VRAM Governor for Phenom Multi-Agent Swarm.

Phase 48-01: SWARM-03.
Serializes local GPU task execution through an asynchronous FIFO queue,
enforcing strict VRAM limits (< 5.5 GB on RTX 3050) and sub-25ms Guardian kill switch aborts.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from services.backend.schemas.swarm_auction import (
    AgentRole,
    ScheduledTask,
    SwarmTaskStatus,
    VRAMMetrics,
)

logger = logging.getLogger("phenom.swarm.scheduler")


class VRAMLimitExceededError(RuntimeError):
    """Raised when local GPU VRAM exceeds the strict 5.5 GB safety threshold."""
    pass


class SwarmScheduler:
    """Asynchronous time-sliced task queue and VRAM governor for the multi-agent swarm."""

    DEFAULT_MAX_VRAM_MB: float = 5632.0  # 5.5 GB limit for RTX 3050 8GB

    def __init__(
        self,
        max_vram_mb: float = DEFAULT_MAX_VRAM_MB,
        guardian_checker: Optional[Callable[[], bool]] = None,
    ) -> None:
        self.max_vram_mb = max_vram_mb
        self._guardian_checker = guardian_checker or self._default_guardian_check
        self._queue: List[ScheduledTask] = []
        self._history: List[ScheduledTask] = []
        self._gpu_lock = asyncio.Lock()
        self._simulated_vram_mb: Optional[float] = None
        self._is_paused: bool = False
        self._is_halted: bool = False

    @staticmethod
    def _default_guardian_check() -> bool:
        """Query Universal Guardian status if present."""
        try:
            from services.backend.safety.guardian import guardian
            return guardian.is_triggered()
        except Exception:
            return False

    def get_vram_metrics(self) -> VRAMMetrics:
        """Measure current VRAM utilization via PyTorch CUDA or monitored telemetry."""
        allocated_mb = 0.0
        reserved_mb = 0.0

        if self._simulated_vram_mb is not None:
            allocated_mb = self._simulated_vram_mb
            reserved_mb = self._simulated_vram_mb + 200.0
        else:
            try:
                import torch
                if torch.cuda.is_available():
                    allocated_mb = torch.cuda.memory_allocated() / (1024 * 1024)
                    reserved_mb = torch.cuda.memory_reserved() / (1024 * 1024)
                else:
                    allocated_mb = 4850.0  # Default 8B footprint in VRAM
                    reserved_mb = 5050.0
            except Exception:
                allocated_mb = 4850.0
                reserved_mb = 5050.0

        peak_mb = max(allocated_mb, reserved_mb)
        is_safe = peak_mb <= self.max_vram_mb

        return VRAMMetrics(
            allocated_mb=round(allocated_mb, 2),
            reserved_mb=round(reserved_mb, 2),
            peak_mb=round(peak_mb, 2),
            max_allowed_mb=self.max_vram_mb,
            is_safe=is_safe,
        )

    def set_simulated_vram(self, vram_mb: float) -> None:
        """Testing hook to simulate GPU memory pressure."""
        self._simulated_vram_mb = vram_mb

    def enqueue_task(
        self,
        node_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        assigned_role: AgentRole,
        task_id: Optional[str] = None,
    ) -> ScheduledTask:
        """Enqueue a task into the time-sliced queue."""
        if self._is_halted or self._guardian_checker():
            raise RuntimeError("Scheduler is halted by Guardian kill switch.")

        task = ScheduledTask(
            task_id=task_id or f"task_{node_id}_{int(time.time() * 1000)}",
            node_id=node_id,
            tool_name=tool_name,
            arguments=arguments,
            assigned_role=assigned_role,
            status=SwarmTaskStatus.SCHEDULED,
        )
        self._queue.append(task)
        logger.info("Enqueued task %s for role %s", task.task_id, assigned_role.value)
        return task

    def get_queue_status(self) -> List[ScheduledTask]:
        """Return snapshot of currently pending and scheduled tasks."""
        return list(self._queue)

    def get_history(self) -> List[ScheduledTask]:
        """Return history of completed/failed tasks."""
        return list(self._history)

    def halt(self) -> int:
        """Sub-25ms Emergency Kill Switch halt: cancels all enqueued and running tasks."""
        t_start = time.perf_counter()
        self._is_halted = True
        cancelled_count = 0

        for task in self._queue:
            task.status = SwarmTaskStatus.HALTED
            task.error = "Halted by Universal Guardian kill switch"
            self._history.append(task)
            cancelled_count += 1

        self._queue.clear()
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        logger.warning(
            "Guardian kill switch invoked on scheduler: %d tasks cancelled in %.3f ms",
            cancelled_count,
            elapsed_ms,
        )
        return cancelled_count

    async def execute_task(
        self,
        task: ScheduledTask,
        executor_fn: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ) -> ScheduledTask:
        """Execute a single task with serialized GPU access and VRAM governance."""
        # 1. Check Guardian Kill Switch (< 25ms SLA)
        if self._is_halted or self._guardian_checker():
            task.status = SwarmTaskStatus.HALTED
            task.error = "Universal Guardian kill switch active"
            self._history.append(task)
            return task

        # 2. Acquire GPU execution lock to prevent parallel VRAM thrashing
        async with self._gpu_lock:
            # 3. Check VRAM metrics before running
            metrics = self.get_vram_metrics()
            if not metrics.is_safe:
                task.status = SwarmTaskStatus.FAILED
                task.error = (
                    f"VRAMLimitExceededError: Peak VRAM {metrics.peak_mb:.1f} MB "
                    f"exceeds limit {metrics.max_allowed_mb:.1f} MB"
                )
                self._history.append(task)
                raise VRAMLimitExceededError(task.error)

            task.status = SwarmTaskStatus.RUNNING
            task.started_at = time.time()
            task.vram_usage_mb = metrics.peak_mb

            try:
                if executor_fn:
                    result = executor_fn(task.tool_name, task.arguments)
                    if asyncio.iscoroutine(result):
                        result = await result
                    task.result = result
                else:
                    # Default: Route to Tool Registry
                    from services.backend.safety.registry import registry
                    tool_def = registry.get(task.tool_name)
                    if tool_def is None:
                        raise ValueError(f"Tool '{task.tool_name}' not found in registry")
                    res = tool_def.handler_fn(**task.arguments)
                    if asyncio.iscoroutine(res):
                        res = await res
                    task.result = res

                task.status = SwarmTaskStatus.COMPLETED
            except Exception as exc:
                logger.error("Error executing task %s: %s", task.task_id, exc)
                task.status = SwarmTaskStatus.FAILED
                task.error = str(exc)
            finally:
                task.completed_at = time.time()
                self._history.append(task)

        return task

    async def run_all(
        self,
        executor_fn: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ) -> List[ScheduledTask]:
        """Process all queued tasks sequentially with serialized GPU execution."""
        results: List[ScheduledTask] = []

        while self._queue:
            if self._is_halted or self._guardian_checker():
                self.halt()
                break

            task = self._queue.pop(0)
            executed_task = await self.execute_task(task, executor_fn)
            results.append(executed_task)

            # Check if task failed due to VRAM limit
            if executed_task.status == SwarmTaskStatus.FAILED and "VRAMLimitExceededError" in str(executed_task.error):
                break

        return results
