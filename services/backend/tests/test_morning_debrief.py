"""
Unit tests for Phenom Morning Debrief Synthesizer (MIS-01).
Verifies:
1. Debrief aggregation across multiple completed, failed, and aborted missions.
2. Non-destructive Obsidian Daily Notes merging under '## 🌙 Overnight Autonomous Missions'.
3. WebSocket payload generation for Cyber HUD morning debrief card.
4. Executive summary witty British Jarvis phrasing.
5. User return event integration.
"""

import os
import shutil
import tempfile
import pytest

from services.backend.missions.morning_debrief import (
    DEBRIEF_SECTION_HEADER,
    MorningDebriefSynthesizer,
)
from services.backend.missions.unattended_runner import UnattendedMissionRunner
from services.backend.schemas.missions import (
    MissionResult,
    MissionStatus,
    current_iso_time,
)


@pytest.fixture
def mock_missions():
    """Returns a list of sample mission results."""
    m1 = MissionResult(
        mission_id="msn_001",
        title="Refactor auth token verification",
        status=MissionStatus.COMPLETED,
        tests_passed=12,
        tests_fixed=2,
        lines_added=45,
        lines_deleted=10,
        files_changed=["services/backend/auth.py", "tests/test_auth.py"],
        branch_name="mission/msn_001",
        worktree_path="C:/Phenom/.phenom_sandbox/missions/msn_001",
        started_at="2026-11-04T02:00:00Z",
        completed_at="2026-11-04T02:05:00Z",
        diagnostic_log="Healed successfully in 2 iterations.",
    )
    m2 = MissionResult(
        mission_id="msn_002",
        title="Optimize vector index caching",
        status=MissionStatus.FAILED,
        tests_passed=5,
        tests_fixed=0,
        lines_added=15,
        lines_deleted=2,
        files_changed=["services/backend/cache.py"],
        branch_name="mission/msn_002",
        worktree_path="C:/Phenom/.phenom_sandbox/missions/msn_002",
        started_at="2026-11-04T03:00:00Z",
        completed_at="2026-11-04T03:10:00Z",
        diagnostic_log="Self-healing exhausted after 5 iterations.\nFinal error [AssertionError]: cache mismatch",
    )
    return [m1, m2]


@pytest.fixture
def temp_vault():
    """Creates a temporary Obsidian vault directory."""
    d = tempfile.mkdtemp(prefix="phenom_test_vault_")
    yield d
    try:
        shutil.rmtree(d)
    except Exception:
        pass


def test_debrief_aggregation(mock_missions):
    """Verifies KPI aggregation across multiple missions."""
    runner = UnattendedMissionRunner()
    for m in mock_missions:
        runner._mission_history[m.mission_id] = m

    synth = MorningDebriefSynthesizer(runner=runner)
    summary = synth.aggregate_debrief(date_str="2026-11-04")

    assert summary.total_missions == 2
    assert summary.successful_missions == 1
    assert summary.failed_missions == 1
    assert summary.tests_fixed == 2
    assert summary.lines_added == 60
    assert summary.lines_deleted == 12
    assert len(summary.touched_files) == 3
    assert "services/backend/auth.py" in summary.touched_files
    assert "Good morning, sir" in summary.executive_summary


def test_non_destructive_obsidian_sync(mock_missions, temp_vault):
    """Verifies that overnight mission summary is merged into Daily Note preserving user text."""
    runner = UnattendedMissionRunner()
    for m in mock_missions:
        runner._mission_history[m.mission_id] = m

    synth = MorningDebriefSynthesizer(runner=runner, vault_path=temp_vault)
    date_str = "2026-11-04"

    # Pre-create daily note with user's handwritten journal
    note_dir = os.path.join(temp_vault, "Daily Notes")
    os.makedirs(note_dir, exist_ok=True)
    note_path = os.path.join(note_dir, f"{date_str}.md")

    user_note = (
        f"# Daily Note: {date_str}\n\n"
        "## 📝 My Morning Intentions\n"
        "- [ ] Ship Milestone 9.0\n"
        "- [ ] Have coffee with team\n\n"
        "## 💡 Reflections\n"
        "Great progress yesterday on the knowledge graph.\n"
    )
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(user_note)

    # Sync debrief
    merged_content = synth.sync_to_obsidian_daily_note(date_str=date_str)

    # Invariant: User notes remain intact
    assert "## 📝 My Morning Intentions" in merged_content
    assert "- [ ] Ship Milestone 9.0" in merged_content
    assert "Great progress yesterday on the knowledge graph." in merged_content

    # Invariant: Debrief section added cleanly
    assert DEBRIEF_SECTION_HEADER in merged_content
    assert "Refactor auth token verification" in merged_content
    assert "Optimize vector index caching" in merged_content

    # Sync a second time (idempotent update)
    second_sync = synth.sync_to_obsidian_daily_note(date_str=date_str)
    # Ensure header is NOT duplicated
    assert second_sync.count(DEBRIEF_SECTION_HEADER) == 1
    assert "## 📝 My Morning Intentions" in second_sync


def test_build_debrief_payload(mock_missions):
    """Verifies WebSocket payload formatting for desktop Cyber HUD."""
    runner = UnattendedMissionRunner()
    for m in mock_missions:
        runner._mission_history[m.mission_id] = m

    synth = MorningDebriefSynthesizer(runner=runner)
    payload_wrapper = synth.build_debrief_payload(date_str="2026-11-04")

    assert payload_wrapper["type"] == "mission.morning_debrief"
    payload = payload_wrapper["payload"]
    assert payload["celebrate"] is True
    assert payload["summary"]["total_missions"] == 2
    assert payload["summary"]["successful_missions"] == 1
    assert payload["summary"]["tests_fixed"] == 2


def test_user_return_trigger(mock_missions, temp_vault):
    """Verifies user return trigger executes debrief broadcast and obsidian sync."""
    runner = UnattendedMissionRunner()
    for m in mock_missions:
        runner._mission_history[m.mission_id] = m

    broadcast_messages = []
    synth = MorningDebriefSynthesizer(runner=runner, vault_path=temp_vault)
    synth.register_broadcaster(lambda msg: broadcast_messages.append(msg))

    result = synth.on_user_return()

    assert result is not None
    assert len(broadcast_messages) == 1
    assert broadcast_messages[0]["type"] == "mission.morning_debrief"

    # Verify daily note exists
    daily_notes = os.listdir(os.path.join(temp_vault, "Daily Notes"))
    assert len(daily_notes) == 1
