"""Automated Verification Suite for Autonomous Executive Briefing & Calendar/Gmail Triage.

Verifies:
1. Gmail Priority Triage & Draft-Only Creation into [Gmail]/Drafts (EXE-01).
2. Strict Rule 9 Enforcement: EmailSendingProhibitedError raised on send attempt (EXE-01).
3. Google Calendar 15-Minute Lookahead Scanner & Deduplication (EXE-02).
4. Executive Morning Briefing Synthesizer (EXE-03).
5. Safety Tool Registrations, Pydantic argument schemas, and Risk Tiers (SAF-01).
6. Synchronous Guardian Kill Switch Halt within < 25ms SLA (SAF-02).
"""

import asyncio
from datetime import datetime, timedelta, timezone
import time
from typing import Any, Dict, List, Optional, Set
import pytest

from services.backend.integrations.google_workspace import (
    GoogleWorkspaceClient,
    EmailSendingProhibitedError,
)
from services.backend.triage.gmail_triage import (
    GmailTriageService,
    EmailTriageItem,
)
from services.backend.triage.calendar_scanner import CalendarLookaheadScanner
from services.backend.triage.executive_briefing import (
    ExecutiveBriefingSynthesizer,
    ExecutiveBriefing,
)
from services.backend.proactive.dispatcher import (
    ProactiveEventDispatcher,
    ProactivePriority,
)
from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.main import on_guardian_state_change
import services.backend.tools.triage_tools  # Ensure triage tools are registered


