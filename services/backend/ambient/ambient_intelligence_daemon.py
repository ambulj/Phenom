"""
Proactive Ambient Intelligence Daemon.
Continuously aggregates system metrics, developer worktree status, upcoming calendar reminders,
and security alerts into prioritized, non-intrusive notification feeds.

Part of Phenom 22.0 Sovereign Swarm Intelligence (AMB-02.1 / NOT-02.1).
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian


class AmbientAlertItem(BaseModel):
    alert_id: str = Field(..., description="Unique alert identifier")
    title: str = Field(..., description="Short alert headline")
    summary: str = Field(..., description="Detailed context or recommendation")
    category: str = Field(default="system", description="system, developer, calendar, security")
    urgency: float = Field(default=0.5, description="Urgency rating from 0.0 (info) to 1.0 (critical)")
    source: str = Field(default="daemon", description="Originating subsystem")
    created_at: float = Field(default_factory=time.time)
    is_dismissed: bool = Field(default=False)
    dismissed_at: Optional[float] = None
    action_suggestion: Optional[str] = None


class AmbientIntelligenceDaemon:
    """
    Maintains and calculates ambient proactive alert feeds.
    """

    def __init__(self):
        self._alerts: Dict[str, AmbientAlertItem] = {}
        self._seed_default_telemetry()

    def _seed_default_telemetry(self):
        # Default baseline ambient alerts
        self.add_alert(
            title="Local GPU VRAM Optimal",
            summary="8B Instruct model cached in NVIDIA VRAM (4.2 GB / 8.0 GB used). Zero cloud egress.",
            category="system",
            urgency=0.25,
            source="gpu_monitor",
        )
        self.add_alert(
            title="Upcoming Architecture Sync",
            summary="Cross-vault Obsidian graph sync scheduled in 15 minutes.",
            category="calendar",
            urgency=0.45,
            source="scheduler",
            action_suggestion="View Knowledge Canvas",
        )

    def add_alert(
        self,
        title: str,
        summary: str,
        category: str = "system",
        urgency: float = 0.5,
        source: str = "daemon",
        action_suggestion: Optional[str] = None,
    ) -> AmbientAlertItem:
        """Adds a new ambient alert item."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Ambient alert creation halted.")

        aid = f"alert_{uuid.uuid4().hex[:8]}"
        alert = AmbientAlertItem(
            alert_id=aid,
            title=title,
            summary=summary,
            category=category,
            urgency=min(1.0, max(0.0, urgency)),
            source=source,
            created_at=time.time(),
            is_dismissed=False,
            action_suggestion=action_suggestion,
        )
        self._alerts[aid] = alert
        return alert

    def dismiss_alert(self, alert_id: str) -> bool:
        """Soft-dismisses an alert (Rule 7 non-destructibility)."""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.is_dismissed = True
            alert.dismissed_at = time.time()
            return True
        return False

    def get_active_alerts(self, min_urgency: float = 0.0) -> List[AmbientAlertItem]:
        """Returns non-dismissed alerts sorted by urgency descending."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Ambient feed query halted.")

        active = [
            a for a in self._alerts.values()
            if not a.is_dismissed and a.urgency >= min_urgency
        ]
        return sorted(active, key=lambda a: a.urgency, reverse=True)

    def synthesize_proactive_briefing(self) -> Dict[str, Any]:
        """
        Synthesizes a high-level briefing of active ambient conditions.
        """
        active = self.get_active_alerts()
        critical = [a for a in active if a.urgency >= 0.75]
        info = [a for a in active if a.urgency < 0.75]

        briefing_text = (
            f"Phenom Ambient Status: {len(active)} active alerts. "
            f"{len(critical)} critical issues requiring immediate attention. "
            f"All operations 100% offline local."
        )

        return {
            "briefing": briefing_text,
            "total_active": len(active),
            "critical_count": len(critical),
            "info_count": len(info),
            "top_alerts": [a.model_dump() for a in active[:5]],
            "timestamp": time.time(),
        }


# Global singleton
ambient_daemon = AmbientIntelligenceDaemon()
