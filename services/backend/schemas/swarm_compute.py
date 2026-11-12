"""
Distributed Swarm Compute & Offline Mesh P2P Offloading Schemas (SWM-01, SAF-01, SAF-02).
Defines Pydantic v2 models for:
- Compute node telemetry, device classes, and thermal/battery constraints
- Distributed workload partitioning (speculative decoding, embeddings, indexing)
- Cluster health, dynamic failover tracking, and load balancing factors
- Safety tool argument schemas for cluster governance
"""

import time
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class ComputeNodeType(str, Enum):
    DESKTOP_GPU = "DESKTOP_GPU"        # High-VRAM local NVIDIA host
    LAPTOP_HYBRID = "LAPTOP_HYBRID"    # Battery/thermal-aware worker
    MOBILE_COMPANION = "MOBILE_COMPANION"  # Phone/tablet edge helper (embeddings only)
    EDGE_NODE = "EDGE_NODE"            # Headless local worker


class WorkloadType(str, Enum):
    SPECULATIVE_DECODING = "SPECULATIVE_DECODING"
    EMBEDDING_BATCH = "EMBEDDING_BATCH"
    DOCUMENT_INDEXING = "DOCUMENT_INDEXING"
    INFERENCE_PROBE = "INFERENCE_PROBE"


class WorkloadStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class SwarmNodeTelemetry(BaseModel):
    """Real-time capability and health metrics of a local swarm peer."""
    model_config = ConfigDict(use_enum_values=True)

    node_id: str = Field(..., description="Unique node identifier")
    device_name: str = Field(..., description="Human-readable device name")
    node_type: ComputeNodeType = Field(default=ComputeNodeType.DESKTOP_GPU, description="Hardware classification")
    available_vram_mb: int = Field(default=0, ge=0, description="Free GPU VRAM in megabytes")
    available_ram_mb: int = Field(default=1024, ge=0, description="Free system RAM in megabytes")
    battery_percent: int = Field(default=100, ge=0, le=100, description="Current battery percentage (0-100)")
    is_plugged_in: bool = Field(default=True, description="Whether node is connected to AC power")
    thermal_throttled: bool = Field(default=False, description="Whether node is currently experiencing thermal throttling")
    compute_flops_rating: float = Field(default=1.0, ge=0.1, le=100.0, description="Relative compute capability multiplier")
    is_online: bool = Field(default=True, description="Online connectivity flag")
    last_heartbeat: float = Field(default_factory=time.time, description="Last heartbeat epoch timestamp")


class DistributedWorkloadTask(BaseModel):
    """An individual compute task dispatched across the local swarm mesh."""
    model_config = ConfigDict(use_enum_values=True)

    task_id: str = Field(..., description="Unique task identifier")
    workload_type: WorkloadType = Field(..., description="Type of compute task")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task inputs or batch chunk")
    assigned_node_id: str = Field(..., description="Node currently assigned to compute this task")
    status: WorkloadStatus = Field(default=WorkloadStatus.PENDING, description="Current task lifecycle status")
    assigned_at: float = Field(default_factory=time.time, description="Assignment epoch timestamp")
    completed_at: Optional[float] = Field(default=None, description="Completion epoch timestamp")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Output payload upon completion")
    error: Optional[str] = Field(default=None, description="Error explanation if failed")
    failover_count: int = Field(default=0, ge=0, description="Number of times task was re-routed due to peer drop")


class SwarmClusterState(BaseModel):
    """Global topology state and aggregated capacity of the swarm mesh."""
    model_config = ConfigDict(use_enum_values=True)

    cluster_id: str = Field(default="phenom-local-cluster", description="Local swarm cluster identifier")
    active_node_count: int = Field(default=1, description="Number of currently active online nodes")
    total_vram_mb: int = Field(default=0, description="Total aggregated free VRAM across cluster")
    total_ram_mb: int = Field(default=0, description="Total aggregated free RAM across cluster")
    nodes: List[SwarmNodeTelemetry] = Field(default_factory=list, description="Registered cluster peer nodes")
    active_workload_count: int = Field(default=0, description="Number of tasks currently in RUNNING state")
    cluster_load_factor: float = Field(default=0.0, ge=0.0, le=1.0, description="Aggregate utilization ratio")
    is_healthy: bool = Field(default=True, description="Overall cluster operational health")
    last_updated: float = Field(default_factory=time.time, description="Last update epoch timestamp")


# ==========================================
# Tool Argument Schemas (SAF-01)
# ==========================================

class SwarmComputeGetTopologyArgs(BaseModel):
    """Arguments for querying local swarm compute topology and nodes (Tier 0)."""
    model_config = ConfigDict(extra="forbid")


class SwarmComputeRegisterNodeArgs(BaseModel):
    """Arguments for registering or updating a peer compute node (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., min_length=1, max_length=64, description="Unique node identifier")
    device_name: str = Field(..., min_length=1, max_length=100, description="Device name")
    node_type: str = Field(default="LAPTOP_HYBRID", description="Node type: DESKTOP_GPU, LAPTOP_HYBRID, MOBILE_COMPANION, EDGE_NODE")
    available_vram_mb: int = Field(default=0, ge=0, description="Free VRAM in MB")
    available_ram_mb: int = Field(default=4096, ge=0, description="Free RAM in MB")
    battery_percent: int = Field(default=100, ge=0, le=100, description="Battery percentage (0-100)")
    is_plugged_in: bool = Field(default=True, description="Is AC plugged in")
    thermal_throttled: bool = Field(default=False, description="Is thermal throttled")
    compute_flops_rating: float = Field(default=1.0, ge=0.1, le=100.0, description="Relative compute rating")


class SwarmComputeOffloadWorkloadArgs(BaseModel):
    """Arguments for dispatching a distributed compute workload (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    workload_type: str = Field(..., description="Workload: SPECULATIVE_DECODING, EMBEDDING_BATCH, DOCUMENT_INDEXING, INFERENCE_PROBE")
    items_count: int = Field(default=10, ge=1, le=1000, description="Number of items or batch slices")
    preferred_node_id: Optional[str] = Field(default=None, description="Optional target node identifier")


class SwarmComputeAbortWorkloadArgs(BaseModel):
    """Arguments for aborting an active distributed workload (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(..., min_length=1, max_length=64, description="ID of active workload task to abort")
