"""
P2P Mesh Schemas and Data Contracts for Phenom Milestone 10.0
Defines cryptographic message frames, discovery beacons, ephemeral pairing payloads,
approval cards, telemetry streams, GraphRAG sync deltas, and tool argument models.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MeshMessageType(str, Enum):
    PAIR_REQUEST = "pair_request"
    PAIR_RESPONSE = "pair_response"
    APPROVAL_CARD_PUSH = "approval_card_push"
    APPROVAL_DECISION = "approval_decision"
    SWARM_STREAM = "swarm_stream"
    MISSION_STREAM = "mission_stream"
    GRAPHRAG_DELTA_SYNC = "graphrag_delta_sync"
    VOICE_AUDIO_CHUNK = "voice_audio_chunk"
    HEARTBEAT = "heartbeat"


class MeshDeviceRole(str, Enum):
    HOST_DESKTOP = "host_desktop"
    COMPANION_MOBILE = "companion_mobile"
    COMPANION_TABLET = "companion_tablet"
    COMPANION_LAPTOP = "companion_laptop"


class MeshDiscoveryBeacon(BaseModel):
    protocol: str = "phenom-mesh/1.0"
    node_id: str
    device_name: str
    host: str
    port: int
    tls_fingerprint: str
    capabilities: List[str] = Field(default_factory=lambda: ["approvals", "telemetry", "graph_sync", "voice"])
    timestamp: float


class EphemeralPairingPayload(BaseModel):
    node_id: str
    host: str
    port: int
    token: str
    tls_fingerprint: str
    expires_at: float
    pairing_uri: str
    qr_matrix_svg: Optional[str] = None
    qr_png_base64: Optional[str] = None


class PairedDeviceProfile(BaseModel):
    node_id: str
    device_name: str
    device_role: MeshDeviceRole = MeshDeviceRole.COMPANION_MOBILE
    shared_secret_hash: str
    paired_at: float
    last_seen_at: float
    ip_address: Optional[str] = None
    authorized_scopes: List[str] = Field(
        default_factory=lambda: ["approvals", "telemetry", "graph_sync", "voice"]
    )


class EncryptedMeshFrame(BaseModel):
    magic: bytes = b"PHN1"
    msg_type: int
    sequence: int
    nonce: bytes
    ciphertext: bytes


class CompanionApprovalCard(BaseModel):
    request_id: str
    tier: int
    tool_name: str
    action_verb: str
    item_count: int = 1
    target_summary: str
    one_line_summary: str
    diff_preview: Optional[str] = None
    created_at: float
    timeout_seconds: Optional[int] = 60


class CompanionApprovalDecision(BaseModel):
    request_id: str
    decision: str  # "approved" or "denied"
    node_id: str
    decided_at: float
    signature: str


class GraphSyncDelta(BaseModel):
    sync_id: str
    origin_node_id: str
    timestamp: float
    node_deltas: List[Dict[str, Any]] = Field(default_factory=list)
    edge_deltas: List[Dict[str, Any]] = Field(default_factory=list)


# --- Tool Argument Models ---

class MeshGetPairedDevicesArgs(BaseModel):
    include_offline: bool = Field(
        default=True,
        description="Whether to include registered paired companion devices that are currently offline."
    )


class MeshGeneratePairingQrArgs(BaseModel):
    ttl_seconds: int = Field(
        default=120,
        ge=30,
        le=600,
        description="Lifetime of the single-use pairing token in seconds (default 120s)."
    )


class MeshSyncPushArgs(BaseModel):
    target_node_id: Optional[str] = Field(
        default=None,
        description="Target companion node ID to push state to, or None to broadcast to all paired devices."
    )
    sync_type: str = Field(
        default="graphrag",
        description="Type of synchronization payload to push ('graphrag', 'approvals', 'telemetry')."
    )


class MeshUnpairDeviceArgs(BaseModel):
    node_id: str = Field(
        ...,
        description="Node ID of the paired companion device to revoke and unpair."
    )
