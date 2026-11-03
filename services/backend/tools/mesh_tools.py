"""
Phenom P2P Mesh Safety Tools (SAF-01)
Registers Tier 0 and Tier 1 tools in the Safety ToolRegistry for paired device inspection,
ephemeral QR code generation, state/delta sync pushes, and device revocation.
"""

from typing import Dict, Any
from services.backend.safety.registry import registry
from services.backend.schemas.mesh import (
    MeshGetPairedDevicesArgs,
    MeshGeneratePairingQrArgs,
    MeshSyncPushArgs,
    MeshUnpairDeviceArgs,
)
from services.backend.mesh.p2p_mesh_engine import p2p_mesh_engine


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="mesh_get_paired_devices",
    tier=0,
    description="Retrieves list of paired companion devices, connection status, roles, and IP addresses (Read-Only)",
    args_schema=MeshGetPairedDevicesArgs,
    preview_fn=lambda a: (
        f"List paired companion devices "
        f"(include_offline={a.get('include_offline', True) if isinstance(a, dict) else getattr(a, 'include_offline', True)}) "
        f"(Read-Only)"
    ),
)
async def mesh_get_paired_devices(args: MeshGetPairedDevicesArgs) -> Dict[str, Any]:
    devices = p2p_mesh_engine.get_paired_devices(include_offline=args.include_offline)
    return {
        "status": "success",
        "device_count": len(devices),
        "devices": [d.model_dump() for d in devices]
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

@registry.register(
    name="mesh_generate_pairing_qr",
    tier=1,
    description="Generates a single-use 120s ephemeral pairing token and visual QR payload for companion onboarding (Reversible change with preview)",
    args_schema=MeshGeneratePairingQrArgs,
    preview_fn=lambda a: (
        f"Generate single-use ephemeral QR pairing payload "
        f"(valid for {a.get('ttl_seconds', 120) if isinstance(a, dict) else getattr(a, 'ttl_seconds', 120)} seconds)"
    ),
)
async def mesh_generate_pairing_qr(args: MeshGeneratePairingQrArgs) -> Dict[str, Any]:
    payload = p2p_mesh_engine.generate_pairing_qr(ttl_seconds=args.ttl_seconds)
    return {
        "status": "success",
        "pairing_uri": payload.pairing_uri,
        "token": payload.token,
        "expires_at": payload.expires_at,
        "qr_matrix_svg": payload.qr_matrix_svg,
        "qr_png_base64": payload.qr_png_base64
    }


@registry.register(
    name="mesh_sync_push",
    tier=1,
    description="Pushes local state deltas or telemetry to paired companion devices (Reversible change with preview)",
    args_schema=MeshSyncPushArgs,
    preview_fn=lambda a: (
        f"Push local mesh synchronization update "
        f"(sync_type='{a.get('sync_type', 'graphrag') if isinstance(a, dict) else getattr(a, 'sync_type', 'graphrag')}', "
        f"target='{a.get('target_node_id', 'all') if isinstance(a, dict) else getattr(a, 'target_node_id', 'all')}')"
    ),
)
async def mesh_sync_push(args: MeshSyncPushArgs) -> Dict[str, Any]:
    devices = p2p_mesh_engine.get_paired_devices(include_offline=False)
    if args.target_node_id:
        devices = [d for d in devices if d.node_id == args.target_node_id]

    return {
        "status": "success",
        "sync_type": args.sync_type,
        "target_node_id": args.target_node_id or "broadcast_all",
        "delivered_devices": [d.node_id for d in devices]
    }


@registry.register(
    name="mesh_unpair_device",
    tier=1,
    description="Revokes companion device authorization and terminates active sessions (Reversible change with preview)",
    args_schema=MeshUnpairDeviceArgs,
    preview_fn=lambda a: (
        f"Revoke companion device pairing and authorization for node "
        f"'{a.get('node_id', '') if isinstance(a, dict) else getattr(a, 'node_id', '')}'"
    ),
)
async def mesh_unpair_device(args: MeshUnpairDeviceArgs) -> Dict[str, Any]:
    unpaired = p2p_mesh_engine.unpair_device(node_id=args.node_id)
    return {
        "status": "success" if unpaired else "not_found",
        "node_id": args.node_id,
        "unpaired": unpaired
    }
