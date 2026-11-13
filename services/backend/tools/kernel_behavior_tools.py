"""
Phenom Real-Time Kernel Behavioral Anomaly Tools
Registers:
1. audit_process_lineage (Tier 0) - Audits process execution trees for parent-child anomalies
2. get_process_behavioral_score (Tier 0) - Queries threat score and anomalies for a target PID
3. get_behavioral_anomalies_log (Tier 0) - Retrieves chronological log of detected anomalies
4. evaluate_etw_threat_event (Tier 1) - Ingests and evaluates raw ETW/Sysmon telemetry event
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.kernel_behavior_correlator import kernel_behavior_correlator


# 1. Audit Process Lineage
class AuditProcessLineageArgs(BaseModel):
    pass


@registry.register(
    name="audit_process_lineage",
    tier=0,
    description="Audits the active Windows process tree in real-time to identify anomalous parent-child LOLBin invocations.",
    args_schema=AuditProcessLineageArgs,
    preview_fn=lambda a: "Audit active process execution trees for lineage anomalies",
    can_remember_per_folder=False
)
def audit_process_lineage() -> List[Dict[str, Any]]:
    return kernel_behavior_correlator.analyze_process_lineage()


# 2. Get Process Threat Score
class ProcessScoreArgs(BaseModel):
    pid: int = Field(..., description="Target process ID to inspect")


@registry.register(
    name="get_process_behavioral_score",
    tier=0,
    description="Queries the dynamic behavioral threat score (0-100) and risk classification for a given PID.",
    args_schema=ProcessScoreArgs,
    preview_fn=lambda a: f"Query behavioral threat score for PID {a.get('pid')}",
    can_remember_per_folder=False
)
def get_process_behavioral_score(pid: int) -> Dict[str, Any]:
    return kernel_behavior_correlator.get_process_threat_score(pid)


# 3. Get Behavioral Anomalies Log
class BehavioralLogArgs(BaseModel):
    pass


@registry.register(
    name="get_behavioral_anomalies_log",
    tier=0,
    description="Retrieves the chronological audit log of all detected process anomalies and injection attempts.",
    args_schema=BehavioralLogArgs,
    preview_fn=lambda a: "Retrieve behavioral anomalies log",
    can_remember_per_folder=False
)
def get_behavioral_anomalies_log() -> List[Dict[str, Any]]:
    return kernel_behavior_correlator.get_behavioral_anomalies()


# 4. Evaluate ETW Threat Event
class EvaluateETWEventArgs(BaseModel):
    event_id: int = Field(..., description="Sysmon or ETW Event ID (e.g. 8 for RemoteThread, 10 for ProcessAccess)")
    source_pid: int = Field(..., description="Source process ID")
    source_process: str = Field(..., description="Source process name (e.g. 'mimikatz.exe', 'powershell.exe')")
    target_pid: int = Field(..., description="Target process ID")
    target_process: str = Field(..., description="Target process name (e.g. 'lsass.exe', 'svchost.exe')")
    start_address: Optional[str] = Field(default="0x00007FF800000000", description="Thread start address or memory location")
    granted_access: Optional[str] = Field(default="0x1010", description="Access mask requested")


def evaluate_etw_event_preview(args: Dict[str, Any]) -> str:
    return f"Evaluate ETW Event ID {args.get('event_id')} from PID {args.get('source_pid')} ({args.get('source_process')}) -> PID {args.get('target_pid')} ({args.get('target_process')})"


@registry.register(
    name="evaluate_etw_threat_event",
    tier=1,
    description="Ingests a raw ETW or Sysmon telemetry event to correlate injection techniques, update process threat scores, and trigger containment recommendations.",
    args_schema=EvaluateETWEventArgs,
    preview_fn=evaluate_etw_event_preview,
    can_remember_per_folder=False
)
def evaluate_etw_threat_event(
    event_id: int,
    source_pid: int,
    source_process: str,
    target_pid: int,
    target_process: str,
    start_address: str = "0x00007FF800000000",
    granted_access: str = "0x1010"
) -> Dict[str, Any]:
    event = {
        "event_id": event_id,
        "source_pid": source_pid,
        "source_process": source_process,
        "target_pid": target_pid,
        "target_process": target_process,
        "start_address": start_address,
        "granted_access": granted_access,
    }
    anomaly = kernel_behavior_correlator.ingest_etw_event(event)
    return {
        "event_evaluated": event,
        "anomaly_triggered": anomaly is not None,
        "anomaly": anomaly or "NO_ANOMALY_DETECTED",
        "process_score": kernel_behavior_correlator.get_process_threat_score(source_pid)
    }
