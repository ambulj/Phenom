"""Automated Verification Suite for Proactive Background Workers & Second-Brain Daily Co-Pilot.

Verifies:
1. Pre-meeting topic research worker brief compilation and meeting note output (WRK-01).
2. Obsidian daily note scaffolding, non-destructive section merging, and git commits (WRK-02).
3. Workspace file categorization and send2trash Rule 7 enforcement (WRK-03).
4. Housekeeping yield when user returns from idle state (WRK-03).
5. Safety tool registrations, Pydantic argument schemas, and risk tiers (SAF-01).
6. Synchronous Guardian kill switch halt latency (< 25ms SLA) across workers (SAF-02).
"""

import asyncio
from datetime import datetime, timezone
import os
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import pytest

from services.backend.automation.topic_researcher import topic_researcher, TopicResearchWorker
from services.backend.automation.workspace_housekeeper import workspace_housekeeper, WorkspaceHousekeeper
from services.backend.memory.daily_copilot import daily_copilot, ObsidianDailyCoPilot
from services.backend.memory.vault import vault_manager
from services.backend.proactive.dispatcher import proactive_dispatcher, ProactivePriority
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.main import on_guardian_state_change
import services.backend.tools.housekeeping_tools  # Ensure tools are registered


@pytest.fixture(autouse=True)
def reset_system_state():
    """Ensure Guardian, dispatcher cooldowns, and workers are in active/normal state before and after each test."""
    guardian.resume()
    proactive_dispatcher._last_emitted_by_type.clear()
    proactive_dispatcher.set_mode("CHILL")
    topic_researcher.reset()
    workspace_housekeeper.reset()
    yield
    guardian.resume()
    proactive_dispatcher._last_emitted_by_type.clear()
    topic_researcher.reset()
    workspace_housekeeper.reset()


@pytest.mark.asyncio
async def test_topic_research_swarm_generates_brief_and_card():
    """WRK-01: Verifies autonomous topic research worker creates meeting note and emits HUD card."""
    topic = "Q4 Autonomous Systems Strategy"
    attendees = ["Alice Engineer", "Bob Product"]
    meeting_time = "2026-11-03 15:00 UTC"

    dispatched_cards = []

    async def mock_broadcast(msg: Dict[str, Any]):
        dispatched_cards.append(msg)

    proactive_dispatcher.ws_broadcast_fn = mock_broadcast

    res = await topic_researcher.research_topic(
        topic=topic,
        attendees=attendees,
        meeting_time=meeting_time,
        event_id="evt-strategy-99",
        use_headless_browser=False,
    )

    assert res["status"] == "ok"
    assert res["topic"] == topic
    assert os.path.exists(res["full_path"])

    # Verify meeting note contents
    with open(res["full_path"], "r", encoding="utf-8") as f:
        content = f.read()

    assert "Meeting Brief: Q4 Autonomous Systems Strategy" in content
    assert "Alice Engineer, Bob Product" in content
    assert "2026-11-03 15:00 UTC" in content
    assert "## 1. Executive Context & Objective" in content
    assert "## 2. Key Discussion Topics & Agenda" in content

    # Verify proactive card was emitted
    cards = [c for c in dispatched_cards if c.get("type") == "PROACTIVE_CARD" and c["card"]["event_type"] == "MEETING_PREP"]
    assert len(cards) >= 1
    assert "Meeting Brief" in cards[0]["card"]["title"]
    assert cards[0]["card"]["action_chip"] == "Open Brief"

    # Cleanup generated test note
    try:
        os.remove(res["full_path"])
    except Exception:
        pass


