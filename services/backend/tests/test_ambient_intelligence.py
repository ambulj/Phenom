"""
Phenom Phase 3 Verification Suite: Proactive Ambient Intelligence & Context Engine
Tests context detection, process classification, hysteresis filtering, mode profiles,
hardware threshold alerts, calendar meeting detection, alert cooldowns, and Tier 0 tools.
"""

import time
import pytest
from datetime import datetime, timezone, timedelta

from services.backend.modes.mode_manager import mode_manager, AssistantMode
from services.backend.ambient.context_detector import (
    ContextDetector,
    classify_process,
    PROCESS_CATEGORY_MAP
)
from services.backend.ambient.ambient_monitor import (
    AmbientEventMonitor,
    AmbientAlert
)
from services.backend.voice.sound_fx import sound_fx
from services.backend.safety.registry import registry
from services.backend.tools.utility_tools import get_ambient_status, set_assistant_mode


# =====================================================================
# 1. MODE MANAGER & DEEP FOCUS TESTS
# =====================================================================

def test_deep_focus_profile_and_silent_policy():
    profile = mode_manager.get_mode_profile(AssistantMode.DEEP_FOCUS)
    assert profile["name"] == "Deep Focus"
    assert profile["notification_policy"] == "silent"
    assert profile["audio_volume_scale"] == 0.0

    # Test notification filtering
    mode_manager.set_mode("deep_focus")
    assert mode_manager.get_current_mode() == AssistantMode.DEEP_FOCUS
    assert mode_manager.is_notification_allowed("normal") is False
    assert mode_manager.is_notification_allowed("medium") is False
    assert mode_manager.is_notification_allowed("high") is False
    assert mode_manager.is_notification_allowed("critical") is True
    assert mode_manager.is_notification_allowed("kill_switch") is True

    # Volume scale must be 0.0
    assert mode_manager.get_volume_scale() == 0.0

    # Reset back to work
    mode_manager.set_mode("work")


def test_mode_manager_set_and_cycle_modes():
    # Set explicitly
    res_work = mode_manager.set_mode("work")
    assert res_work["mode"] == "work"

    res_study = mode_manager.set_mode("study")
    assert res_study["mode"] == "study"

    res_chill = mode_manager.set_mode("chill")
    assert res_chill["mode"] == "chill"

    res_deep = mode_manager.set_mode("deep_focus")
    assert res_deep["mode"] == "deep_focus"

    # Cycle mode order: Work -> Study -> Chill -> Deep Focus -> Work
    mode_manager.set_mode("work")
    c1 = mode_manager.cycle_mode()
    assert c1["mode"] == "study"

    c2 = mode_manager.cycle_mode()
    assert c2["mode"] == "chill"

    c3 = mode_manager.cycle_mode()
    assert c3["mode"] == "deep_focus"

    c4 = mode_manager.cycle_mode()
    assert c4["mode"] == "work"


# =====================================================================
# 2. CONTEXT DETECTOR & HYSTERESIS TESTS
# =====================================================================

def test_classify_process_names():
    assert classify_process("code.exe") == AssistantMode.WORK
    assert classify_process("cursor.exe") == AssistantMode.WORK
    assert classify_process("pycharm64.exe") == AssistantMode.WORK
    assert classify_process("windowsterminal.exe") == AssistantMode.WORK

    assert classify_process("obsidian.exe") == AssistantMode.STUDY
    assert classify_process("notion.exe") == AssistantMode.STUDY
    assert classify_process("acrobat.exe") == AssistantMode.STUDY

    assert classify_process("steam.exe") == AssistantMode.CHILL
    assert classify_process("vlc.exe") == AssistantMode.CHILL
    assert classify_process("spotify.exe") == AssistantMode.CHILL

    assert classify_process("notepad.exe") is None
    assert classify_process("") is None
    assert classify_process(None) is None


def test_context_detector_hysteresis_filter():
    detector = ContextDetector(hysteresis_seconds=5.0)
    mode_manager.set_mode("work")
    t0 = 1000.0

    # User switches to steam.exe (Chill candidate) at t=1000.0
    r1 = detector.sample_and_evaluate(override_process="steam.exe", now_ts=t0)
    assert r1["switched"] is False
    assert r1["recommended_mode"] == "chill"
    assert mode_manager.get_current_mode() == AssistantMode.WORK

    # User still on steam.exe at t=1003.0 (< 5s elapsed) -> must NOT switch yet
    r2 = detector.sample_and_evaluate(override_process="steam.exe", now_ts=t0 + 3.0)
    assert r2["switched"] is False
    assert mode_manager.get_current_mode() == AssistantMode.WORK

    # Flapping test: user quickly switches to code.exe at t=1004.0 -> resets hysteresis
    r3 = detector.sample_and_evaluate(override_process="code.exe", now_ts=t0 + 4.0)
    assert r3["switched"] is False
    assert r3["recommended_mode"] == "work"

    # User switches to obsidian.exe at t=1010.0
    detector.sample_and_evaluate(override_process="obsidian.exe", now_ts=1010.0)

    # Sustained obsidian.exe until t=1015.5 (5.5s elapsed >= 5.0s) -> MUST switch to Study!
    r4 = detector.sample_and_evaluate(override_process="obsidian.exe", now_ts=1015.5)
    assert r4["switched"] is True
    assert r4["active_mode"] == "study"
    assert mode_manager.get_current_mode() == AssistantMode.STUDY

    # Reset
    mode_manager.set_mode("work")


def test_context_detector_suppressed_in_deep_focus():
    detector = ContextDetector(hysteresis_seconds=5.0)
    mode_manager.set_mode("deep_focus")

    # In Deep Focus, detector does not switch away automatically
    res = detector.sample_and_evaluate(override_process=None, now_ts=time.time())
    assert res["switched"] is False
    assert res["active_mode"] == "deep_focus"

    mode_manager.set_mode("work")


