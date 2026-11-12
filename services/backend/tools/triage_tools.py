"""Phenom Autonomous Triage & Executive Briefing Tools.

Provides tool endpoints for generating executive briefings, scanning upcoming calendar events,
triaging unread emails, and saving drafts into [Gmail]/Drafts.
Strictly respects SAFETY.md:
- get_executive_briefing (Tier 0): Read-only executive operational briefing.
- scan_calendar_upcoming (Tier 0): Read-only calendar lookahead.
- triage_unread_emails (Tier 0): Read-only inbox triage analysis.
- draft_email_reply (Tier 1): Requires interactive preview confirmation.
- schedule_meeting_event (Tier 1): Requires interactive preview confirmation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.triage.executive_briefing import executive_briefing
from services.backend.triage.calendar_scanner import calendar_scanner
from services.backend.triage.gmail_triage import gmail_triage
from services.backend.integrations.google_workspace import google_workspace


class GetExecutiveBriefingArgs(BaseModel):
    """Schema for get_executive_briefing (no arguments required)."""
    pass


class ScanCalendarUpcomingArgs(BaseModel):
    lookahead_minutes: Optional[int] = Field(
        default=30,
        ge=5,
        le=1440,
        description="Horizon window in minutes to look ahead for calendar events (default: 30)",
    )


class TriageUnreadEmailsArgs(BaseModel):
    max_results: Optional[int] = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of unread emails to inspect (default: 10)",
    )


class DraftEmailReplyArgs(BaseModel):
    to_address: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Body of the draft reply")


class ScheduleMeetingEventArgs(BaseModel):
    summary: str = Field(..., description="Meeting title / summary")
    start_time_iso: str = Field(..., description="Start time in ISO8601 format (e.g. 2026-11-03T10:00:00Z)")
    end_time_iso: str = Field(..., description="End time in ISO8601 format (e.g. 2026-11-03T10:30:00Z)")
    description: Optional[str] = Field(default="", description="Optional meeting description or agenda")


@registry.register(
    name="get_executive_briefing",
    tier=0,
    description="Compiles today's operational briefing including calendar timeline, unread priority emails, and Obsidian goals. Read-only.",
    args_schema=GetExecutiveBriefingArgs,
    preview_fn=lambda a: "Generate today's executive operational briefing (Read-only)",
)
def get_executive_briefing(**kwargs) -> Dict[str, Any]:
    # Synchronous query of existing or immediate briefing
    cached = executive_briefing.get_latest_briefing()
    if cached:
        return {"status": "ok", "briefing": cached.model_dump()}
    # Return formatted placeholder until async loop generates first briefing
    return {
        "status": "ok",
        "briefing": {
            "greeting": "Good day, sir.",
            "markdown_content": "Executive briefing synthesizer is initialized and monitoring background feeds.",
            "events": [],
            "daily_goals": executive_briefing.read_obsidian_daily_goals(),
        },
    }


@registry.register(
    name="scan_calendar_upcoming",
    tier=0,
    description="Scans upcoming Google Calendar events within the specified lookahead horizon. Read-only.",
    args_schema=ScanCalendarUpcomingArgs,
    preview_fn=lambda a: f"Scan upcoming calendar events within next {a.get('lookahead_minutes', 30)} minutes (Read-only)",
)
def scan_calendar_upcoming(lookahead_minutes: int = 30, **kwargs) -> Dict[str, Any]:
    events = google_workspace.get_calendar_events()
    return {
        "status": "ok",
        "lookahead_minutes": lookahead_minutes,
        "event_count": len(events),
        "events": events[:10],
    }


@registry.register(
    name="triage_unread_emails",
    tier=0,
    description="Scans unread emails via SSL IMAP and evaluates priority scores without sending. Read-only.",
    args_schema=TriageUnreadEmailsArgs,
    preview_fn=lambda a: f"Triage unread emails (max: {a.get('max_results', 10)}) (Read-only)",
)
def triage_unread_emails(max_results: int = 10, **kwargs) -> Dict[str, Any]:
    raw_emails = google_workspace.search_emails(query="is:unread", max_results=max_results)
    triaged = []
    for msg in raw_emails:
        subject = msg.get("subject", "")
        sender = msg.get("from", "")
        snippet = msg.get("snippet", "")
        score = gmail_triage.score_urgency(subject, snippet, sender)
        triaged.append({
            "id": msg.get("id"),
            "sender": sender,
            "subject": subject,
            "priority_score": score,
            "snippet": snippet[:100],
        })

    return {
        "status": "ok",
        "unread_count": len(triaged),
        "items": triaged,
    }


@registry.register(
    name="draft_email_reply",
    tier=1,
    description="Saves a proposed email draft directly into [Gmail]/Drafts for user review. Never sends outbound mail. Requires confirmation.",
    args_schema=DraftEmailReplyArgs,
    preview_fn=lambda a: f"Save email draft in Gmail: To='{a.get('to_address')}', Subject='{a.get('subject')}'",
)
def draft_email_reply(to_address: str, subject: str, body: str, **kwargs) -> Dict[str, Any]:
    # Strictly creates draft via IMAP APPEND (Rule 9)
    result = google_workspace.save_draft(to=to_address, subject=subject, body=body)
    return {
        "status": "draft_created",
        "folder": "[Gmail]/Drafts",
        "to": to_address,
        "subject": subject,
        "result": result,
    }


@registry.register(
    name="schedule_meeting_event",
    tier=1,
    description="Creates a new event on Google Calendar. Never edits or deletes existing events. Requires confirmation.",
    args_schema=ScheduleMeetingEventArgs,
    preview_fn=lambda a: f"Create Google Calendar event: '{a.get('summary')}' starting at {a.get('start_time_iso')}",
)
def schedule_meeting_event(summary: str, start_time_iso: str, end_time_iso: str, description: str = "", **kwargs) -> Dict[str, Any]:
    res = google_workspace.create_calendar_event(
        summary=summary,
        start_time=start_time_iso,
        end_time=end_time_iso,
        description=description,
    )
    return {
        "status": "event_created",
        "summary": summary,
        "start": start_time_iso,
        "end": end_time_iso,
        "result": res,
    }
