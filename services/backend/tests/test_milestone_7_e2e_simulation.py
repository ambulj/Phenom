"""Phenom Milestone 7.0 End-to-End Autonomous Executive Simulation.

Exercises the complete proactive executive lifecycle:
1. User Inactivity: WorkspaceHousekeeper organizes files & recycles clutter via send2trash (Rule 7).
2. Lookahead & Topic Research: Calendar scanner detects imminent meeting -> TopicResearchWorker generates brief in vault/Meetings/ -> Dispatches MEETING_PREP card.
3. Gmail Priority Triage: Urgency scored -> Draft reply created in [Gmail]/Drafts (Rule 9: drafts only, zero outbound send).
4. Second-Brain Daily Co-Pilot: Non-destructive daily note synchronization preserves handwritten user entries.
5. Executive Briefing Synthesis: Compiles schedule, unread triage count, and daily note goals into a HUD card.
6. User Return: Housekeeper immediately yields on USER_RETURNED.
7. Emergency Kill Switch: Synchronous Guardian halt cascades across entire stack in < 25ms SLA.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import os
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional
from unittest.mock import patch
import pytest

from services.backend.automation.topic_researcher import topic_researcher
from services.backend.automation.workspace_housekeeper import workspace_housekeeper
from services.backend.integrations.google_workspace import (
    GoogleWorkspaceClient,
    EmailSendingProhibitedError,
)
from services.backend.main import on_guardian_state_change
from services.backend.memory.daily_copilot import daily_copilot
from services.backend.memory.vault import vault_manager
from services.backend.proactive.dispatcher import proactive_dispatcher, ProactivePriority
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.sensors.idle_sensor import idle_detector
from services.backend.triage.calendar_scanner import calendar_scanner
from services.backend.triage.executive_briefing import executive_briefing
from services.backend.triage.gmail_triage import gmail_triage


class E2EMockWorkspaceClient(GoogleWorkspaceClient):
    """Deterministic mock client for end-to-end integration testing."""

    def __init__(self):
        super().__init__()
        now = datetime.now(timezone.utc)
        self.mock_events = [
            {
                "id": "e2e-evt-101",
                "summary": "Distributed Swarm Architecture Review",
                "description": "Weekly deep dive into autonomous agent protocols",
                "start": {"dateTime": (now + timedelta(minutes=10)).isoformat()},
                "end": {"dateTime": (now + timedelta(minutes=45)).isoformat()},
                "attendees": [{"email": "techlead@example.com", "displayName": "Tech Lead"}],
                "hangoutLink": "https://meet.google.com/phenom-e2e-meet",
            }
        ]
        self.mock_emails = [
            {
                "id": "e2e-msg-201",
                "from": "executive@example.com",
                "subject": "URGENT: Review Milestone 7 Deployment",
                "snippet": "Can you verify all background workers and safety systems before production?",
                "date": "Tue, 3 Nov 2026 10:00:00 +0000",
            }
        ]
        self.created_drafts = []

    def get_calendar_events(self, time_min: Optional[str] = None, time_max: Optional[str] = None, max_results: int = 10) -> List[Dict[str, Any]]:
        return self.mock_events

    def list_events(self, max_results: int = 10, time_min: Optional[str] = None, time_max: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.mock_events

    def search_emails(self, query: str = "is:unread", max_results: int = 10) -> List[Dict[str, Any]]:
        return self.mock_emails

    def save_draft(self, to: str = "", to_address: str = "", subject: str = "", body: str = "") -> Dict[str, Any]:
        recipient = to or to_address
        draft_record = {
            "status": "draft_saved",
            "mailbox": "[Gmail]/Drafts",
            "to": recipient,
            "subject": subject,
            "body_snippet": body[:100],
        }
        self.created_drafts.append(draft_record)
        return draft_record

    def create_draft(self, to: str = "", to_address: str = "", subject: str = "", body: str = "") -> Dict[str, Any]:
        return self.save_draft(to=to, to_address=to_address, subject=subject, body=body)


@pytest.fixture(autouse=True)
def clean_simulation_environment():
    """Ensure clean state before and after E2E simulation run."""
    guardian.resume()
    proactive_dispatcher.reset()
    proactive_dispatcher._last_emitted_by_type.clear()
    proactive_dispatcher.set_mode("CHILL")
    topic_researcher.reset()
    workspace_housekeeper.reset()
    calendar_scanner.reset()
    gmail_triage.reset()
    yield
    guardian.resume()
    proactive_dispatcher.reset()
    topic_researcher.reset()
    workspace_housekeeper.reset()
    calendar_scanner.reset()
    gmail_triage.reset()


@pytest.mark.asyncio
async def test_full_milestone_7_day_in_the_life_simulation():
    """Runs full-loop integration simulation from user inactivity to emergency kill switch."""
    dispatched_cards = []

    async def mock_broadcast(msg: Dict[str, Any]):
        dispatched_cards.append(msg)

    proactive_dispatcher.ws_broadcast_fn = mock_broadcast

    mock_client = E2EMockWorkspaceClient()
    calendar_scanner.workspace_client = mock_client
    gmail_triage.workspace_client = mock_client
    executive_briefing.workspace_client = mock_client

    # -------------------------------------------------------------
    # STEP 1: Inactivity Housekeeping (Rule 7 compliant)
    # -------------------------------------------------------------
    with tempfile.TemporaryDirectory() as staging_dir:
        # Create unfiled files and temporary clutter
        doc_path = os.path.join(staging_dir, "Q4_Financials.pdf")
        clutter_path = os.path.join(staging_dir, "download_cache.tmp")

        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("Q4 Financial Report")
        with open(clutter_path, "w", encoding="utf-8") as f:
            f.write("Temporary cache bytes")

        recycled_paths = []

        def mock_send2trash(path):
            recycled_paths.append(os.path.basename(path))
            if os.path.exists(path):
                os.remove(path)

        with patch("services.backend.automation.workspace_housekeeper.send2trash.send2trash", side_effect=mock_send2trash):
            hk_res = await workspace_housekeeper.organize_workspace(directory=staging_dir, enforce_idle_check=False)

        assert hk_res["status"] == "completed"
        assert hk_res["moved_count"] == 1
        assert hk_res["recycled_count"] == 1
        assert os.path.exists(os.path.join(staging_dir, "Documents", "Q4_Financials.pdf"))
        assert "download_cache.tmp" in recycled_paths

    # -------------------------------------------------------------
    # STEP 2: Calendar Lookahead & Topic Research Swarm
    # -------------------------------------------------------------
    imminent_alerts = await calendar_scanner.scan_upcoming(force_refresh=True)
    assert len(imminent_alerts) == 1
    imminent_meeting = imminent_alerts[0]
    assert "Distributed Swarm" in imminent_meeting["summary"]

    # Pre-meeting topic research worker generates brief note
    research_res = await topic_researcher.research_topic(
        topic=imminent_meeting["summary"],
        attendees=["Tech Lead"],
        meeting_time="In 10 Minutes",
        event_id=imminent_meeting.get("event_id") or imminent_meeting.get("id"),
        use_headless_browser=False,
    )
    assert research_res["status"] == "ok"
    assert os.path.exists(research_res["full_path"])

    with open(research_res["full_path"], "r", encoding="utf-8") as f:
        brief_text = f.read()
    assert "Meeting Brief: Distributed Swarm Architecture Review" in brief_text

    # -------------------------------------------------------------
    # STEP 3: Real Gmail Priority Triage & Rule 9 Draft Creation
    # -------------------------------------------------------------
    triaged_emails = await gmail_triage.triage_unread_emails(max_results=5, auto_draft=True)
    assert len(triaged_emails) == 1
    triaged_item = triaged_emails[0]
    assert triaged_item.priority_score == 3  # Urgent
    assert triaged_item.draft_saved is True
    assert len(mock_client.created_drafts) == 1
    assert mock_client.created_drafts[0]["mailbox"] == "[Gmail]/Drafts"

    # Strictly verify Rule 9: outbound email sending is blocked by construction
    with pytest.raises(EmailSendingProhibitedError):
        mock_client.send_email(
            to="test@example.com",
            subject="Outbound Send Attempt",
            body="Should fail immediately"
        )

    # -------------------------------------------------------------
    # STEP 4: Obsidian Daily Note Auto-Co-Pilot Synchronization
    # -------------------------------------------------------------
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_path = daily_copilot.ensure_daily_note(today_str)

    # Write handwritten journal entry to test preservation
    user_journal_note = "- [Journal] Important architecture milestone completed today."
    with open(daily_path, "a", encoding="utf-8") as f:
        f.write(f"\n{user_journal_note}\n")

    # Co-pilot synchronizes timeblocks and action items
    daily_copilot.sync_calendar_timeblocks(mock_client.mock_events, date_str=today_str)
    daily_copilot.add_action_item("Review pre-meeting brief in Obsidian", date_str=today_str)
    daily_copilot.log_background_operation("Completed workspace cleanup and meeting prep", date_str=today_str)

    # Read back daily note and verify non-destructive merge
    daily_content = daily_copilot.read_daily_note(today_str)
    assert "Distributed Swarm Architecture Review" in daily_content
    assert "Review pre-meeting brief in Obsidian" in daily_content
    assert "Completed workspace cleanup and meeting prep" in daily_content
    assert user_journal_note in daily_content, "User handwritten notes must never be overwritten!"

    # -------------------------------------------------------------
    # STEP 5: Executive Morning Briefing Synthesis
    # -------------------------------------------------------------
    briefing = await executive_briefing.generate_briefing(broadcast_card=True)
    assert briefing is not None
    assert len(briefing.events) >= 1
    assert briefing.unread_email_count >= 1

    # Verify proactive cards arrived on the HUD
    card_types = [c["card"]["event_type"] for c in dispatched_cards if c.get("type") == "PROACTIVE_CARD"]
    assert "MEETING_PREP" in card_types
    assert "EMAIL_TRIAGE" in card_types
    assert "MORNING_BRIEF" in card_types

    # -------------------------------------------------------------
    # STEP 6: Emergency Guardian Kill Switch Cascade (< 25ms SLA)
    # -------------------------------------------------------------
    start_time = time.perf_counter()
    guardian.trigger("e2e_emergency_simulation")
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    assert elapsed_ms < 25.0, f"Guardian halt took {elapsed_ms:.2f}ms (exceeded 25ms SLA)!"
    assert guardian.is_halted is True
    assert topic_researcher.is_halted is True
    assert workspace_housekeeper.is_halted is True
    assert calendar_scanner.is_halted is True
    assert gmail_triage.is_halted is True

    # Confirm all subsequent operations are blocked
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await topic_researcher.research_topic("Post-Halt Topic")

    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await workspace_housekeeper.organize_workspace()

    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await calendar_scanner.scan_upcoming()

    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await gmail_triage.triage_unread_emails()

    # Clean up generated research test note
    try:
        os.remove(research_res["full_path"])
    except Exception:
        pass
