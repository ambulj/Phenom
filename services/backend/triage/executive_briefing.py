"""Executive Morning Briefing Synthesizer for Phenom.

Synthesizes daily schedule, unread priority emails, pending drafts,
and Obsidian daily note goals into an executive briefing card (EXE-03).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
import os
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from services.backend.integrations.google_workspace import (
    GoogleWorkspaceClient,
    google_workspace,
)
from services.backend.triage.gmail_triage import (
    GmailTriageService,
    gmail_triage,
)
from services.backend.proactive.dispatcher import (
    ProactiveEventDispatcher,
    ProactiveCard,
    ProactivePriority,
    proactive_dispatcher,
)

logger = logging.getLogger(__name__)


class ExecutiveBriefing(BaseModel):
    """Structured data model of an executive daily briefing."""

    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    date_formatted: str = Field(default="")
    greeting: str = Field(default="")
    event_count: int = Field(default=0)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    unread_email_count: int = Field(default=0)
    priority_emails: List[Dict[str, Any]] = Field(default_factory=list)
    drafts_pending: int = Field(default=0)
    daily_goals: List[str] = Field(default_factory=list)
    markdown_content: str = Field(default="")


class ExecutiveBriefingSynthesizer:
    """Compiles daily operational briefings for the desktop user."""

    def __init__(
        self,
        workspace_client: Optional[GoogleWorkspaceClient] = None,
        triage_service: Optional[GmailTriageService] = None,
        dispatcher: Optional[ProactiveEventDispatcher] = None,
        vault_path: str = "vault",
    ) -> None:
        self.workspace_client = workspace_client or google_workspace
        self.triage_service = triage_service or gmail_triage
        self.dispatcher = dispatcher or proactive_dispatcher
        self.vault_path = vault_path

        self._latest_briefing: Optional[ExecutiveBriefing] = None

    def read_obsidian_daily_goals(self) -> List[str]:
        """Read unchecked tasks from today's Obsidian daily note if present."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        daily_note_candidates = [
            os.path.join(self.vault_path, f"{today_str}.md"),
            os.path.join(self.vault_path, "Daily Notes", f"{today_str}.md"),
            os.path.join(self.vault_path, "daily", f"{today_str}.md"),
        ]

        goals: List[str] = []
        for path in daily_note_candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    for line in lines:
                        clean = line.strip()
                        # Match uncompleted markdown tasks: - [ ] Task description
                        if re.match(r"^[-*]\s*\[\s*\]\s+", clean):
                            task_text = re.sub(r"^[-*]\s*\[\s*\]\s+", "", clean)
                            goals.append(task_text)
                    if goals:
                        break
                except Exception as exc:
                    logger.debug("Could not read daily note at %s: %s", path, exc)

        return goals[:5]  # Top 5 goals

    async def generate_briefing(self, broadcast_card: bool = True) -> ExecutiveBriefing:
        """Compile complete executive briefing and optionally dispatch proactive card."""
        now_dt = datetime.now()
        date_formatted = now_dt.strftime("%A, %B %d, %Y")

        # 1. Fetch today's calendar schedule
        now_utc = datetime.now(timezone.utc)
        end_of_day_utc = now_utc + timedelta(hours=24)

        events_raw = await asyncio.to_thread(
            self.workspace_client.get_calendar_events,
            time_min=now_utc.isoformat(),
            time_max=end_of_day_utc.isoformat(),
        )

        formatted_events: List[Dict[str, Any]] = []
        for ev in events_raw:
            start_str = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date") or ""
            summary = ev.get("summary") or "Untitled Meeting"
            link = ev.get("hangoutLink") or ""
            time_label = "All Day"
            if "T" in start_str:
                try:
                    ev_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    time_label = ev_dt.strftime("%I:%M %p")
                except Exception:
                    pass
            formatted_events.append({
                "summary": summary,
                "time": time_label,
                "link": link,
            })

        # 2. Fetch unread priority emails
        triaged_items = await self.triage_service.triage_unread_emails(max_results=10, auto_draft=False)
        priority_emails = [
            {"subject": item.subject, "sender": item.sender, "priority": item.priority_score}
            for item in triaged_items
            if item.priority_score >= 2
        ]

        # 3. Read Obsidian daily goals
        daily_goals = self.read_obsidian_daily_goals()

        # 4. Synthesize Jarvis Markdown Presentation
        hour = now_dt.hour
        greeting_time = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
        greeting = f"{greeting_time}, sir. Here is your executive operational briefing."

        lines: List[str] = [
            f"### Executive Briefing — {date_formatted}",
            f"{greeting}\n",
        ]

        if formatted_events:
            lines.append(f"📅 **Upcoming Agenda ({len(formatted_events)} events):**")
            for ev in formatted_events[:5]:
                link_text = f" ([Join Meeting]({ev['link']}))" if ev["link"] else ""
                lines.append(f"- **{ev['time']}** — {ev['summary']}{link_text}")
            lines.append("")
        else:
            lines.append("📅 **Schedule:** Your calendar is clear for the next 24 hours.\n")

        if priority_emails:
            lines.append(f"📬 **Inbox Triage ({len(priority_emails)} priority threads):**")
            for mail in priority_emails[:3]:
                lines.append(f"- From **{mail['sender'][:30]}**: {mail['subject'][:45]}")
            lines.append("")
        else:
            lines.append("📬 **Inbox Triage:** No urgent unread messages requiring immediate action.\n")

        if daily_goals:
            lines.append(f"🎯 **Obsidian Daily Directives ({len(daily_goals)} pending):**")
            for goal in daily_goals:
                lines.append(f"- [ ] {goal}")
            lines.append("")

        markdown_content = "\n".join(lines)

        briefing = ExecutiveBriefing(
            date_formatted=date_formatted,
            greeting=greeting,
            event_count=len(formatted_events),
            events=formatted_events,
            unread_email_count=len(triaged_items),
            priority_emails=priority_emails,
            drafts_pending=len(priority_emails),
            daily_goals=daily_goals,
            markdown_content=markdown_content,
        )
        self._latest_briefing = briefing

        if broadcast_card:
            card = ProactiveCard(
                event_type="MORNING_BRIEF",
                priority=ProactivePriority.NORMAL,
                title=f"Executive Briefing: {len(formatted_events)} Events, {len(priority_emails)} Priority Emails",
                description=markdown_content[:250] + ("..." if len(markdown_content) > 250 else ""),
                action_chip="View Full Briefing",
                action_payload={"briefing": briefing.model_dump()},
            )
            await self.dispatcher.dispatch(card)

        return briefing

    def get_latest_briefing(self) -> Optional[ExecutiveBriefing]:
        """Return the most recently generated executive briefing."""
        return self._latest_briefing


executive_briefing = ExecutiveBriefingSynthesizer()
