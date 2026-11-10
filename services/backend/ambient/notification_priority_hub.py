"""
Context-Aware Notification Priority Hub.
Evaluates user focus state, active applications, and alert urgency to filter and suppress
interruptions during deep work sessions.

Part of Phenom 22.0 Sovereign Swarm Intelligence (AMB-02.2).
"""

import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.ambient.ambient_intelligence_daemon import (
    ambient_daemon,
    AmbientAlertItem,
)


class NotificationPriorityHub:
    """
    Filters and regulates ambient alert delivery based on dynamic focus modes.
    """

    THRESHOLDS = {
        "deep_focus": 0.75,
        "balanced": 0.40,
        "ambient": 0.00,
    }

    def __init__(self):
        self._current_mode: str = "balanced"
        self._custom_threshold: Optional[float] = None
        self._suppressed_alerts: List[str] = []

    def get_effective_threshold(self) -> float:
        if self._custom_threshold is not None:
            return self._custom_threshold
        return self.THRESHOLDS.get(self._current_mode, 0.40)

    def set_mode(self, mode: str, custom_threshold: Optional[float] = None) -> Dict[str, Any]:
        """Sets active focus mode: deep_focus, balanced, ambient."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Priority hub configuration halted.")

        if mode not in self.THRESHOLDS and custom_threshold is None:
            raise ValueError(f"Invalid mode '{mode}'. Choose from: {list(self.THRESHOLDS.keys())}")

        self._current_mode = mode
        self._custom_threshold = custom_threshold

        return {
            "mode": self._current_mode,
            "threshold": self.get_effective_threshold(),
            "status": "updated",
        }

    def evaluate_delivery(self, alert: AmbientAlertItem) -> Dict[str, Any]:
        """
        Determines whether an alert should be surfaced immediately or suppressed into background buffer.
        """
        threshold = self.get_effective_threshold()
        should_deliver = alert.urgency >= threshold

        if not should_deliver:
            if alert.alert_id not in self._suppressed_alerts:
                self._suppressed_alerts.append(alert.alert_id)

        return {
            "alert_id": alert.alert_id,
            "title": alert.title,
            "urgency": alert.urgency,
            "threshold": threshold,
            "delivered": should_deliver,
            "focus_mode": self._current_mode,
        }

    def get_filtered_feed(self) -> Dict[str, Any]:
        """
        Returns delivered alerts matching the current focus threshold along with buffered count.
        """
        threshold = self.get_effective_threshold()
        active = ambient_daemon.get_active_alerts(min_urgency=0.0)

        delivered = [a for a in active if a.urgency >= threshold]
        suppressed = [a for a in active if a.urgency < threshold]

        return {
            "focus_mode": self._current_mode,
            "threshold": threshold,
            "delivered_alerts": [a.model_dump() for a in delivered],
            "suppressed_count": len(suppressed),
            "total_active": len(active),
        }


# Global singleton
priority_hub = NotificationPriorityHub()
