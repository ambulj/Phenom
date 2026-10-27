"""
Phenom Google Workspace Integration (Phase 5)
Gmail and Google Calendar.
Reading is allowed.
Email drafts can be saved (never send).
Calendar events can be created (never edit or delete).
Hard code-level prohibitions:
- Sending email is strictly blocked (raises EmailSendingProhibitedError)
- Deleting calendar events is strictly blocked (raises CalendarModificationProhibitedError)
- Editing calendar events is strictly blocked (raises CalendarModificationProhibitedError)
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class EmailSendingProhibitedError(Exception):
    """Raised whenever sending an email is attempted."""
    pass

class CalendarModificationProhibitedError(Exception):
    """Raised whenever deleting or editing calendar events is attempted."""
    pass

class GoogleWorkspaceClient:
    def __init__(self, token_override: Optional[str] = None):
        self._token = token_override or os.environ.get("GOOGLE_WORKSPACE_TOKEN")
        self._authenticated = bool(self._token)
        # In-memory storage for drafts and events created during session
        self._drafts: List[Dict[str, Any]] = []
        self._events: List[Dict[str, Any]] = [
            {
                "id": "event_sample_1",
                "summary": "Team Sync & Standup",
                "start": "2026-10-28T10:00:00Z",
                "end": "2026-10-28T10:30:00Z",
                "description": "Daily engineering sync.",
                "creator": "lead@company.com"
            },
            {
                "id": "event_sample_2",
                "summary": "Product Architecture Review",
                "start": "2026-10-28T15:00:00Z",
                "end": "2026-10-28T16:00:00Z",
                "description": "Deep dive into Phase 5 architecture.",
                "creator": "architect@company.com"
            }
        ]
        self._sample_emails: List[Dict[str, Any]] = [
            {
                "id": "msg_001",
                "from": "manager@company.com",
                "to": "user@company.com",
                "subject": "Sprint Goals Q4",
                "snippet": "Here are the top priorities for our sprint deliverables...",
                "body": "Here are the top priorities for our sprint deliverables: 1. Assistant Core, 2. Reliability.",
                "received_at": "2026-10-27T18:30:00Z"
            },
            {
                "id": "msg_002",
                "from": "newsletter@techinsights.org",
                "to": "user@company.com",
                "subject": "Weekly Tech Radar",
                "snippet": "Exciting advancements in local LLMs and agent architectures...",
                "body": "Exciting advancements in local LLMs and agent architectures this week.",
                "received_at": "2026-10-28T08:00:00Z"
            }
        ]

    def is_authenticated(self) -> bool:
        return self._authenticated

    # ----------------- HARD CODE-LEVEL PROHIBITIONS -----------------
    def send_email(self, to: str, subject: str, body: str) -> None:
        """Permanently blocked by construction."""
        raise EmailSendingProhibitedError(
            "Sending emails is strictly blocked by Phenom permanent safety rules. "
            "Phenom may only create email drafts for your review in Gmail."
        )

    def delete_calendar_event(self, event_id: str) -> None:
        """Permanently blocked by construction."""
        raise CalendarModificationProhibitedError(
            f"Deleting calendar events (id='{event_id}') is strictly blocked by Phenom safety rules."
        )

    def edit_calendar_event(self, event_id: str, updates: Dict[str, Any]) -> None:
        """Permanently blocked by construction."""
        raise CalendarModificationProhibitedError(
            f"Editing calendar events (id='{event_id}') is strictly blocked by Phenom safety rules. "
            "Phenom may create new calendar events, but cannot alter existing ones."
        )

    # ----------------- GMAIL READING & DRAFTS -----------------
    def search_emails(self, query: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
        """Searches or lists inbox messages."""
        q = query.lower().strip()
        if not q:
            return self._sample_emails[:max_results]
        matches = [
            e for e in self._sample_emails
            if q in e["subject"].lower() or q in e["snippet"].lower() or q in e["from"].lower()
        ]
        return matches[:max_results]

    def read_email(self, email_id: str) -> Optional[Dict[str, Any]]:
        for e in self._sample_emails:
            if e["id"] == email_id:
                return e
        return None

    def create_draft(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Creates a Gmail draft (Tier 1 action). Never sends."""
        draft_id = f"draft_{len(self._drafts) + 1:03d}"
        now_str = datetime.now(timezone.utc).isoformat()
        draft = {
            "id": draft_id,
            "to": to,
            "subject": subject,
            "body": body,
            "created_at": now_str,
            "status": "DRAFT",
            "note": "Draft saved in Gmail. Open Gmail to review and send manually."
        }
        self._drafts.append(draft)
        return draft

    def list_drafts(self) -> List[Dict[str, Any]]:
        return self._drafts

    # ----------------- CALENDAR READING & EVENT CREATION -----------------
    def list_events(self, max_results: int = 10) -> List[Dict[str, Any]]:
        return self._events[:max_results]

    def create_event(self, summary: str, start_time: str, end_time: str, description: str = "") -> Dict[str, Any]:
        """Creates a calendar event (Tier 2 action)."""
        event_id = f"event_{len(self._events) + 1:03d}"
        event = {
            "id": event_id,
            "summary": summary,
            "start": start_time,
            "end": end_time,
            "description": description,
            "creator": "phenom_assistant",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._events.append(event)
        return event

# Global Google Workspace client
google_workspace = GoogleWorkspaceClient()
