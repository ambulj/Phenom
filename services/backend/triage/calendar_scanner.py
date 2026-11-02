"""Google Calendar 15-Minute Lookahead Scanner for Phenom.

Monitors Google Calendar REST API for meetings starting in the next 15-30 minutes,
deduplicates notifications, and dispatches pre-meeting briefing cards (EXE-02).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional, Set

from services.backend.integrations.google_workspace import (
    GoogleWorkspaceClient,
    google_workspace,
)
from services.backend.proactive.dispatcher import (
    ProactiveEventDispatcher,
    ProactiveCard,
    ProactivePriority,
    proactive_dispatcher,
)
from services.backend.safety.guardian import guardian

logger = logging.getLogger(__name__)


class CalendarLookaheadScanner:
    """Scans upcoming Google Calendar events and surfaces 15-minute meeting alerts."""

    def __init__(
        self,
        workspace_client: Optional[GoogleWorkspaceClient] = None,
        dispatcher: Optional[ProactiveEventDispatcher] = None,
        poll_interval: float = 180.0,  # Poll every 3 minutes
        lookahead_minutes: int = 30,
        alert_horizon_minutes: int = 15,
    ) -> None:
        self.workspace_client = workspace_client or google_workspace
        self.dispatcher = dispatcher or proactive_dispatcher
        self.poll_interval = poll_interval
        self.lookahead_minutes = lookahead_minutes
        self.alert_horizon_minutes = alert_horizon_minutes
        self._halted: bool = False

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._notified_event_ids: Set[str] = set()

    @property
    def is_halted(self) -> bool:
        """Returns True if halted by Guardian or manually."""
        return self._halted or guardian.is_halted

    def reset(self) -> None:
        """Reset halted state."""
        self._halted = False

    def parse_start_time(self, event: Dict[str, Any]) -> Optional[datetime]:
        """Extract and parse start datetime in UTC."""
        start = event.get("start", {})
        dt_str = start.get("dateTime") or start.get("date")
        if not dt_str:
            return None

        try:
            # Handle standard ISO8601 strings
            clean_str = dt_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception as exc:
            logger.debug("Could not parse event start time '%s': %s", dt_str, exc)
            return None

    async def scan_upcoming(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Query calendar events starting within lookahead window and alert on imminent ones."""
        if self.is_halted:
            raise PermissionError("Calendar scanning blocked: Guardian kill switch is active.")

        now_utc = datetime.now(timezone.utc)
        max_utc = now_utc + timedelta(minutes=self.lookahead_minutes)

        events = await asyncio.to_thread(
            self.workspace_client.get_calendar_events,
            time_min=now_utc.isoformat(),
            time_max=max_utc.isoformat(),
        )

        upcoming_alerts: List[Dict[str, Any]] = []

        for ev in events:
            ev_id = str(ev.get("id") or "")
            summary = ev.get("summary") or "Untitled Meeting"
            description = ev.get("description") or ""
            conference_link = ev.get("hangoutLink") or ev.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri") or ""

            # Extract attendees
            attendees_list = ev.get("attendees", [])
            attendee_names = [a.get("displayName") or a.get("email") for a in attendees_list if isinstance(a, dict)]
            attendee_names = [name for name in attendee_names if name]
            attendees_summary = ", ".join(attendee_names[:4]) if attendee_names else "Solo / No Attendees"
            if len(attendee_names) > 4:
                attendees_summary += f" +{len(attendee_names) - 4} more"

            start_dt = self.parse_start_time(ev)
            if not start_dt:
                continue

            # Calculate minutes remaining
            delta_seconds = (start_dt - now_utc).total_seconds()
            minutes_to_start = max(0, int(delta_seconds / 60.0))

            # Check if event starts within alert horizon (default <= 15 minutes)
            if delta_seconds <= (self.alert_horizon_minutes * 60):
                if ev_id not in self._notified_event_ids or force_refresh:
                    self._notified_event_ids.add(ev_id)
                    alert_payload = {
                        "event_id": ev_id,
                        "summary": summary,
                        "minutes_to_start": minutes_to_start,
                        "start_iso": start_dt.isoformat(),
                        "attendees": attendees_summary,
                        "conference_link": conference_link,
                        "description": description[:200],
                    }
                    upcoming_alerts.append(alert_payload)

                    # Dispatch URGENT proactive card
                    card = ProactiveCard(
                        event_type="MEETING_PREP",
                        priority=ProactivePriority.URGENT,
                        title=f"Meeting in {minutes_to_start} min: {summary[:40]}",
                        description=f"Attendees: {attendees_summary}. {('Link: ' + conference_link) if conference_link else ''}",
                        action_chip="Open Briefing",
                        action_payload=alert_payload,
                    )
                    await self.dispatcher.dispatch(card)
                    logger.info("Dispatched pre-meeting alert for '%s' (starts in %d min)", summary, minutes_to_start)

        return upcoming_alerts

    async def _run_loop(self) -> None:
        """Background calendar lookahead scanning loop."""
        logger.info("CalendarLookaheadScanner background loop started (interval=%.1fs)", self.poll_interval)
        while self._running:
            try:
                await self.scan_upcoming()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("CalendarLookaheadScanner loop exception: %s", exc)
                await asyncio.sleep(self.poll_interval)

    def start(self) -> None:
        """Start background calendar lookahead scanner."""
        if self._running:
            return
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._run_loop())
        except RuntimeError:
            logger.debug("No running event loop; calendar scanner will start when loop runs.")

    def stop(self) -> None:
        """Gracefully stop calendar scanning."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

    def halt(self) -> None:
        """Synchronous Guardian halt callback (< 5ms SLA)."""
        self._halted = True
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

    # Alias for lookahead scan
    scan_lookahead = scan_upcoming


calendar_scanner = CalendarLookaheadScanner()
