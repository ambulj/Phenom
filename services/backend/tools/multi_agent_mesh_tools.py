from typing import Dict, Any, Optional

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.multi_agent_mesh import (
    MeshGetStatusArgs,
    MeshDiscoverPeersArgs,
    MeshDelegateTaskArgs,
    MeshDisconnectPeerArgs,
)
from services.backend.mesh_protocol import local_mesh_peer_discovery


@registry.register(
    name="mesh_get_status",
    tier=0,
    description="Inspect local multi-agent mesh state, connected subnet peers, and delegation statistics (Read-Only)",
    args_schema=MeshGetStatusArgs,
    preview_fn=lambda args: "Querying multi-agent mesh state and connected subnet peers (Tier 0 read-only)",
)
def mesh_get_status(include_recent: bool = True, **kwargs) -> Dict[str, Any]:
    """Inspect mesh state and peer connectivity."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: mesh status query blocked.")
    return local_mesh_peer_discovery.get_status(include_recent=include_recent).model_dump()


@registry.register(
    name="mesh_discover_peers",
    tier=0,
    description="Scan local subnet for encrypted mDNS/UDP peer beacons (Read-Only)",
    args_schema=MeshDiscoverPeersArgs,
    preview_fn=lambda args: f"Scanning local subnet for peer beacons (timeout: {args.get('scan_timeout_seconds', 2.0)}s)",
)
def mesh_discover_peers(scan_timeout_seconds: float = 2.0, **kwargs) -> Dict[str, Any]:
    """Scan local subnet for peer beacons."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: peer discovery scan blocked.")
    peers = local_mesh_peer_discovery.discover_peers(scan_timeout_seconds=scan_timeout_seconds)
    return {"peers": [p.model_dump() for p in peers], "count": len(peers)}


def _preview_delegate_task(args: Dict[str, Any]) -> str:
    return (
        f"Delegate task requiring capability '{args.get('capability_required')}' "
        f"to subnet peer node '{args.get('target_node_id')}'"
    )


@registry.register(
    name="mesh_delegate_task",
    tier=1,
    description="Delegate a specialized compute, analysis, or sandbox task to an authenticated subnet peer (Tier 1 Preview)",
    args_schema=MeshDelegateTaskArgs,
    preview_fn=_preview_delegate_task,
)
def mesh_delegate_task(
    target_node_id: str,
    capability_required: str,
    payload: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Delegate task to a peer node."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: task delegation blocked.")
    res = local_mesh_peer_discovery.delegate_task(
        target_node_id=target_node_id,
        capability_required=capability_required,
        payload=payload or {},
    )
    return res.model_dump()


def _preview_disconnect_peer(args: Dict[str, Any]) -> str:
    return f"Disconnect subnet peer node '{args.get('node_id')}' from the mesh"


@registry.register(
    name="mesh_disconnect_peer",
    tier=1,
    description="Disconnect an authenticated subnet peer from the mesh network (Tier 1 Preview)",
    args_schema=MeshDisconnectPeerArgs,
    preview_fn=_preview_disconnect_peer,
)
def mesh_disconnect_peer(node_id: str, **kwargs) -> Dict[str, Any]:
    """Disconnect peer node from mesh."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: peer disconnect blocked.")
    disconnected = local_mesh_peer_discovery.disconnect_peer(node_id=node_id)
    return {"node_id": node_id, "disconnected": disconnected}
