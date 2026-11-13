"""
Phenom Tactical Incident Response & RAM Forensics Tool Suite
Registers:
1. trigger_incident_pcap_dump (Tier 0) - Flushes in-memory packet ring buffer to disk
2. isolate_pid_network_egress (Tier 1) - Cuts off network sockets for suspicious PID
3. remove_pid_network_isolation (Tier 1) - Restores network connectivity for PID
4. dump_process_memory_forensics (Tier 0) - Scans process memory pages for IOCs
5. list_isolated_processes (Tier 0) - Queries currently isolated processes
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.incident_responder import incident_responder


# 1. PCAP Dump
class PCAPDumpArgs(BaseModel):
    alert_id: str = Field(description="Unique alert or incident identifier triggering the dump")
    output_dir: Optional[str] = Field(default=None, description="Directory path to save the PCAP dump")

@registry.register(
    name="trigger_incident_pcap_dump",
    tier=0,
    description="Flushes the rolling in-memory network packet buffer to disk as an incident PCAP artifact.",
    args_schema=PCAPDumpArgs,
    preview_fn=lambda a: f"Flush rolling network packet buffer to PCAP for alert: {a.get('alert_id')}",
    can_remember_per_folder=False
)
def trigger_incident_pcap_dump(alert_id: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    return incident_responder.trigger_incident_pcap_dump(alert_id=alert_id, output_dir=output_dir)


# 2. Isolate PID Egress
class IsolatePIDArgs(BaseModel):
    pid: int = Field(description="Process ID to isolate from network egress")

@registry.register(
    name="isolate_pid_network_egress",
    tier=1,
    description="Severs outbound network connections for a suspicious PID, preventing data exfiltration while keeping RAM intact.",
    args_schema=IsolatePIDArgs,
    preview_fn=lambda a: f"Sever outbound network egress for PID: {a.get('pid')}",
    can_remember_per_folder=False
)
def isolate_pid_network_egress(pid: int) -> Dict[str, Any]:
    return incident_responder.isolate_pid_network_egress(pid=pid)


# 3. Remove PID Isolation
class RemoveIsolationArgs(BaseModel):
    pid: int = Field(description="Process ID to restore network connectivity for")

@registry.register(
    name="remove_pid_network_isolation",
    tier=1,
    description="Removes network egress shielding and restores connectivity for the specified PID.",
    args_schema=RemoveIsolationArgs,
    preview_fn=lambda a: f"Restore network egress connectivity for PID: {a.get('pid')}",
    can_remember_per_folder=False
)
def remove_pid_network_isolation(pid: int) -> Dict[str, Any]:
    return incident_responder.remove_pid_isolation(pid=pid)


# 4. Dump Memory Forensics
class MemoryDumpArgs(BaseModel):
    pid: int = Field(description="Target process ID to perform memory forensics on")

@registry.register(
    name="dump_process_memory_forensics",
    tier=0,
    description="Samples user-mode process memory pages and triages for URLs, IPs, and Base64 IOCs without crashing the process.",
    args_schema=MemoryDumpArgs,
    preview_fn=lambda a: f"Extract and triage RAM memory strings for PID: {a.get('pid')}",
    can_remember_per_folder=False
)
def dump_process_memory_forensics(pid: int) -> Dict[str, Any]:
    return incident_responder.dump_process_memory_forensics(pid=pid)


# 5. List Isolated Processes
class ListIsolatedArgs(BaseModel):
    pass

@registry.register(
    name="list_isolated_processes",
    tier=0,
    description="Lists all processes currently under active network egress isolation.",
    args_schema=ListIsolatedArgs,
    preview_fn=lambda a: "List active network-isolated processes",
    can_remember_per_folder=False
)
def list_isolated_processes() -> List[Dict[str, Any]]:
    return incident_responder.list_isolated_processes()
