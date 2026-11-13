"""
Phenom Memory Integrity & Code Injection Guard Tool Suite
Registers:
1. scan_process_memory_integrity (Tier 0) - Scans target PID memory pages for RWX allocations
2. audit_system_memory_posture (Tier 0) - Audits running processes across the system for RWX pages
3. verify_process_pe_header (Tier 0) - Verifies in-memory PE header integrity to detect process hollowing
4. quarantine_anomalous_process (Tier 1) - Enforces non-destructive process containment (network egress severed)
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.memory_integrity_guard import memory_integrity_guard


# 1. Scan Process Memory Integrity
class ScanProcessMemoryArgs(BaseModel):
    pid: int = Field(..., description="Target process ID to audit for RWX memory pages")


@registry.register(
    name="scan_process_memory_integrity",
    tier=0,
    description="Audits virtual memory page protection attributes (VirtualQueryEx) for target PID to detect anomalous PAGE_EXECUTE_READWRITE (RWX) allocations.",
    args_schema=ScanProcessMemoryArgs,
    preview_fn=lambda a: f"Audit memory page protection attributes for PID {a.get('pid')}",
    can_remember_per_folder=False
)
def scan_process_memory_integrity(pid: int) -> Dict[str, Any]:
    return memory_integrity_guard.scan_process_memory(pid)


# 2. Audit System Memory Posture
class AuditSystemMemoryArgs(BaseModel):
    max_processes: Optional[int] = Field(default=25, description="Maximum number of user-space processes to scan")


@registry.register(
    name="audit_system_memory_posture",
    tier=0,
    description="Scans running user-space processes across the Windows system to identify active RWX memory pages or unbacked executable allocations.",
    args_schema=AuditSystemMemoryArgs,
    preview_fn=lambda a: f"Scan active system processes (max {a.get('max_processes', 25)}) for memory protection anomalies",
    can_remember_per_folder=False
)
def audit_system_memory_posture(max_processes: int = 25) -> Dict[str, Any]:
    return memory_integrity_guard.audit_system_rwx_pages(max_processes=max_processes)


# 3. Verify Process PE Header
class VerifyPEHeaderArgs(BaseModel):
    pid: int = Field(..., description="Target process ID to inspect for PE header integrity")


@registry.register(
    name="verify_process_pe_header",
    tier=0,
    description="Validates in-memory DOS ('MZ') and NT ('PE') module headers for a target process to detect process hollowing or memory overwrites.",
    args_schema=VerifyPEHeaderArgs,
    preview_fn=lambda a: f"Verify in-memory PE header integrity for PID {a.get('pid')}",
    can_remember_per_folder=False
)
def verify_process_pe_header(pid: int) -> Dict[str, Any]:
    return memory_integrity_guard.verify_pe_header_integrity(pid)


# 4. Quarantine Anomalous Process
class QuarantineProcessArgs(BaseModel):
    pid: int = Field(..., description="Target process ID to place into non-destructive sandbox quarantine")


def quarantine_process_preview(args: Dict[str, Any]) -> str:
    return f"Enforce non-destructive quarantine on PID {args.get('pid')} (block outbound socket egress)"


@registry.register(
    name="quarantine_anomalous_process",
    tier=1,
    description="Enforces non-destructive sandbox containment on an anomalous process by severing network egress via Netsh firewall while keeping process RAM intact for forensics.",
    args_schema=QuarantineProcessArgs,
    preview_fn=quarantine_process_preview,
    can_remember_per_folder=False
)
def quarantine_anomalous_process(pid: int) -> Dict[str, Any]:
    return memory_integrity_guard.quarantine_process(pid)
