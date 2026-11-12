"""
Phenom Proactive Ambient Event Monitor
Background evaluator monitoring hardware resource spikes, calendar conflicts, and background task
completions, dispatching typed ambient alerts to the Cyber HUD with mode-aware notification policies.
"""

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Callable, Awaitable
from pydantic import BaseModel, Field
import psutil

from services.backend.modes.mode_manager import mode_manager
from services.backend.voice.sound_fx import sound_fx
from services.backend.safety.action_log import action_log

logger = logging.getLogger("phenom.ambient_monitor")


class AmbientAlert(BaseModel):
    id: str = Field(default_factory=lambda: f"alert-{uuid.uuid4().hex[:8]}")
    title: str
    message: str
    category: str = "general"  # calendar | system | task | general
    urgency: str = "medium"    # low | medium | high | critical
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    auto_dismiss_seconds: int = 6
    sound: str = "chime"       # chime | subtle | none


class AmbientEventMonitor:
    """
    Evaluates system resources, calendar meetings, and task status to emit unprompted alerts.
    """

    def __init__(self, cooldown_seconds: float = 300.0):
        self.cooldown_seconds = cooldown_seconds
        self._last_alert_times: Dict[str, float] = {}
        self._alerted_calendar_events: Set[str] = set()
        self._broadcaster: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
        self.is_running: bool = False

    def set_broadcaster(self, broadcaster: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Sets the WebSocket broadcaster for Cyber HUD toast events."""
        self._broadcaster = broadcaster

    def _is_in_cooldown(self, key: str, now: float) -> bool:
        last = self._last_alert_times.get(key, 0.0)
        return (now - last) < self.cooldown_seconds

    def evaluate_hardware(
        self,
        cpu_percent: Optional[float] = None,
        ram_percent: Optional[float] = None,
        vram_percent: Optional[float] = None,
        now_ts: Optional[float] = None
    ) -> List[AmbientAlert]:
        """
        Evaluates CPU, RAM, and GPU VRAM metrics against alert thresholds.
        """
        now = now_ts if now_ts is not None else time.time()
        alerts: List[AmbientAlert] = []

        # 1. CPU Check (> 90%)
        cpu = cpu_percent if cpu_percent is not None else psutil.cpu_percent(interval=None)
        if cpu >= 90.0 and not self._is_in_cooldown("cpu_spike", now):
            self._last_alert_times["cpu_spike"] = now
            alerts.append(AmbientAlert(
                title="High CPU Utilization",
                message=f"CPU load reached {cpu:.1f}%. Background tasks may experience throttling.",
                category="system",
                urgency="high",
                sound="subtle"
            ))

        # 2. RAM Check (> 85%)
        ram = ram_percent if ram_percent is not None else psutil.virtual_memory().percent
        if ram >= 85.0 and not self._is_in_cooldown("ram_spike", now):
            self._last_alert_times["ram_spike"] = now
            alerts.append(AmbientAlert(
                title="System Memory Pressure",
                message=f"System RAM usage at {ram:.1f}%. Consider closing inactive browser tabs.",
                category="system",
                urgency="high",
                sound="subtle"
            ))

        # 3. GPU VRAM Check (> 90%)
        vram = vram_percent
        if vram is None:
            try:
                import torch
                if torch.cuda.is_available():
                    allocated = torch.cuda.memory_allocated()
                    total = torch.cuda.get_device_properties(0).total_memory
                    vram = (allocated / total) * 100.0
            except Exception:
                pass

        if vram is not None and vram >= 90.0 and not self._is_in_cooldown("vram_spike", now):
            self._last_alert_times["vram_spike"] = now
            alerts.append(AmbientAlert(
                title="GPU VRAM Saturation",
                message=f"GPU VRAM usage at {vram:.1f}%. Local model inference may degrade.",
                category="system",
                urgency="critical",
                sound="subtle"
            ))

        return alerts

    def evaluate_calendar(
        self,
        events: Optional[List[Dict[str, Any]]] = None,
        now_dt: Optional[datetime] = None
    ) -> List[AmbientAlert]:
        """
        Checks upcoming Google Calendar events within the next 15 minutes.
        """
        now = now_dt if now_dt is not None else datetime.now(timezone.utc)
        alerts: List[AmbientAlert] = []

        calendar_events = events
        if calendar_events is None:
            try:
                from services.backend.integrations.google_workspace import google_workspace
                calendar_events = google_workspace.list_calendar_events(time_window_hours=1)
            except Exception:
                calendar_events = []

        for ev in calendar_events:
            ev_id = ev.get("id") or ev.get("summary", "")
            if not ev_id or ev_id in self._alerted_calendar_events:
                continue

            start_str = ev.get("start")
            if not start_str:
                continue

            try:
                # Handle ISO timestamps
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                diff_seconds = (start_dt - now).total_seconds()
                diff_minutes = int(diff_seconds / 60)

                # Alert if event begins between 1 and 15 minutes from now
                if 0 <= diff_minutes <= 15:
                    self._alerted_calendar_events.add(ev_id)
                    alerts.append(AmbientAlert(
                        title="Upcoming Meeting",
                        message=f"'{ev.get('summary', 'Meeting')}' starts in {diff_minutes} minute(s).",
                        category="calendar",
                        urgency="medium",
                        sound="chime"
                    ))
            except Exception:
                continue

        return alerts

    async def evaluate_and_broadcast(
        self,
        mock_hardware: Optional[Dict[str, float]] = None,
        mock_calendar: Optional[List[Dict[str, Any]]] = None
    ) -> List[AmbientAlert]:
        """
        Runs hardware and calendar evaluations, filters by active mode policy,
        and broadcasts alerts to Cyber HUD.
        """
        alerts: List[AmbientAlert] = []

        # Evaluate hardware
        if mock_hardware:
            alerts.extend(self.evaluate_hardware(
                cpu_percent=mock_hardware.get("cpu"),
                ram_percent=mock_hardware.get("ram"),
                vram_percent=mock_hardware.get("vram")
            ))
        else:
            alerts.extend(self.evaluate_hardware())

        # Evaluate calendar
        alerts.extend(self.evaluate_calendar(events=mock_calendar))

        filtered_alerts: List[AmbientAlert] = []
        for alert in alerts:
            # Check if active mode policy permits this urgency
            if not mode_manager.is_notification_allowed(alert.urgency):
                logger.debug(f"[AmbientMonitor] Suppressed {alert.category} alert '{alert.title}' under active mode.")
                continue

            filtered_alerts.append(alert)

            # Play procedural chime if sound requested and not muted
            if alert.sound == "chime":
                sound_fx.play_ambient_toast_chime()
            elif alert.sound == "subtle":
                sound_fx.play_subtle_alert_chime()

            # Broadcast over WebSocket to Cyber HUD
            if self._broadcaster:
                try:
                    await self._broadcaster({
                        "id": alert.id,
                        "type": "ambient.alert",
                        "ts": alert.timestamp,
                        "payload": alert.model_dump()
                    })
                except Exception as e:
                    logger.error(f"[AmbientMonitor] Failed to broadcast alert: {e}")

            # Log to action_log
            action_log.log_action(
                tool="ambient_alert",
                tier=0,
                args={"title": alert.title, "category": alert.category, "urgency": alert.urgency},
                decision="auto",
                result_status="SUCCESS",
                source="ambient_monitor"
            )

        return filtered_alerts


# Global ambient event monitor instance
ambient_monitor = AmbientEventMonitor()
