"""
Phenom Sigma Rule Real-Time SIEM & Threat Hunting Engine
Compiles and evaluates Sigma detection rules against Windows Security, System,
and Sysmon telemetry to detect adversary tradecraft mapped to the MITRE ATT&CK framework:
- T1059.001: PowerShell Encoded/Bypass Execution
- T1055: Process Injection & Hollowing (CreateRemoteThread)
- T1003.001: LSASS Memory Dumping via ProcessAccess
- T1547.001: Registry Run Keys / Startup Folder Persistence
- T1218: System Binary Proxy Execution (LOLBins: certutil, bitsadmin, mshta)
"""

import time
import re
from typing import Dict, Any, List, Optional
from services.backend.safety.guardian import guardian


class SigmaSIEMEngine:
    """Evaluates telemetry events against an in-memory database of Sigma threat rules."""

    DEFAULT_SIGMA_RULES = [
        {
            "id": "SIGMA-WIN-001",
            "title": "Suspicious PowerShell Encoded or Download Cradle",
            "technique": "T1059.001",
            "tactic": "Execution",
            "severity": "HIGH",
            "event_id": 4104,
            "patterns": [r"-enc(odedcommand)?\s+[a-za-z0-9+/=]{10,}", r"downloadstring", r"iex\s*\(", r"invoke-webrequest"]
        },
        {
            "id": "SIGMA-WIN-002",
            "title": "Remote Thread Injection into Core System Process",
            "technique": "T1055",
            "tactic": "Privilege Escalation / Defense Evasion",
            "severity": "CRITICAL",
            "event_id": 8,
            "patterns": [r"createremotethread", r"targetimage.*\\(svchost|explorer|lsass)\.exe"]
        },
        {
            "id": "SIGMA-WIN-003",
            "title": "Direct Process Access to LSASS Memory Space",
            "technique": "T1003.001",
            "tactic": "Credential Access",
            "severity": "CRITICAL",
            "event_id": 10,
            "patterns": [r"lsass\.exe", r"grantedaccess.*0x1010", r"process_vm_read"]
        },
        {
            "id": "SIGMA-WIN-004",
            "title": "System Binary Proxy Execution via CertUtil URLCache",
            "technique": "T1218",
            "tactic": "Defense Evasion",
            "severity": "HIGH",
            "event_id": 1,
            "patterns": [r"certutil(\.exe)?.*-urlcache", r"bitsadmin(\.exe)?.*\/transfer"]
        },
        {
            "id": "SIGMA-WIN-005",
            "title": "Persistence via Windows CurrentVersion Run Key",
            "technique": "T1547.001",
            "tactic": "Persistence",
            "severity": "MEDIUM",
            "event_id": 13,
            "patterns": [r"currentversion\\run", r"currentversion\\runonce"]
        }
    ]

    def __init__(self):
        self._rules = list(self.DEFAULT_SIGMA_RULES)
        self._alert_history: List[Dict[str, Any]] = []

    def get_loaded_rules(self) -> List[Dict[str, Any]]:
        """Returns the active catalog of loaded Sigma rules."""
        return self._rules

    def evaluate_event(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Matches a single normalized event against the loaded Sigma rules."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch active. Aborting SIEM evaluation.")

        matched_alerts = []
        raw_text = json_str = ""
        try:
            import json
            raw_text = json.dumps(event_data).lower()
        except Exception:
            raw_text = str(event_data).lower()

        event_id = event_data.get("event_id")

        for rule in self._rules:
            # Check event ID match if specified in event
            if event_id and rule.get("event_id") and event_id != rule["event_id"]:
                continue

            patterns = rule.get("patterns", [])
            for pat in patterns:
                if re.search(pat, raw_text, re.IGNORECASE):
                    alert = {
                        "alert_id": f"alert-{int(time.time() * 1000)}",
                        "rule_id": rule["id"],
                        "title": rule["title"],
                        "technique": rule["technique"],
                        "tactic": rule["tactic"],
                        "severity": rule["severity"],
                        "timestamp": time.time(),
                        "evidence": raw_text[:200]
                    }
                    matched_alerts.append(alert)
                    self._alert_history.append(alert)
                    break

        return matched_alerts

    def run_siem_correlation_sweep(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Correlates a batch of telemetry events into an incident report."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch active. Aborting SIEM sweep.")

        t0 = time.perf_counter()
        total_alerts = []
        for ev in events:
            alerts = self.evaluate_event(ev)
            total_alerts.extend(alerts)

        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for a in total_alerts:
            sev = a.get("severity", "LOW")
            if sev in severity_counts:
                severity_counts[sev] += 1

        overall_threat_level = "GREEN"
        if severity_counts["CRITICAL"] > 0:
            overall_threat_level = "CRITICAL (Immediate containment recommended)"
        elif severity_counts["HIGH"] > 0:
            overall_threat_level = "ELEVATED (Adversary persistence / LOLBin behavior detected)"
        elif severity_counts["MEDIUM"] > 0:
            overall_threat_level = "GUARDED"

        return {
            "events_analyzed": len(events),
            "rules_active": len(self._rules),
            "threat_level": overall_threat_level,
            "alerts_triggered": len(total_alerts),
            "severity_breakdown": severity_counts,
            "alerts": total_alerts,
            "analysis_duration_ms": round((time.perf_counter() - t0) * 1000, 2)
        }


sigma_siem = SigmaSIEMEngine()
