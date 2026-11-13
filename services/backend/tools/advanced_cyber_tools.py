"""
Phenom Advanced Cyber Warfare & Defensive Intelligence Tools
Registers:
1. Sigma Rule Real-Time Telemetry Correlation (evaluate_sigma_telemetry)
2. IoT Firmware & Binwalk Security Triage (triage_iot_firmware)
3. P2P Encrypted Mesh Bridge Management (start_p2p_mesh_node, broadcast_p2p_directive, list_p2p_mesh_peers)
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.sigma_siem import sigma_siem
from services.backend.cyber.firmware_triage import firmware_triage
from services.backend.cyber.p2p_mesh import p2p_mesh


# 1. Sigma SIEM
class SigmaEvaluateArgs(BaseModel):
    events: List[Dict[str, Any]] = Field(description="List of telemetry events to evaluate against Sigma detection rules")

@registry.register(
    name="evaluate_sigma_telemetry",
    tier=0,
    description="Correlates Windows/Sysmon telemetry events against in-memory Sigma threat rules mapped to MITRE ATT&CK.",
    args_schema=SigmaEvaluateArgs,
    preview_fn=lambda a: f"Evaluate {len(a.get('events', []))} telemetry event(s) against Sigma detection rules",
    can_remember_per_folder=False
)
def evaluate_sigma_telemetry(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    return sigma_siem.run_siem_correlation_sweep(events)


# 2. IoT Firmware Triage
class FirmwareTriageArgs(BaseModel):
    file_path: str = Field(description="Absolute path to firmware binary image (.bin, .rom, .img)")

@registry.register(
    name="triage_iot_firmware",
    tier=0,
    description="Inspects embedded IoT firmware binary images for filesystem headers (SquashFS, U-Boot) and hardcoded private keys.",
    args_schema=FirmwareTriageArgs,
    preview_fn=lambda a: f"Triage IoT firmware image: {a.get('file_path')}",
    can_remember_per_folder=False
)
def triage_iot_firmware(file_path: str) -> Dict[str, Any]:
    return firmware_triage.analyze_firmware_image(file_path)


# 3. P2P Mesh
class StartMeshArgs(BaseModel):
    port: int = Field(default=53530, description="UDP discovery port (defaults to 53530)")

@registry.register(
    name="start_p2p_mesh_node",
    tier=0,
    description="Starts the local peer-to-peer encrypted mesh bridge for decentralized Jarvis node synchronization.",
    args_schema=StartMeshArgs,
    preview_fn=lambda a: f"Start P2P encrypted mesh node on port {a.get('port', 53530)}",
    can_remember_per_folder=False
)
def start_p2p_mesh_node(port: int = 53530) -> Dict[str, Any]:
    return p2p_mesh.start_mesh(port=port)


class BroadcastMeshArgs(BaseModel):
    directive_type: str = Field(description="Directive action name (e.g. SYNC_STATE, THREAT_ALERT)")
    payload: Dict[str, Any] = Field(description="Payload dictionary to sync across mesh")

@registry.register(
    name="broadcast_p2p_directive",
    tier=1,
    description="Broadcasts an authenticated encrypted directive to all discovered mesh peer nodes.",
    args_schema=BroadcastMeshArgs,
    preview_fn=lambda a: f"Broadcast P2P mesh directive: {a.get('directive_type')}",
    can_remember_per_folder=False
)
def broadcast_p2p_directive(directive_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return p2p_mesh.broadcast_mesh_directive(directive_type=directive_type, payload=payload)


class ListPeersArgs(BaseModel):
    pass

@registry.register(
    name="list_p2p_mesh_peers",
    tier=0,
    description="Lists active discovered peer nodes across the local P2P encrypted mesh network.",
    args_schema=ListPeersArgs,
    preview_fn=lambda a: "List active P2P mesh peer nodes",
    can_remember_per_folder=False
)
def list_p2p_mesh_peers() -> List[Dict[str, Any]]:
    return p2p_mesh.list_peers()