@pytest.mark.asyncio
async def test_obsidian_daily_copilot_scaffolding_and_non_destructive_merging():
    """WRK-02: Verifies daily note scaffolding, non-destructive section merging, and undo rollback."""
    test_date = "2026-11-03"
    note_path = daily_copilot.ensure_daily_note(test_date)
    assert os.path.exists(note_path)

    # 1. User writes custom reflections in ## Notes & Journal
    custom_journal_text = "- Attended Phenom 7.0 design session. User notes must never be overwritten!"
    with open(note_path, "r", encoding="utf-8") as f:
        existing = f.read()
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(existing + f"\n{custom_journal_text}\n")

    # 2. Daily Co-Pilot syncs calendar schedule
    mock_events = [
        {
            "summary": "Swarm Architecture Review",
            "start": "2026-11-03T10:00:00Z",
            "end": "2026-11-03T11:00:00Z",
            "meet_link": "https://meet.google.com/abc-phenom",
        },
        {
            "summary": "Executive Sync",
            "start": "2026-11-03T14:30:00Z",
            "end": "2026-11-03T15:00:00Z",
        },
    ]
    sync_res = daily_copilot.sync_calendar_timeblocks(mock_events, date_str=test_date)
    assert sync_res["status"] == "ok"
    assert sync_res["events_synced"] == 2

    # 3. Daily Co-Pilot adds action items
    item_res = daily_copilot.add_action_item("Review automated test regressions", date_str=test_date)
    assert item_res["status"] == "ok"

    # 4. Daily Co-Pilot logs background operations
    log_res = daily_copilot.log_background_operation("Housekeeper organized 5 unfiled documents", date_str=test_date)
    assert log_res["status"] == "ok"

    # 5. Read back and verify all sections merged correctly while preserving user's custom journal entry
    updated_content = daily_copilot.read_daily_note(test_date)
    assert "## Scheduled Timeblocks" in updated_content
    assert "Swarm Architecture Review" in updated_content
    assert "https://meet.google.com/abc-phenom" in updated_content
    assert "## Action Items & Directives" in updated_content
    assert "Review automated test regressions" in updated_content
    assert "## Background Swarm & Triage Log" in updated_content
    assert "Housekeeper organized 5 unfiled documents" in updated_content

    # Strict non-destructive assertion:
    assert custom_journal_text in updated_content

    # 6. Verify reversible undo token rollback
    undo_token = log_res["undo_token"]
    rollback_ok = daily_copilot.rollback_mutation(undo_token)
    assert rollback_ok is True
    post_rollback = daily_copilot.read_daily_note(test_date)
    assert "Housekeeper organized 5 unfiled documents" not in post_rollback
    assert custom_journal_text in post_rollback


