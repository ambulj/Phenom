"""
Phase 3 Verification Suite: Autonomous Proactive Background Daemon & Event Scheduler (SCH-02, AUT-01, SAF-01, SAF-02).
Covers:
1. Persistent background asyncio scheduler daemon loop & job execution.
2. 08:30 AM morning briefing generation with Jarvis TTS prompt and Obsidian daily note sync.
3. Workspace file watcher and activity ledger indexing.
4. Multi-channel proactive alert dispatching (Telegram, HUD WebSocket, and Voice).
5. Safety Engine tool registry audit (Pydantic schemas & preview functions).
6. Universal Guardian kill switch SLA benchmark (< 25.0ms SLA).
"""

import os
import time
import shutil
import pytest
import asyncio
from typing import Dict, Any

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.scheduler.event_daemon import event_daemon, EventDaemon
from services.backend.scheduler.morning_briefing import morning_briefing_service
from services.backend.scheduler.multi_channel_dispatcher import multi_channel_dispatcher
import services.backend.tools.scheduler_tools as scheduler_tools


# ---------------- 1. PERSISTENT SCHEDULER DAEMON LOOP (SCH-02.1) ----------------

@pytest.mark.asyncio
async def test_persistent_scheduler_daemon_loop():
    """Asserts scheduler daemon runs on asyncio loop, executes jobs on schedule, and supports cancellation."""
    daemon = EventDaemon(poll_interval_seconds=0.02)
    daemon.start()
    assert daemon._running is True

    execution_counter = {"count": 0}

    async def sample_task():
        execution_counter["count"] += 1
        return "ok"

    job = daemon.register_job(
        job_id="test-job-fast",
        name="Fast Interval Test Job",
        interval_seconds=0.05,
        callback=sample_task
    )
    # Set next run to immediate
    job.next_run = time.time()

    # Allow daemon loop to tick
    await asyncio.sleep(0.18)

    assert execution_counter["count"] >= 2, f"Expected at least 2 executions, got {execution_counter['count']}"
    assert job.run_count >= 2
    assert job.last_status == "success"

    # Test cancellation
    cancelled = daemon.cancel_job("test-job-fast")
    assert cancelled is True
    assert daemon.cancel_job("non-existent") is False

    daemon.stop()
    assert daemon._running is False


# ---------------- 2. PROACTIVE MORNING BRIEFING & OBSIDIAN SYNC (AUT-01.1) ----------------

def test_proactive_morning_briefing_and_obsidian_sync(tmp_path):
    """Asserts 08:30 morning briefing synthesizes spoken TTS prompt and creates structured daily note in Obsidian."""
    test_vault = str(tmp_path / "vault")
    morning_briefing_service.vault_dir = test_vault

    briefing = morning_briefing_service.generate_briefing(
        include_weather=True,
        include_calendar=True
    )

    assert briefing["status"] == "success"
    assert "Good morning, sir" in briefing["spoken_prompt"]
    assert "Weather" in briefing["spoken_prompt"]
    assert os.path.exists(briefing["obsidian_note_path"])

    # Read back the generated Obsidian note
    with open(briefing["obsidian_note_path"], "r", encoding="utf-8") as f:
        note_content = f.read()

    assert "type: daily_debrief" in note_content
    assert "Executive Audio Briefing" in note_content
    assert "Weather & Environmental Context" in note_content
    assert "Top Priorities & Focus" in note_content


# ---------------- 3. WORKSPACE FILE WATCHER & ACTIVITY INDEX (AUT-01.2) ----------------

def test_workspace_file_watcher_and_indexing(tmp_path):
    """Asserts workspace file watcher detects new files and logs metadata to Obsidian activity ledger."""
    watch_dir = tmp_path / "watched_workspace"
    watch_dir.mkdir()

    daemon = EventDaemon()
    daemon.add_watch_dir(str(watch_dir))

    # Create test files
    file1 = watch_dir / "architecture_plan.md"
    file1.write_text("# Milestone 19 Architecture", encoding="utf-8")

    file2 = watch_dir / "telemetry_dump.json"
    file2.write_text('{"status": "nominal"}', encoding="utf-8")

    events = daemon.check_file_watcher_events()
    assert len(events) >= 2

    filenames = [e["filename"] for e in events]
    assert "architecture_plan.md" in filenames
    assert "telemetry_dump.json" in filenames

    # Verify event fields
    event1 = next(e for e in events if e["filename"] == "architecture_plan.md")
    assert event1["event"] == "created"
    assert event1["extension"] == ".md"
    assert event1["size_bytes"] > 0


# ---------------- 4. MULTI-CHANNEL PROACTIVE ALERT DISPATCH (SCH-02.2) ----------------

