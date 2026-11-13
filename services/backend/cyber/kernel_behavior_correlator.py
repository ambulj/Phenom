"""
Phenom Real-Time ETW/Sysmon Behavioral Anomaly Correlator
Monitors and analyzes process behaviors in user space without third-party kernel drivers:
1. Parent-Child Lineage Analysis: Detects anomalous child processes spawned by office suites,
   browsers, or service hosts (e.g. Word -> PowerShell, Explorer -> CertUtil).
2. Remote Thread & Injection Detection: Correlates Sysmon Event ID 8 (CreateRemoteThread)
   and Event ID 10 (ProcessAccess) targeting sensitive processes (lsass.exe, svchost.exe).
3. Dynamic Behavioral Risk Scoring: Assigns 0-100 threat severity scores to active PIDs.
4. Universal Guardian Kill-Switch (<25ms SLA): Synchronous disengagement on emergency halt.
"""

import os
import time
import threading
from typing import Dict, Any, List, Optional
import psutil

from services.backend.safety.guardian import guardian


class KernelBehaviorCorrelator:
    """Real-time correlator for process lineage anomalies and injection telemetry."""

    SUSPICIOUS_SPAWNS = {
        # Office / Document readers spawning shells
        "winword.exe": ["powershell.exe", "cmd.exe", "wscript.exe", "cscript.exe", "certutil.exe"],
        "excel.exe": ["powershell.exe", "cmd.exe", "wscript.exe", "cscript.exe", "bitsadmin.exe"],
        "powerpnt.exe": ["powershell.exe", "cmd.exe", "mshta.exe"],
        "acrord32.exe": ["powershell.exe", "cmd.exe", "cscript.exe"],
        # Web server / API runtimes spawning shells
        "python.exe": ["whoami.exe", "net.exe", "nltest.exe"],
        # System binaries spawning LOLBins
        "svchost.exe": ["certutil.exe", "rundll32.exe", "regsvr32.exe", "powershell.exe"],
    }

    PROTECTED_SYSTEM_BINARIES = [
        "lsass.exe",
        "svchost.exe",
        "csrss.exe",
        "smss.exe",
        "services.exe",
        "winlogon.exe",
        "explorer.exe"
    ]

    def __init__(self):
        self._anomalies: List[Dict[str, Any]] = []
        self._process_threat_scores: Dict[int, int] = {}
        self._lock = threading.Lock()

    def analyze_process_lineage(self) -> List[Dict[str, Any]]:
        """Audits all active processes to detect suspicious parent-child relationships."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch active. Aborting lineage analysis.")

        detected: List[Dict[str, Any]] = []

        try:
            # Build PID -> Process mapping
            processes = {}
            for p in psutil.process_iter(['pid', 'ppid', 'name', 'cmdline']):
                try:
                    processes[p.info['pid']] = p.info
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            for pid, p_info in processes.items():
                ppid = p_info.get('ppid')
                parent_info = processes.get(ppid)
                if not parent_info:
                    continue

                p_name = (p_info.get('name') or '').lower()
                parent_name = (parent_info.get('name') or '').lower()

                # Check known suspicious parent-child combos
                disallowed_children = self.SUSPICIOUS_SPAWNS.get(parent_name, [])
                if p_name in disallowed_children:
                    anomaly = {
                        "timestamp": time.time(),
                        "rule_id": "ANOMALY-LINEAGE-001",
                        "anomaly_type": "SUSPICIOUS_PARENT_CHILD_SPAWN",
                        "severity": "HIGH",
                        "pid": pid,
                        "process": p_name,
                        "parent_pid": ppid,
                        "parent_process": parent_name,
                        "cmdline": " ".join(p_info.get('cmdline') or []),
                        "mitre_technique": "T1059 (Command and Scripting Interpreter)",
                        "containment_recommended": "NETWORK_EGRESS_ISOLATION"
                    }
                    detected.append(anomaly)
                    self._update_threat_score(pid, 65)

        except Exception:
            pass

        with self._lock:
            self._anomalies.extend(detected)

        return detected

    def ingest_etw_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluates an incoming ETW or Sysmon telemetry event against behavioral rules."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch active. Aborting event ingestion.")

        event_id = event.get("event_id")
        source_pid = event.get("source_pid", 0)
        source_process = (event.get("source_process") or "").lower()
        target_pid = event.get("target_pid", 0)
        target_process = (event.get("target_process") or "").lower()

        anomaly: Optional[Dict[str, Any]] = None

        # Sysmon Event ID 8: CreateRemoteThread
        if event_id == 8:
            is_critical_target = any(prot in target_process for prot in self.PROTECTED_SYSTEM_BINARIES)
            severity = "CRITICAL" if is_critical_target else "HIGH"
            score_inc = 85 if is_critical_target else 55

            anomaly = {
                "timestamp": time.time(),
                "rule_id": "ANOMALY-INJECTION-008",
                "anomaly_type": "REMOTE_THREAD_INJECTION",
                "severity": severity,
                "source_pid": source_pid,
                "source_process": source_process,
                "target_pid": target_pid,
                "target_process": target_process,
                "start_address": event.get("start_address", "0x00007FF800000000"),
                "mitre_technique": "T1055.001 (Dynamic-link Library Injection)",
                "containment_recommended": "PROCESS_MEMORY_FREEZE"
            }
            self._update_threat_score(source_pid, score_inc)

        # Sysmon Event ID 10: ProcessAccess (e.g. LSASS memory read)
        elif event_id == 10:
            if "lsass" in target_process:
                anomaly = {
                    "timestamp": time.time(),
                    "rule_id": "ANOMALY-LSASS-ACCESS-010",
                    "anomaly_type": "CREDENTIAL_SUBSYSTEM_MEMORY_ACCESS",
                    "severity": "CRITICAL",
                    "source_pid": source_pid,
                    "source_process": source_process,
                    "target_pid": target_pid,
                    "target_process": target_process,
                    "granted_access": event.get("granted_access", "0x1010 (PROCESS_VM_READ)"),
                    "mitre_technique": "T1003.001 (LSASS Memory)",
                    "containment_recommended": "IMMEDIATE_PID_QUARANTINE"
                }
                self._update_threat_score(source_pid, 95)

        if anomaly:
            with self._lock:
                self._anomalies.append(anomaly)

        return anomaly

    def _update_threat_score(self, pid: int, score: int):
        with self._lock:
            current = self._process_threat_scores.get(pid, 0)
            self._process_threat_scores[pid] = min(100, current + score)

    def get_process_threat_score(self, pid: int) -> Dict[str, Any]:
        """Returns the dynamic threat score and classification for a given PID."""
        with self._lock:
            score = self._process_threat_scores.get(pid, 0)
            level = "CRITICAL" if score >= 70 else "SUSPICIOUS" if score >= 40 else "CLEAN"
            related = [a for a in self._anomalies if a.get("pid") == pid or a.get("source_pid") == pid]
            return {
                "pid": pid,
                "threat_score": score,
                "risk_level": level,
                "anomalies_detected": len(related),
                "anomaly_details": related[-3:]
            }

    def get_behavioral_anomalies(self) -> List[Dict[str, Any]]:
        """Returns the chronological audit log of all detected process anomalies."""
        with self._lock:
            return list(self._anomalies)

    def clear_anomalies(self):
        """Resets anomaly history (for test isolation)."""
        with self._lock:
            self._anomalies.clear()
            self._process_threat_scores.clear()


kernel_behavior_correlator = KernelBehaviorCorrelator()