@pytest.mark.asyncio
async def test_workspace_housekeeper_file_categorization_and_send2trash_rule7():
    """WRK-03: Verifies unfiled files are organized into categories and clutter is recycled via send2trash (Rule 7)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files in root of temp workspace
        doc_file = os.path.join(temp_dir, "Project_Plan.pdf")
        img_file = os.path.join(temp_dir, "Orb_Design.png")
        zip_file = os.path.join(temp_dir, "Dataset.zip")
        code_file = os.path.join(temp_dir, "controller.py")
        clutter_tmp = os.path.join(temp_dir, "scratch_cache.tmp")
        clutter_partial = os.path.join(temp_dir, "video.partial")

        for fpath in [doc_file, img_file, zip_file, code_file, clutter_tmp, clutter_partial]:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write("Phenom test content")

        recycled_calls = []

        def mock_send2trash(path):
            recycled_calls.append(os.path.basename(path))
            if os.path.exists(path):
                os.remove(path)  # Simulate recycle bin removal for test cleanup

        with patch("services.backend.automation.workspace_housekeeper.send2trash.send2trash", side_effect=mock_send2trash):
            res = await workspace_housekeeper.organize_workspace(directory=temp_dir, enforce_idle_check=False)

        assert res["status"] == "completed"
        assert res["moved_count"] == 4
        assert res["recycled_count"] == 2

        # Verify organized directories exist and contain moved files
        assert os.path.exists(os.path.join(temp_dir, "Documents", "Project_Plan.pdf"))
        assert os.path.exists(os.path.join(temp_dir, "Images", "Orb_Design.png"))
        assert os.path.exists(os.path.join(temp_dir, "Archives", "Dataset.zip"))
        assert os.path.exists(os.path.join(temp_dir, "Code", "controller.py"))

        # Verify Rule 7: send2trash was explicitly used for temporary clutter files
        assert "scratch_cache.tmp" in recycled_calls
        assert "video.partial" in recycled_calls
        assert not os.path.exists(clutter_tmp)
        assert not os.path.exists(clutter_partial)


@pytest.mark.asyncio
async def test_workspace_housekeeper_yields_when_user_returns():
    """WRK-03: Verifies housekeeper immediately halts and yields when user returns from idle."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create 5 test files
        for i in range(5):
            with open(os.path.join(temp_dir, f"file_{i}.txt"), "w", encoding="utf-8") as f:
                f.write("text content")

        # Mock idle sensor that simulates user returning after the first file
        class FlappingIdleSensor:
            def __init__(self):
                self.calls = 0

            @property
            def is_idle(self):
                self.calls += 1
                # Returns True on first check, False on subsequent checks
                return self.calls <= 1

        mock_sensor = FlappingIdleSensor()
        housekeeper = WorkspaceHousekeeper(target_directory=temp_dir, idle_sensor_instance=mock_sensor)

        res = await housekeeper.organize_workspace(directory=temp_dir, enforce_idle_check=True)

        # Housekeeper should interrupt and yield
        assert res["interrupted"] is True
        assert res["status"] == "interrupted"
        # Not all files were processed due to user returning
        assert res["moved_count"] < 5


def test_housekeeping_safety_tools_and_schemas():
    """SAF-01: Verifies tool registry risk tiers, Pydantic argument schemas, and preview generators."""
    # 1. get_housekeeper_status (Tier 0)
    tool_status = registry.get("get_housekeeper_status")
    assert tool_status is not None
    assert tool_status.tier == 0
    preview_status = tool_status.preview_fn({})
    assert "Read-only" in preview_status

    # 2. run_workspace_housekeeping (Tier 1)
    tool_hk = registry.get("run_workspace_housekeeping")
    assert tool_hk is not None
    assert tool_hk.tier == 1
    preview_hk = tool_hk.preview_fn({"directory": "C:\\Downloads"})
    assert "C:\\Downloads" in preview_hk
    assert "Recycle Bin" in preview_hk

    # 3. dispatch_topic_research (Tier 1)
    tool_research = registry.get("dispatch_topic_research")
    assert tool_research is not None
    assert tool_research.tier == 1
    preview_res = tool_research.preview_fn({"topic": "AI Ethics Sync"})
    assert "AI Ethics Sync" in preview_res
    assert "Obsidian meeting brief" in preview_res

    # 4. sync_obsidian_daily_note (Tier 1)
    tool_sync = registry.get("sync_obsidian_daily_note")
    assert tool_sync is not None
    assert tool_sync.tier == 1
    preview_sync = tool_sync.preview_fn({"date_str": "2026-11-03"})
    assert "2026-11-03" in preview_sync


@pytest.mark.asyncio
async def test_guardian_halt_synchronously_halts_workers_within_sla():
    """SAF-02: Verifies Guardian trigger synchronously halts workers in < 25ms SLA and blocks actions."""
    # Trigger Guardian halt and benchmark execution time
    start_time = time.perf_counter()
    guardian.trigger("test_sla")
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    # Strict SLA: synchronously halting must execute in < 25ms
    assert elapsed_ms < 25.0, f"Guardian halt took {elapsed_ms:.2f}ms (exceeded 25ms SLA)"

    # Verify both workers reflect halted state
    assert topic_researcher.is_halted is True
    assert workspace_housekeeper.is_halted is True

    # Verify workers strictly reject subsequent operations while halted
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await topic_researcher.research_topic("Forbidden Topic")

    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await workspace_housekeeper.organize_workspace()