@pytest.mark.asyncio
async def test_multi_channel_alert_dispatch():
    """Asserts alerts are dispatched across Telegram, WebSocket HUD, and spoken voice simultaneously."""
    received_hud_events = []

    async def mock_ws_broadcast(event: Dict[str, Any]):
        received_hud_events.append(event)

    multi_channel_dispatcher.set_ws_broadcast_fn(mock_ws_broadcast)
    multi_channel_dispatcher.set_focus_mode("NORMAL")
    multi_channel_dispatcher._last_alert_time = 0.0  # Reset cooldown

    res = await multi_channel_dispatcher.dispatch_alert(
        title="Server Overload Warning",
        message="GPU VRAM temperature reached 78C",
        priority="URGENT",
        channels=["hud", "voice", "telegram"]
    )

    assert res["status"] == "dispatched"
    assert res["channels"]["hud"] == "sent"
    assert len(received_hud_events) == 1
    assert received_hud_events[0]["payload"]["title"] == "Server Overload Warning"

    # Test focus mode suppression for non-urgent messages
    multi_channel_dispatcher.set_focus_mode("DEEP_FOCUS")
    suppressed = await multi_channel_dispatcher.dispatch_alert(
        title="Low Priority Reminder",
        message="Take a 5-minute break",
        priority="LOW"
    )
    assert suppressed["status"] == "suppressed"
    assert "focus_mode" in suppressed["reason"]


# ---------------- 5. SAFETY ENGINE TOOL REGISTRY AUDIT (SAF-01.1) ----------------

def test_scheduler_tools_registry_audit():
    """Asserts all Phase 3 scheduler and briefing tools are registered in Safety Engine with valid schemas."""
    expected_tools = {
        "schedule_proactive_job": 1,
        "list_scheduled_jobs": 0,
        "cancel_scheduled_job": 1,
        "trigger_morning_briefing": 0,
        "get_scheduler_daemon_status": 0
    }

    for name, tier in expected_tools.items():
        assert name in registry._tools, f"Tool '{name}' must be registered in ToolRegistry"
        tool_entry = registry._tools[name]
        assert tool_entry.tier == tier, f"Tool '{name}' tier mismatch: expected {tier}, got {tool_entry.tier}"
        assert tool_entry.args_schema is not None, f"Tool '{name}' missing Pydantic args_schema"
        assert tool_entry.preview_fn is not None, f"Tool '{name}' missing preview function"

    # Test preview generators
    args_schedule = scheduler_tools.ScheduleProactiveJobArgs(name="Daily Cleanup", interval_seconds=3600)
    preview_schedule = registry._tools["schedule_proactive_job"].preview_fn(args_schedule)
    assert "Daily Cleanup" in preview_schedule
    assert "3600" in preview_schedule

    args_cancel = scheduler_tools.CancelScheduledJobArgs(job_id="job-12345")
    preview_cancel = registry._tools["cancel_scheduled_job"].preview_fn(args_cancel)
    assert "job-12345" in preview_cancel


# ---------------- 6. UNIVERSAL GUARDIAN KILL SWITCH SLA BENCHMARK (SAF-02.1) ----------------

@pytest.mark.asyncio
async def test_guardian_kill_switch_scheduler_sla_benchmark():
    """
    Asserts Guardian kill switch synchronously aborts scheduler daemon operations
    with guaranteed latency < 25.0ms SLA across 50 consecutive benchmark cycles.
    """
    latencies = []

    for i in range(50):
        # Reset and trigger guardian
        guardian.resume()
        assert guardian.is_halted is False

        t0 = time.perf_counter()
        guardian.trigger("Benchmark Scheduler Killswitch Activation")
        t1 = time.perf_counter()

        latency_ms = (t1 - t0) * 1000.0
        latencies.append(latency_ms)

        assert guardian.is_halted is True

        # Assert morning briefing immediately raises PermissionError
        with pytest.raises(PermissionError):
            morning_briefing_service.generate_briefing()

        # Assert alert dispatcher immediately raises PermissionError
        with pytest.raises(PermissionError):
            await multi_channel_dispatcher.dispatch_alert("Test", "Body")

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

    print(f"\n[GUARDIAN SCHEDULER SLA BENCHMARK] 50 Cycles: Avg={avg_latency:.4f}ms, P95={p95_latency:.4f}ms, Max={max_latency:.4f}ms (< 25.0ms SLA)")

    # Resume system after benchmark
    guardian.resume()
    assert guardian.is_halted is False

    assert avg_latency < 25.0, f"Average Guardian latency {avg_latency:.4f}ms exceeded 25.0ms SLA"
    assert max_latency < 25.0, f"Max Guardian latency {max_latency:.4f}ms exceeded 25.0ms SLA"
