"""
Cross-Device Distributed Swarm & Offline Mesh P2P Compute Offloading Tools (SWM-01, SAF-01, SAF-02).
Registers Tier 0 and Tier 1 tools for managing local cluster nodes, querying topology,
dispatching constraint-aware workloads (speculative decoding, embeddings), and aborting tasks.
"""

from typing import Dict, Any, Optional

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.swarm_compute import (
    SwarmComputeGetTopologyArgs,
    SwarmComputeRegisterNodeArgs,
    SwarmComputeOffloadWorkloadArgs,
    SwarmComputeAbortWorkloadArgs,
    ComputeNodeType,
    WorkloadType,
)
from services.backend.swarm_compute.node_manager import swarm_node_manager
from services.backend.swarm_compute.workload_scheduler import swarm_workload_scheduler


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="swarm_compute_get_topology",
    tier=0,
    description="Inspects active local P2P swarm compute cluster topology, online nodes, and hardware telemetry (Read-Only)",
    args_schema=SwarmComputeGetTopologyArgs,
    preview_fn=lambda a: "Inspect local swarm compute cluster nodes and hardware metrics (Read-Only)",
)
def swarm_compute_get_topology(**kwargs) -> Dict[str, Any]:
    """Inspect swarm compute topology."""
    state = swarm_workload_scheduler.get_cluster_state()
    return {
        "status": "success",
        "cluster_state": state.model_dump(),
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

@registry.register(
    name="swarm_compute_register_node",
    tier=1,
    description="Registers or updates a local mesh peer node with battery, thermal, and memory telemetry (Reversible change with preview)",
    args_schema=SwarmComputeRegisterNodeArgs,
    preview_fn=lambda a: (
        f"Register swarm peer node '{a.get('node_id') if isinstance(a, dict) else getattr(a, 'node_id', '')}' "
        f"({a.get('device_name') if isinstance(a, dict) else getattr(a, 'device_name', '')}) "
        f"[type: {a.get('node_type') if isinstance(a, dict) else getattr(a, 'node_type', 'LAPTOP_HYBRID')}, "
        f"battery: {a.get('battery_percent', 100) if isinstance(a, dict) else getattr(a, 'battery_percent', 100)}%]"
    ),
)
def swarm_compute_register_node(
    node_id: str,
    device_name: str,
    node_type: str = "LAPTOP_HYBRID",
    available_vram_mb: int = 0,
    available_ram_mb: int = 4096,
    battery_percent: int = 100,
    is_plugged_in: bool = True,
    thermal_throttled: bool = False,
    compute_flops_rating: float = 1.0,
    **kwargs,
) -> Dict[str, Any]:
    """Register or update a peer compute node."""
    if guardian.is_halted or swarm_workload_scheduler.is_halted():
        raise PermissionError("Swarm compute operations halted by Guardian kill switch.")

    node = swarm_node_manager.register_node(
        node_id=node_id,
        device_name=device_name,
        node_type=node_type,
        available_vram_mb=available_vram_mb,
        available_ram_mb=available_ram_mb,
        battery_percent=battery_percent,
        is_plugged_in=is_plugged_in,
        thermal_throttled=thermal_throttled,
        compute_flops_rating=compute_flops_rating,
    )

    return {
        "status": "success",
        "node": node.model_dump(),
    }


@registry.register(
    name="swarm_compute_offload_workload",
    tier=1,
    description="Partitions and offloads a compute workload (speculative decoding, embeddings, indexing) across eligible cluster peers (Reversible change with preview)",
    args_schema=SwarmComputeOffloadWorkloadArgs,
    preview_fn=lambda a: (
        f"Offload compute workload '{a.get('workload_type') if isinstance(a, dict) else getattr(a, 'workload_type', 'EMBEDDING_BATCH')}' "
        f"({a.get('items_count', 10) if isinstance(a, dict) else getattr(a, 'items_count', 10)} items) "
        f"across local mesh cluster"
    ),
)
def swarm_compute_offload_workload(
    workload_type: str,
    items_count: int = 10,
    preferred_node_id: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Offload a compute task to a mesh peer."""
    if guardian.is_halted or swarm_workload_scheduler.is_halted():
        raise PermissionError("Swarm compute operations halted by Guardian kill switch.")

    task = swarm_workload_scheduler.dispatch_workload(
        workload_type=workload_type,
        items_count=items_count,
        preferred_node_id=preferred_node_id,
    )

    return {
        "status": "success",
        "task": task.model_dump(),
    }


@registry.register(
    name="swarm_compute_abort_workload",
    tier=1,
    description="Aborts an in-flight distributed workload task on a swarm peer (Reversible change with preview)",
    args_schema=SwarmComputeAbortWorkloadArgs,
    preview_fn=lambda a: (
        f"Abort in-flight swarm compute task '{a.get('task_id') if isinstance(a, dict) else getattr(a, 'task_id', '')}'"
    ),
)
def swarm_compute_abort_workload(
    task_id: str,
    **kwargs,
) -> Dict[str, Any]:
    """Abort a distributed workload."""
    if guardian.is_halted or swarm_workload_scheduler.is_halted():
        raise PermissionError("Swarm compute operations halted by Guardian kill switch.")

    aborted = swarm_workload_scheduler.abort_workload(task_id)
    return {
        "status": "success" if aborted else "not_found",
        "task_id": task_id,
        "aborted": aborted,
    }
