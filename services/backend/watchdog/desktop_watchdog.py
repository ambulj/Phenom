"""Desktop Watchdog for Phenom (Milestone 25 Phase 4).

Monitors application hang states, crash modals, build errors, and system threshold alerts
in real-time without intrusive interruption (DOG-01.1).
"""

from __future__ import annotations

import datetime
import logging
import re
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.watchdog.desktop_watchdog")


class Rule8ViolationError(Exception):
    """Raised when an observed incident involves payment, checkout, or billing UI."""
    pass


class WatchdogIncident(BaseModel):
    incident_id: str = Field(default_factory=lambda: f"inc_{uuid.uuid4().hex[:8]}")
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    incident_type: str  # HUNG_PROCESS, CRASH_DIALOG, BUILD_FAILURE, HIGH_RESOURCE_USAGE, SYSTEM_ALERT
    process_name: str
    window_title: Optional[str] = None
    details: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    is_resolved: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DesktopWatchdog:
    """Continuous background event monitor for desktop abnormalities."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing|stripe|paypal)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._incidents: List[WatchdogIncident] = []
        self._sensitivity_mode: str = "BALANCED"  # CONSERVATIVE, BALANCED, AGGRESSIVE

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Desktop watchdog halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: incident involving payments or checkout is strictly prohibited. Found: {text}"
            )

    def record_incident(
        self,
        severity: str,
        incident_type: str,
        process_name: str,
        details: str,
        window_title: Optional[str] = None,
    ) -> WatchdogIncident:
        """Log a new desktop incident with Rule 8 screening."""
        self._check_guardian()
        self._validate_rule_8(process_name)
        self._validate_rule_8(details)
        if window_title:
            self._validate_rule_8(window_title)

        incident = WatchdogIncident(
            severity=severity.upper(),
            incident_type=incident_type.upper(),
            process_name=process_name,
            window_title=window_title,
            details=details,
        )
        self._incidents.insert(0, incident)
        # Cap log size to 50
        if len(self._incidents) > 50:
            self._incidents.pop()
        return incident

    def get_active_incidents(self, unresolved_only: bool = True) -> List[WatchdogIncident]:
        """Query active desktop incidents."""
        self._check_guardian()
        if unresolved_only:
            return [i for i in self._incidents if not i.is_resolved]
        return list(self._incidents)

    def resolve_incident(self, incident_id: str) -> bool:
        """Mark an incident as resolved."""
        self._check_guardian()
        for inc in self._incidents:
            if inc.incident_id == incident_id:
                inc.is_resolved = True
                return True
        return False

    def set_sensitivity(self, mode: str) -> str:
        """Adjust watchdog alert sensitivity policy."""
        self._check_guardian()
        mode_upper = mode.upper()
        if mode_upper in ("CONSERVATIVE", "BALANCED", "AGGRESSIVE"):
            self._sensitivity_mode = mode_upper
        return self._sensitivity_mode

    def get_system_health(self) -> Dict[str, Any]:
        """Compute aggregated health score based on unresolved incidents."""
        self._check_guardian()
        unresolved = [i for i in self._incidents if not i.is_resolved]
        critical_count = sum(1 for i in unresolved if i.severity == "CRITICAL")
        warning_count = sum(1 for i in unresolved if i.severity in ("WARNING", "ERROR"))

        if critical_count > 0:
            status = "CRITICAL"
            health_score = max(0.1, 0.4 - critical_count * 0.1)
        elif warning_count > 0:
            status = "DEGRADED"
            health_score = max(0.5, 0.9 - warning_count * 0.1)
        else:
            status = "HEALTHY"
            health_score = 1.0

        return {
            "status": status,
            "health_score": round(health_score, 2),
            "unresolved_count": len(unresolved),
            "sensitivity_mode": self._sensitivity_mode,
        }


# Singleton instance
desktop_watchdog = DesktopWatchdog()
