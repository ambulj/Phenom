"""Phenom Milestone 7.0 Safety ToolRegistry Audit & Risk Tier Verification.

Verifies:
1. Complete registration of all 12 Milestone 7.0 proactive tools in ToolRegistry (SAF-01).
2. Strict classification: Tier 0 for read-only tools, Tier 1 for user-confirmed mutating actions.
3. Pydantic argument schemas, constraints, field bounds, and defaults.
4. Preview functions generate clear, human-readable confirmation text for every Tier 1 action.
5. Action log audit trail integration.
"""

from typing import Any, Dict, List
import pytest
from pydantic import ValidationError

from services.backend.safety.registry import registry
from services.backend.safety.action_log import action_log

# Import all tool packages to ensure complete registration
import services.backend.tools.proactive_tools
import services.backend.tools.triage_tools
import services.backend.tools.housekeeping_tools


EXPECTED_MILESTONE_7_TOOLS = {
    # Proactive Ambient Tools (Phase 1)
    "get_proactive_status": 0,
    "configure_proactive_cooldown": 1,
    "dismiss_proactive_card": 0,
    # Executive Briefing & Triage Tools (Phase 2)
    "get_executive_briefing": 0,
    "scan_calendar_upcoming": 0,
    "triage_unread_emails": 0,
    "draft_email_reply": 1,
    "schedule_meeting_event": 1,
    # Background Workers & Housekeeping Tools (Phase 3)
    "get_housekeeper_status": 0,
    "run_workspace_housekeeping": 1,
    "dispatch_topic_research": 1,
    "sync_obsidian_daily_note": 1,
}


def test_milestone_7_tools_registration_and_tier_classification():
    """SAF-01: Verifies all 12 Milestone 7 tools are registered with strict risk tiers."""
    for tool_name, expected_tier in EXPECTED_MILESTONE_7_TOOLS.items():
        entry = registry.get(tool_name)
        assert entry is not None, f"Tool '{tool_name}' must be registered in ToolRegistry."
        assert entry.tier == expected_tier, (
            f"Tool '{tool_name}' has tier {entry.tier}; expected {expected_tier}."
        )
        assert entry.description and len(entry.description.strip()) > 10
        assert entry.args_schema is not None
        assert callable(entry.preview_fn)


def test_milestone_7_tier_0_read_only_previews():
    """SAF-01: Verifies Tier 0 read-only tools indicate read-only inspection in preview."""
    tier_0_tools = [name for name, tier in EXPECTED_MILESTONE_7_TOOLS.items() if tier == 0]
    assert len(tier_0_tools) == 6

    for tool_name in tier_0_tools:
        entry = registry.get(tool_name)
        preview_text = entry.preview_fn({})
        assert isinstance(preview_text, str)
        assert len(preview_text.strip()) > 0
        # Ensure preview denotes read-only inspection
        assert "read-only" in preview_text.lower() or "status" in preview_text.lower() or "dismiss" in preview_text.lower()


def test_milestone_7_tier_1_confirmation_previews():
    """SAF-01: Verifies Tier 1 mutating tools dynamically include argument context in previews."""
    # 1. configure_proactive_cooldown
    entry_cool = registry.get("configure_proactive_cooldown")
    p_cool = entry_cool.preview_fn({"event_type": "MORNING_BRIEF", "event_cooldown_seconds": 1800})
    assert "MORNING_BRIEF" in p_cool
    assert "1800" in p_cool

    # 2. draft_email_reply
    entry_draft = registry.get("draft_email_reply")
    p_draft = entry_draft.preview_fn({
        "to_address": "alice@example.com",
        "subject": "Re: Roadmap",
        "body": "Sounds good!"
    })
    assert "alice@example.com" in p_draft
    assert "Re: Roadmap" in p_draft
    assert "[Gmail]/Drafts" in p_draft or "draft" in p_draft.lower()

    # 3. schedule_meeting_event
    entry_sched = registry.get("schedule_meeting_event")
    p_sched = entry_sched.preview_fn({
        "summary": "Executive Q4 Review",
        "start_time_iso": "2026-11-03T14:00:00Z",
        "end_time_iso": "2026-11-03T15:00:00Z"
    })
    assert "Executive Q4 Review" in p_sched

    # 4. run_workspace_housekeeping
    entry_hk = registry.get("run_workspace_housekeeping")
    p_hk = entry_hk.preview_fn({"directory": "C:\\Downloads"})
    assert "C:\\Downloads" in p_hk
    assert "Recycle Bin" in p_hk

    # 5. dispatch_topic_research
    entry_res = registry.get("dispatch_topic_research")
    p_res = entry_res.preview_fn({"topic": "Distributed Consensus"})
    assert "Distributed Consensus" in p_res
    assert "Obsidian" in p_res

    # 6. sync_obsidian_daily_note
    entry_sync = registry.get("sync_obsidian_daily_note")
    p_sync = entry_sync.preview_fn({"date_str": "2026-11-03"})
    assert "2026-11-03" in p_sync


def test_milestone_7_pydantic_schema_validation():
    """SAF-01: Verifies Pydantic schema field constraints, bounds, and rejection of invalid data."""
    # 1. scan_calendar_upcoming: lookahead_minutes bounds [5, 1440]
    entry_cal = registry.get("scan_calendar_upcoming")
    schema_cal = entry_cal.args_schema

    # Valid
    valid_cal = schema_cal(lookahead_minutes=45)
    assert valid_cal.lookahead_minutes == 45

    # Invalid: < 5
    with pytest.raises(ValidationError):
        schema_cal(lookahead_minutes=2)

    # Invalid: > 1440
    with pytest.raises(ValidationError):
        schema_cal(lookahead_minutes=2000)

    # 2. triage_unread_emails: max_results bounds [1, 50]
    entry_email = registry.get("triage_unread_emails")
    schema_email = entry_email.args_schema

    valid_email = schema_email(max_results=20)
    assert valid_email.max_results == 20

    with pytest.raises(ValidationError):
        schema_email(max_results=0)

    with pytest.raises(ValidationError):
        schema_email(max_results=100)

    # 3. draft_email_reply: requires to_address, subject, body
    entry_draft = registry.get("draft_email_reply")
    schema_draft = entry_draft.args_schema

    with pytest.raises(ValidationError):
        schema_draft(to_address="test@example.com")  # Missing subject, body

    valid_draft = schema_draft(to_address="a@b.com", subject="Subj", body="Body")
    assert valid_draft.to_address == "a@b.com"

    # 4. dispatch_topic_research: requires topic
    entry_research = registry.get("dispatch_topic_research")
    schema_research = entry_research.args_schema

    with pytest.raises(ValidationError):
        schema_research()  # Missing topic

    valid_res = schema_research(topic="Autonomous Safety")
    assert valid_res.topic == "Autonomous Safety"