class MockWorkspaceClient(GoogleWorkspaceClient):
    """Mock Google Workspace client for offline deterministic unit testing."""

    def __init__(self):
        super().__init__()
        self.mock_emails = [
            {
                "id": "msg-101",
                "from": "supervisor@example.com",
                "subject": "URGENT: Review Q4 Swarm Deployment by EOD",
                "snippet": "Can you please review the attached architecture report and send feedback?",
                "date": "Tue, 3 Nov 2026 09:00:00 +0000",
            },
            {
                "id": "msg-102",
                "from": "newsletter@techdaily.com",
                "subject": "Weekly Tech Digest",
                "snippet": "Here are the top stories in artificial intelligence this week.",
                "date": "Tue, 3 Nov 2026 08:30:00 +0000",
            },
        ]
        now = datetime.now(timezone.utc)
        self.mock_events = [
            {
                "id": "evt-001",
                "summary": "Swarm Architecture Sync",
                "description": "Weekly technical roadmap sync",
                "start": {"dateTime": (now + timedelta(minutes=10)).isoformat()},
                "end": {"dateTime": (now + timedelta(minutes=40)).isoformat()},
                "attendees": [{"email": "alice@example.com", "displayName": "Alice Smith"}],
                "hangoutLink": "https://meet.google.com/xyz-phenom",
            },
            {
                "id": "evt-002",
                "summary": "Afternoon Deep Focus",
                "description": "Solo coding session",
                "start": {"dateTime": (now + timedelta(minutes=120)).isoformat()},
                "end": {"dateTime": (now + timedelta(minutes=240)).isoformat()},
                "attendees": [],
            },
        ]
        self.drafts_saved: List[Dict[str, Any]] = []

    def search_emails(self, query: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
        return self.mock_emails[:max_results]

    def save_draft(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        draft_record = {"to": to, "subject": subject, "body": body, "timestamp": time.time()}
        self.drafts_saved.append(draft_record)
        return {"status": "ok", "draft_id": f"draft-{len(self.drafts_saved)}"}

    def get_calendar_events(self, time_min: Optional[str] = None, time_max: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.mock_events


# ---------------------------------------------------------------------------
# Test 1: Gmail Triage & Draft Creation (EXE-01)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gmail_triage_priority_scoring_and_draft_creation():
    """Verify unread emails are scored, urgent emails drafted into Drafts, and Rule 9 enforced."""
    mock_client = MockWorkspaceClient()
    dispatched_cards = []

    async def mock_broadcast(msg: Dict[str, Any]):
        dispatched_cards.append(msg)

    dispatcher = ProactiveEventDispatcher(ws_broadcast_fn=mock_broadcast, default_cooldown_seconds=1.0)
    triage_service = GmailTriageService(workspace_client=mock_client, dispatcher=dispatcher)

    # 1. Verify urgency scoring
    assert triage_service.score_urgency("URGENT: Server Down", "Check now", "ops@ex.com") == 3
    assert triage_service.score_urgency("Weekly Newsletter", "Unsubscribe here", "news@ex.com") == 1
    assert triage_service.score_urgency("Quick Question?", "Could you please verify this?", "bob@ex.com") == 2

    # 2. Run triage
    items = await triage_service.triage_unread_emails(max_results=5, auto_draft=True)
    assert len(items) == 2
    assert items[0].id == "msg-101"
    assert items[0].priority_score == 3
    assert items[0].draft_saved is True
    assert len(mock_client.drafts_saved) == 1
    assert "supervisor@example.com" in mock_client.drafts_saved[0]["to"]
    assert "Re: URGENT: Review Q4 Swarm Deployment by EOD" in mock_client.drafts_saved[0]["subject"]

    # 3. Verify Rule 9: send_email is strictly prohibited
    with pytest.raises(EmailSendingProhibitedError) as exc_info:
        mock_client.send_email("test@example.com", "Test", "Hello")
    assert "strictly blocked by Phenom permanent safety rules" in str(exc_info.value)

    # 4. Verify proactive card was emitted
    assert len(dispatched_cards) >= 1
    card_msg = [m for m in dispatched_cards if m["type"] == "PROACTIVE_CARD"][0]
    assert "Priority Email" in card_msg["card"]["title"]
    assert card_msg["card"]["action_chip"] == "Review in Gmail"


# ---------------------------------------------------------------------------
# Test 2: Calendar Lookahead Scanner (EXE-02)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_calendar_lookahead_scanner_15min_alert_and_deduplication():
    """Verify events starting in <= 15 minutes trigger urgent proactive alert, and deduplicate."""
    mock_client = MockWorkspaceClient()
    dispatched_cards = []

    async def mock_broadcast(msg: Dict[str, Any]):
        dispatched_cards.append(msg)

    dispatcher = ProactiveEventDispatcher(ws_broadcast_fn=mock_broadcast, default_cooldown_seconds=1.0)
    scanner = CalendarLookaheadScanner(
        workspace_client=mock_client,
        dispatcher=dispatcher,
        lookahead_minutes=30,
        alert_horizon_minutes=15,
    )

    # Scan upcoming events (evt-001 starts in 10 mins <= 15 min; evt-002 starts in 120 mins)
    alerts = await scanner.scan_upcoming()
    assert len(alerts) == 1
    assert alerts[0]["event_id"] == "evt-001"
    assert alerts[0]["summary"] == "Swarm Architecture Sync"
    assert alerts[0]["minutes_to_start"] <= 15
    assert "Alice Smith" in alerts[0]["attendees"]
    assert "https://meet.google.com/xyz-phenom" in alerts[0]["conference_link"]

    # Verify URGENT proactive card was emitted
    urgent_cards = [m for m in dispatched_cards if m["type"] == "PROACTIVE_CARD"]
    assert len(urgent_cards) == 1
    assert urgent_cards[0]["card"]["priority"] == int(ProactivePriority.URGENT)
    assert "Meeting in" in urgent_cards[0]["card"]["title"]

    # Deduplication test: scanning again must NOT alert for evt-001 again
    dispatched_cards.clear()
    alerts_second_pass = await scanner.scan_upcoming()
    assert len(alerts_second_pass) == 0
    assert len(dispatched_cards) == 0


# ---------------------------------------------------------------------------
# Test 3: Executive Morning Briefing Synthesizer (EXE-03)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_executive_morning_briefing_synthesis():
    """Verify executive briefing combines calendar, email triage, and markdown presentation."""
    mock_client = MockWorkspaceClient()
    dispatched_cards = []

    async def mock_broadcast(msg: Dict[str, Any]):
        dispatched_cards.append(msg)

    dispatcher = ProactiveEventDispatcher(ws_broadcast_fn=mock_broadcast, default_cooldown_seconds=1.0)
    triage_service = GmailTriageService(workspace_client=mock_client, dispatcher=dispatcher)
    synthesizer = ExecutiveBriefingSynthesizer(
        workspace_client=mock_client,
        triage_service=triage_service,
        dispatcher=dispatcher,
        vault_path="vault",
    )

    briefing = await synthesizer.generate_briefing(broadcast_card=True)
    assert isinstance(briefing, ExecutiveBriefing)
    assert "Executive Briefing" in briefing.markdown_content
    assert "sir." in briefing.greeting.lower()
    assert briefing.event_count >= 1
    assert len(briefing.events) >= 1
    assert briefing.events[0]["summary"] == "Swarm Architecture Sync"

    # Verify proactive card broadcast
    cards = [m for m in dispatched_cards if m["type"] == "PROACTIVE_CARD"]
    assert len(cards) >= 1
    morning_cards = [c for c in cards if c["card"]["event_type"] == "MORNING_BRIEF"]
    assert len(morning_cards) >= 1
    assert morning_cards[0]["card"]["action_chip"] == "View Full Briefing"


# ---------------------------------------------------------------------------
# Test 4: Safety Tools Registration & Execution (SAF-01)
# ---------------------------------------------------------------------------
def test_triage_safety_tools_registration_and_execution():
    """Verify Safety layer ToolRegistry registration and execution schemas."""
    # 1. get_executive_briefing (Tier 0)
    brief_entry = registry.get("get_executive_briefing")
    assert brief_entry is not None
    assert brief_entry.tier == 0
    res_brief = brief_entry.handler_fn()
    assert res_brief["status"] == "ok"
    assert "briefing" in res_brief

    # 2. scan_calendar_upcoming (Tier 0)
    cal_entry = registry.get("scan_calendar_upcoming")
    assert cal_entry is not None
    assert cal_entry.tier == 0
    res_cal = cal_entry.handler_fn(lookahead_minutes=45)
    assert res_cal["status"] == "ok"

    # 3. triage_unread_emails (Tier 0)
    email_entry = registry.get("triage_unread_emails")
    assert email_entry is not None
    assert email_entry.tier == 0
    res_email = email_entry.handler_fn(max_results=5)
    assert res_email["status"] == "ok"

    # 4. draft_email_reply (Tier 1)
    draft_entry = registry.get("draft_email_reply")
    assert draft_entry is not None
    assert draft_entry.tier == 1
    preview = draft_entry.preview_fn({"to_address": "client@example.com", "subject": "Project Proposal"})
    assert "To='client@example.com'" in preview
    res_draft = draft_entry.handler_fn(
        to_address="client@example.com",
        subject="Project Proposal",
        body="Here is the proposal text.",
    )
    assert res_draft["status"] == "draft_created"
    assert res_draft["folder"] == "[Gmail]/Drafts"

    # 5. schedule_meeting_event (Tier 1)
    sched_entry = registry.get("schedule_meeting_event")
    assert sched_entry is not None
    assert sched_entry.tier == 1
    preview_cal = sched_entry.preview_fn({"summary": "Q4 Review", "start_time_iso": "2026-11-03T15:00:00Z"})
    assert "Q4 Review" in preview_cal


# ---------------------------------------------------------------------------
# Test 5: Synchronous Guardian Kill Switch Halt (< 25ms SLA) (SAF-02)
# ---------------------------------------------------------------------------
def test_guardian_synchronously_halts_triage_services():
    """Verify Guardian trigger synchronously halts calendar scanner and email triage in < 25ms."""
    from services.backend.triage.calendar_scanner import calendar_scanner
    from services.backend.triage.gmail_triage import gmail_triage

    guardian.resume()
    calendar_scanner.start()
    gmail_triage.start()

    t_start = time.perf_counter()
    guardian.trigger("test_triage_guardian_halt")
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    # Assert synchronous sub-25ms SLA
    assert elapsed_ms < 25.0, f"Guardian trigger took {elapsed_ms:.2f}ms, exceeded 25.0ms SLA"

    # Verify scanners halted
    assert calendar_scanner._running is False
    assert gmail_triage._running is False

    guardian.resume()