# =====================================================================
# 3. AMBIENT EVENT MONITOR TESTS
# =====================================================================

def test_ambient_hardware_thresholds_and_cooldown():
    monitor = AmbientEventMonitor(cooldown_seconds=300.0)
    t0 = 2000.0

    # Normal metrics -> zero alerts
    a_norm = monitor.evaluate_hardware(cpu_percent=45.0, ram_percent=60.0, vram_percent=70.0, now_ts=t0)
    assert len(a_norm) == 0

    # High CPU (> 90%) and High RAM (> 85%) -> triggers 2 alerts
    a_spike = monitor.evaluate_hardware(cpu_percent=94.5, ram_percent=88.2, vram_percent=50.0, now_ts=t0)
    assert len(a_spike) == 2
    assert any(a.title == "High CPU Utilization" for a in a_spike)
    assert any(a.title == "System Memory Pressure" for a in a_spike)

    # Immediate second check at t0 + 10s -> must be suppressed by cooldown!
    a_cool = monitor.evaluate_hardware(cpu_percent=95.0, ram_percent=89.0, vram_percent=50.0, now_ts=t0 + 10.0)
    assert len(a_cool) == 0

    # After cooldown expires at t0 + 305s -> can fire again
    a_after = monitor.evaluate_hardware(cpu_percent=95.0, ram_percent=89.0, vram_percent=50.0, now_ts=t0 + 305.0)
    assert len(a_after) == 2


def test_ambient_calendar_meeting_detection_and_deduplication():
    monitor = AmbientEventMonitor()
    now_dt = datetime.now(timezone.utc)

    # Create test meetings:
    # 1. Starts in 8 minutes (in 0-15m window) -> must alert
    # 2. Starts in 45 minutes (outside window) -> no alert
    # 3. Ended 10 minutes ago -> no alert
    meeting_soon = (now_dt + timedelta(minutes=8)).isoformat()
    meeting_far = (now_dt + timedelta(minutes=45)).isoformat()
    meeting_past = (now_dt - timedelta(minutes=10)).isoformat()

    events = [
        {"id": "ev-soon-1", "summary": "Sprint Planning", "start": meeting_soon},
        {"id": "ev-far-2", "summary": "Quarterly Review", "start": meeting_far},
        {"id": "ev-past-3", "summary": "Coffee Break", "start": meeting_past}
    ]

    alerts = monitor.evaluate_calendar(events=events, now_dt=now_dt)
    assert len(alerts) == 1
    assert alerts[0].title == "Upcoming Meeting"
    assert "Sprint Planning" in alerts[0].message
    assert alerts[0].category == "calendar"

    # Second check with same event list -> deduplication prevents duplicate alert
    alerts_repeat = monitor.evaluate_calendar(events=events, now_dt=now_dt + timedelta(minutes=1))
    assert len(alerts_repeat) == 0


@pytest.mark.asyncio
async def test_ambient_monitor_mode_notification_filtering():
    monitor = AmbientEventMonitor()
    mock_hardware = {"cpu": 95.0, "ram": 50.0, "vram": 50.0}

    # 1. Under WORK mode (standard policy) -> alert is broadcast
    mode_manager.set_mode("work")
    broadcasted = []
    async def fake_broadcast(msg):
        broadcasted.append(msg)

    monitor.set_broadcaster(fake_broadcast)
    alerts_work = await monitor.evaluate_and_broadcast(mock_hardware=mock_hardware)
    assert len(alerts_work) == 1
    assert len(broadcasted) == 1
    assert broadcasted[0]["type"] == "ambient.alert"

    # 2. Under DEEP_FOCUS mode (silent policy) -> high urgency alert is suppressed!
    mode_manager.set_mode("deep_focus")
    # Reset cooldown so filter alone determines emission
    monitor._last_alert_times.clear()
    broadcasted.clear()

    alerts_deep = await monitor.evaluate_and_broadcast(mock_hardware=mock_hardware)
    assert len(alerts_deep) == 0
    assert len(broadcasted) == 0

    mode_manager.set_mode("work")


# =====================================================================
# 4. AUDIO CHIMES & PROCEDURAL SYNTHESIS TESTS
# =====================================================================

def test_sound_fx_ambient_chimes():
    # In test mode, sound_fx skips audio output safely without raising
    sound_fx.play_ambient_toast_chime()
    sound_fx.play_subtle_alert_chime()

    # Verify volume scaling
    mode_manager.set_mode("work")
    assert mode_manager.get_volume_scale() == 1.0

    mode_manager.set_mode("study")
    assert mode_manager.get_volume_scale() == 0.35

    mode_manager.set_mode("deep_focus")
    assert mode_manager.get_volume_scale() == 0.0

    mode_manager.set_mode("work")


# =====================================================================
# 5. SAFETY REGISTRY & TIER 0 UTILITY TOOLS TESTS
# =====================================================================

def test_ambient_tools_registered_in_safety_registry():
    status_tool = registry.get("get_ambient_status")
    assert status_tool is not None
    assert status_tool.tier == 0

    mode_tool = registry.get("set_assistant_mode")
    assert mode_tool is not None
    assert mode_tool.tier == 0

    # Test executions
    stat = get_ambient_status()
    assert stat["status"] == "success"
    assert stat["active_mode"] in ["work", "study", "chill", "deep_focus"]
    assert "cpu_percent" in stat

    res_set = set_assistant_mode("chill")
    assert res_set["mode"] == "chill"
    assert mode_manager.get_current_mode() == AssistantMode.CHILL

    mode_manager.set_mode("work")
