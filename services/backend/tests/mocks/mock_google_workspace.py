"""
Mock Google Workspace Client for Unit & Integration Tests
Provides isolated, deterministic test fixtures for testing without touching real Gmail IMAP or Google Calendar APIs.
Production code in services/backend/integrations/google_workspace.py strictly contains ZERO fabricated data.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from services.backend.integrations.google_workspace import (
    GoogleWorkspaceClient, EmailSendingProhibitedError, CalendarModificationProhibitedError
)

class MockGoogleWorkspaceClient(GoogleWorkspaceClient):
    def __init__(self):
        super().__init__()
        self._mock_emails: List[Dict[str, Any]] = [
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
        self._mock_events: List[Dict[str, Any]] = [
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

    def is_gmail_configured(self) -> bool:
        return True

    def is_calendar_configured(self) -> bool:
        return True

    def is_authenticated(self) -> bool:
        return True

    def search_emails(self, query: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
        q = query.lower().strip()
        if not q or q == "unseen":
            return self._mock_emails[:max_results]
        matches = [
            e for e in self._mock_emails
            if q in e["subject"].lower() or q in e["snippet"].lower() or q in e["from"].lower()
        ]
        return matches[:max_results]

    def read_email(self, email_id: str) -> Optional[Dict[str, Any]]:
        for e in self._mock_emails:
            if e["id"] == email_id:
                return e
        return None

    def create_draft(self, to: str, subject: str, body: str) -> Dict[str, Any]:
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

    def list_events(self, max_results: int = 10) -> List[Dict[str, Any]]:
        return self._mock_events[:max_results]

    def create_event(self, summary: str, start_time: str, end_time: str, description: str = "") -> Dict[str, Any]:
        event_id = f"event_{len(self._mock_events) + 1:03d}"
        event = {
            "id": event_id,
            "summary": summary,
            "start": start_time,
            "end": end_time,
            "description": description,
            "creator": "phenom_assistant",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._mock_events.append(event)
        return event
