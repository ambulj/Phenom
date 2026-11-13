"""
Phenom Native Kali Linux Toolchain Registry
Registers:
1. execute_native_nmap_stream (Tier 1) - Runs Nmap with structured XML streaming parser
2. query_metasploit_rpc (Tier 1) - Interacts with Metasploit msfrpcd JSON-RPC service
3. stream_tshark_capture (Tier 0) - Dissects network traffic via TShark with credential redaction
4. audit_aircrack_monitors (Tier 0) - Analyzes 802.11 airwaves, BSSIDs, and deauth frames
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.kali_native_suite import kali_suite


# 1. Execute Native Nmap Stream
class NmapStreamArgs(BaseModel):
    target: str = Field(..., description="Target IP or local lab hostname to audit (must satisfy Safe-Mode)")
    arguments: Optional[str] = Field(default="-sT -p 80,443,8000,8080", description="Nmap CLI arguments")


def nmap_preview(args: Dict[str, Any]) -> str:
    target = args.get("target", "unknown")
    args_str = args.get("arguments", "-sT")
    return f"Execute native Nmap XML stream scan against authorized target '{target}' ({args_str})"


@registry.register(
    name="execute_native_nmap_stream",
    tier=1,
    description="Executes Nmap with real-time XML streaming parsing to catalog open ports, service versions, and NSE scripts within authorized lab subnets.",
    args_schema=NmapStreamArgs,
    preview_fn=nmap_preview,
    can_remember_per_folder=False
)
def execute_native_nmap_stream(target: str, arguments: str = "-sT -p 80,443,8000,8080") -> Dict[str, Any]:
    return kali_suite.execute_nmap_stream(target, arguments=arguments)


# 2. Query Metasploit RPC
class MetasploitRPCArgs(BaseModel):
    method: str = Field(..., description="Metasploit JSON-RPC method (e.g. core.version, module.exploits, session.list)")
    params: Optional[List[Any]] = Field(default=None, description="Positional parameters for the RPC method")
    rpc_host: Optional[str] = Field(default="127.0.0.1", description="msfrpcd service host")
    rpc_port: Optional[int] = Field(default=55553, description="msfrpcd service port")


def msf_preview(args: Dict[str, Any]) -> str:
    method = args.get("method", "unknown")
    host = args.get("rpc_host", "127.0.0.1")
    return f"Dispatch authorized Metasploit RPC call '{method}' to msfrpcd at {host}"


@registry.register(
    name="query_metasploit_rpc",
    tier=1,
    description="Dispatches a programmatic JSON-RPC query to local msfrpcd daemon to query modules, sessions, or execution status.",
    args_schema=MetasploitRPCArgs,
    preview_fn=msf_preview,
    can_remember_per_folder=False
)
def query_metasploit_rpc(
    method: str,
    params: Optional[List[Any]] = None,
    rpc_host: str = "127.0.0.1",
    rpc_port: int = 55553
) -> Dict[str, Any]:
    return kali_suite.query_metasploit_rpc(method, params=params, rpc_host=rpc_host, rpc_port=rpc_port)


# 3. Stream TShark Capture
class TSharkCaptureArgs(BaseModel):
    interface: Optional[str] = Field(default="eth0", description="Network interface name to capture packets on")
    packet_count: Optional[int] = Field(default=10, description="Number of packets to capture and dissect")
    filter_expr: Optional[str] = Field(default=None, description="Optional BPF capture filter expression")


@registry.register(
    name="stream_tshark_capture",
    tier=0,
    description="Captures and dissects live network packet frames via TShark, applying automatic credential and bearer token redaction.",
    args_schema=TSharkCaptureArgs,
    preview_fn=lambda a: f"Capture {a.get('packet_count', 10)} packets on interface '{a.get('interface', 'eth0')}' with credential redaction",
    can_remember_per_folder=False
)
def stream_tshark_capture(
    interface: str = "eth0",
    packet_count: int = 10,
    filter_expr: Optional[str] = None
) -> Dict[str, Any]:
    return kali_suite.stream_tshark_capture(interface=interface, packet_count=packet_count, filter_expr=filter_expr)


# 4. Audit Aircrack Monitors
class AuditAircrackArgs(BaseModel):
    pass


@registry.register(
    name="audit_aircrack_monitors",
    tier=0,
    description="Audits local wireless interfaces, scanning nearby 802.11 access points, associated clients, and detecting deauth frame bursts.",
    args_schema=AuditAircrackArgs,
    preview_fn=lambda a: "Audit 802.11 wireless airspace for rogue access points and deauth bursts",
    can_remember_per_folder=False
)
def audit_aircrack_monitors() -> Dict[str, Any]:
    return kali_suite.audit_wireless_interfaces()
