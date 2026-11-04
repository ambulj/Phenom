"""
Swarm Workload Scheduler (SWM-01, SAF-01, SAF-02).
Dynamically partitions speculative decoding, embedding batches, and document indexing
across local mesh nodes respecting battery, thermal, and VRAM limits with automatic failover.
"""

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from services.backend.schemas.swarm_compute import (
    ComputeNodeType,
    DistributedWorkloadTask,
    SwarmClusterState,
    SwarmNodeTelemetry,
    WorkloadStatus,
    WorkloadType,
)
from services.backend.swarm_compute.node_manager import (
    SwarmNodeManager,
    swarm_node_manager,
)

logger = logging.getLogger(__name__)


class SwarmWorkloadScheduler:
    """Schedules, offloads, and monitors distributed compute tasks across P2P mesh peers."""

    def __init__(self, node_manager: Optional[SwarmNodeManager] = None) -> None:
        self.node_manager = node_manager or swarm_node_manager
        self._tasks: Dict[str, DistributedWorkloadTask] = {}
        self._halted: bool = False
        self._broadcaster: Optional[Callable[[dict], None]] = None

    def register_broadcaster(self, broadcaster: Callable[[dict], None]) -> None:
        self._broadcaster = broadcaster

    def _notify(self, event_type: str, payload: dict) -> None:
        if self._broadcaster and not self._halted:
            try:
                self._broadcaster({
                    "type": event_type,
                    "payload": payload,
                })
            except Exception as e:
                logger.debug(f"[SwarmScheduler] Broadcast error: {e}")

    def halt(self) -> None:
        """Immediate synchronous halt for Guardian kill switch (< 10ms SLA)."""
        self._halted = True
        # Abort all in-flight tasks
        for task in self._tasks.values():
            if task.status in (WorkloadStatus.PENDING, WorkloadStatus.RUNNING):
                task.status = WorkloadStatus.ABORTED
                task.completed_at = time.time()
                task.error = "Aborted by Guardian kill switch"

        self.node_manager.halt()
        logger.info("[SwarmScheduler] SwarmWorkloadScheduler halted synchronously by Guardian.")

    def reset(self) -> None:
        self._halted = False
        self._tasks.clear()
        self.node_manager.reset()

    def is_halted(self) -> bool:
        return self._halted

    def evaluate_candidate_nodes(
        self,
        workload_type: WorkloadType,
    ) -> List[SwarmNodeTelemetry]:
        """
        Filters and ranks available nodes respecting hardware, battery, and thermal limits.
        Constraint Rules:
        - Must be online
        - Must not be thermal throttled
        - Battery must be >= 20% or plugged in
        - For SPECULATIVE_DECODING: VRAM >= 2048 MB, mobile companion disallowed
        - For EMBEDDING_BATCH / DOCUMENT_INDEXING: RAM >= 1024 MB
        """
        all_nodes = self.node_manager.list_nodes(online_only=True)
        candidates = []

        for node in all_nodes:
            # Thermal check
            if node.thermal_throttled:
                logger.debug(f"[SwarmScheduler] Skipping node {node.node_id}: thermal throttled")
                continue

            # Battery check
            if not node.is_plugged_in and node.battery_percent < 20:
                logger.debug(f"[SwarmScheduler] Skipping node {node.node_id}: low battery ({node.battery_percent}%)")
                continue

            # Workload-specific hardware constraints
            if workload_type == WorkloadType.SPECULATIVE_DECODING:
                if node.node_type == ComputeNodeType.MOBILE_COMPANION:
                    continue
                if node.available_vram_mb < 2048:
                    continue

            elif workload_type in (WorkloadType.EMBEDDING_BATCH, WorkloadType.DOCUMENT_INDEXING):
                if node.available_ram_mb < 1024:
                    continue

            candidates.append(node)

        # Sort candidates: prioritize highest compute flops * available memory
        candidates.sort(
            key=lambda n: n.compute_flops_rating * (n.available_vram_mb + n.available_ram_mb),
            reverse=True,
        )
        return candidates

    def dispatch_workload(
        self,
        workload_type: WorkloadType | str,
        items_count: int = 10,
        preferred_node_id: Optional[str] = None,
        custom_payload: Optional[Dict[str, Any]] = None,
    ) -> DistributedWorkloadTask:
        """Dispatch a distributed workload task to an eligible peer node."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Swarm workload dispatch blocked.")

        if isinstance(workload_type, str):
            try:
                wtype = WorkloadType(workload_type.upper())
            except ValueError:
                wtype = WorkloadType.EMBEDDING_BATCH
        else:
            wtype = workload_type

        # Find best candidate node
        candidates = self.evaluate_candidate_nodes(wtype)
        if not candidates:
            # Fall back to host node
            host = self.node_manager.get_node(self.node_manager.host_node_id)
            if not host:
                raise RuntimeError("No candidate swarm nodes or host available.")
            chosen_node = host
        else:
            # Check preferred node if specified and valid
            chosen_node = candidates[0]
            if preferred_node_id:
                for cand in candidates:
                    if cand.node_id == preferred_node_id:
                        chosen_node = cand
                        break

        task_id = f"swm_{uuid.uuid4().hex[:8]}"
        task = DistributedWorkloadTask(
            task_id=task_id,
            workload_type=wtype,
            payload=custom_payload or {"items_count": items_count},
            assigned_node_id=chosen_node.node_id,
            status=WorkloadStatus.RUNNING,
            assigned_at=time.time(),
        )

        self._tasks[task_id] = task

        # Simulate local execution result with realistic latency / tokens
        self._complete_simulated_task(task, chosen_node, items_count)

        self._notify("swarm_workload_update", task.model_dump())
        return task

    def _complete_simulated_task(
        self,
        task: DistributedWorkloadTask,
        node: SwarmNodeTelemetry,
        items_count: int,
    ) -> None:
        """Simulate task execution on local mesh peer."""
        task.status = WorkloadStatus.COMPLETED
        task.completed_at = time.time()

        if task.workload_type == WorkloadType.SPECULATIVE_DECODING:
            tokens_generated = items_count * 16
            task.result = {
                "tokens_generated": tokens_generated,
                "speed_tps": round(node.compute_flops_rating * 18.5, 2),
                "acceptance_rate": 0.88,
                "offloaded_device": node.device_name,
            }
        elif task.workload_type == WorkloadType.EMBEDDING_BATCH:
            accel = node.node_type.value if hasattr(node.node_type, "value") else str(node.node_type)
            task.result = {
                "embeddings_computed": items_count,
                "dimension": 768,
                "device_accelerator": accel,
                "latency_ms": round(15.0 / node.compute_flops_rating, 2),
            }
        elif task.workload_type == WorkloadType.DOCUMENT_INDEXING:
            task.result = {
                "documents_indexed": items_count,
                "chunks_created": items_count * 4,
                "vector_store": "local_sqlite_vss",
            }
        else:
            task.result = {
                "status": "probed",
                "node_id": node.node_id,
                "health": "nominal",
            }

    def failover_task(self, task_id: str) -> DistributedWorkloadTask:
        """
        Dynamically re-routes a task to an alternate candidate or the sovereign host
        if the currently assigned node dropped offline or failed.
        """
        if self._halted:
            raise PermissionError("Guardian kill switch active: Swarm failover blocked.")

        if task_id not in self._tasks:
            raise KeyError(f"Task '{task_id}' not found.")

        task = self._tasks[task_id]
        prior_node_id = task.assigned_node_id

        # Mark prior node offline or deprioritize
        self.node_manager.mark_node_offline(prior_node_id)

        # Re-evaluate candidates excluding prior node
        candidates = [
            c for c in self.evaluate_candidate_nodes(task.workload_type)
            if c.node_id != prior_node_id
        ]

        if candidates:
            new_node = candidates[0]
        else:
            # Fall back to sovereign host
            new_node = self.node_manager.get_node(self.node_manager.host_node_id)  # type: ignore
            if not new_node:
                raise RuntimeError("Failed to resolve fallback host node.")

        task.assigned_node_id = new_node.node_id
        task.failover_count += 1
        task.status = WorkloadStatus.RUNNING
        task.error = None

        # Re-execute on new node
        items_count = task.payload.get("items_count", 10)
        self._complete_simulated_task(task, new_node, items_count)

        logger.info(f"[SwarmScheduler] Task {task_id} failed over from {prior_node_id} to {new_node.node_id} (count={task.failover_count})")
        self._notify("swarm_workload_update", task.model_dump())
        return task

    def abort_workload(self, task_id: str) -> bool:
        """Abort an active workload task."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Abort blocked.")

        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = WorkloadStatus.ABORTED
            task.completed_at = time.time()
            task.error = "Manually aborted by user"
            self._notify("swarm_workload_update", task.model_dump())
            return True
        return False

    def get_task(self, task_id: str) -> Optional[DistributedWorkloadTask]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[DistributedWorkloadTask]:
        return list(self._tasks.values())

    def get_cluster_state(self) -> SwarmClusterState:
        """Returns comprehensive cluster state with workload telemetry."""
        cluster_state = self.node_manager.get_cluster_state()
        active_count = sum(1 for t in self._tasks.values() if t.status == WorkloadStatus.RUNNING)
        cluster_state.active_workload_count = active_count
        cluster_state.cluster_load_factor = min(1.0, active_count / max(1, cluster_state.active_node_count * 2))
        return cluster_state


# Global singleton instance
swarm_workload_scheduler = SwarmWorkloadScheduler()
