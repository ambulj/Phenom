from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class MeshNodeStatus(str, Enum):
    DISCOVERED = "discovered"
    AUTHENTICATED = "authenticated"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class MeshPeerNode(BaseModel):
    node_id: str
    device_name: str
    ip_address: str
    port: int
    capabilities: List[str] = Field(default_factory=list)
    status: MeshNodeStatus
    last_seen: float
    signature_verified: bool = True


class MeshTaskDelegation(BaseModel):
    task_id: str
    target_node_id: str
    capability_required: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: str
    latency_ms: float
    timestamp: float


class MultiAgentMeshState(BaseModel):
    local_node_id: str
    is_advertising: bool
    peers: Dict[str, MeshPeerNode] = Field(default_factory=dict)
    total_delegated_tasks: int = 0
    recent_delegations: List[MeshTaskDelegation] = Field(default_factory=list)


class MeshGetStatusArgs(BaseModel):
    include_recent: bool = True


class MeshDiscoverPeersArgs(BaseModel):
    scan_timeout_seconds: float = Field(2.0, ge=0.5, le=10.0, description="Duration in seconds to listen for mDNS/UDP discovery beacons")


class MeshDelegateTaskArgs(BaseModel):
    target_node_id: str = Field(..., description="Destination peer node ID")
    capability_required: str = Field(..., description="Required remote capability, e.g. gpu_compute or audio_transcription")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task arguments and execution parameters")


class MeshDisconnectPeerArgs(BaseModel):
    node_id: str = Field(..., description="Peer node ID to disconnect")
