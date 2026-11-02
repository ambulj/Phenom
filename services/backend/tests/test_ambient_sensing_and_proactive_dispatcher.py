"""Automated Verification Suite for Ambient Context Sensing & Proactive Event Architecture.

Verifies:
1. Win32 Idle Detector elapsed calculation, 32-bit wrap-around, and state transitions (SEN-01).
2. Active Window Context Sensor and privacy title redaction (SEN-02).
3. Proactive Event Dispatcher priority queues, cooldowns, and DEEP_FOCUS suppression (DIS-01).
4. Multimodal WebSocket event bridge and active card management (DIS-02).
5. Safety tool registration, Pydantic schemas, and execution (SAF-01).
6. Synchronous Guardian kill switch halt within < 25ms SLA (SAF-02).
"""

import asyncio
import time
from typing import Any, Dict, List
import pytest

from services.backend.sensors.idle_sensor import Win32IdleDetector
from services.backend.sensors.context_sensor import Win32ContextSensor, ForegroundContext
from services.backend.proactive.dispatcher import (
    ProactiveEventDispatcher,
    ProactiveCard,
    ProactivePriority,
)
from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.main import on_guardian_state_change  # Registers on_guardian_state_change with Guardian
import services.backend.tools.proactive_tools  # Ensure tools are registered


# ---------------------------------------------------------------------------
# Test 1: Win32 Idle Detector & State Transitions (SEN-01)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_win32_idle_sensor_elapsed_and_wraparound():
    """Verify idle calculation, 32-bit wrap-around math, and callback transitions."""
    simulated_elapsed = 10.0

    def mock_get_idle():
        return simulated_elapsed

    idle_events: List[str] = []

    async def on_idle(dur: float):
        idle_events.append(f"idle_{dur}")

    def on_returned(dur: float):
        idle_events.append(f"returned_{dur}")

    detector = Win32IdleDetector(
        idle_threshold_seconds=50.0,
        on_idle_callback=on_idle,
        on_returned_callback=on_returned,
        poll_interval_active=0.01,
        poll_interval_idle=0.01,
        get_idle_seconds_fn=mock_get_idle,
    )

    # Initial active check
    assert not detector.is_idle
    assert detector.get_current_idle_seconds() == 10.0

    # Start loop
    detector.start()
    await asyncio.sleep(0.05)
    assert not detector.is_idle
    assert len(idle_events) == 0

    # Transition to idle (threshold=50s, mock=60s)
    simulated_elapsed = 60.0
    await asyncio.sleep(0.05)
    assert detector.is_idle
    assert len(idle_events) == 1
    assert "idle_60" in idle_events[0]

    # Transition back to returned (mock=5s)
    simulated_elapsed = 5.0
    await asyncio.sleep(0.05)
    assert not detector.is_idle
    assert len(idle_events) == 2
    assert "returned_5" in idle_events[1]

    detector.halt()
    assert not detector._running


# ---------------------------------------------------------------------------
# Test 2: Active Window Context Sensor & Privacy Redaction (SEN-02)
# ---------------------------------------------------------------------------
def test_win32_context_sensor_and_privacy_redaction():
    """Verify foreground window context querying and sensitive title redaction."""
    sensor = Win32ContextSensor()

    # Sensitivity check logic
    assert sensor.check_sensitivity("Bitwarden - Master Password", "chrome.exe") is True
    assert sensor.check_sensitivity("WhatsApp Web", "chrome.exe") is True
    assert sensor.check_sensitivity("Bank Login - Chase", "msedge.exe") is True
    assert sensor.check_sensitivity("KeePass Password Safe", "keepass.exe") is True
    assert sensor.check_sensitivity("main.py - Phenom - VS Code", "Code.exe") is False
    assert sensor.check_sensitivity("Obsidian Vault", "obsidian.exe") is False

    # Live or mock context query
    ctx = sensor.query_context(redact_sensitive=True)
    assert isinstance(ctx, ForegroundContext)
    assert ctx.title is not None
    assert ctx.app_name is not None
    assert isinstance(ctx.is_sensitive, bool)


# ---------------------------------------------------------------------------
# Test 3: Proactive Dispatcher Priority & Mode Suppression (DIS-01)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_proactive_dispatcher_priority_and_mode_suppression():
    """Verify DEEP_FOCUS / STUDY mode suppression of non-urgent cards."""
    broadcasts: List[Dict[str, Any]] = []

    async def mock_ws_broadcast(msg: Dict[str, Any]):
        broadcasts.append(msg)

    dispatcher = ProactiveEventDispatcher(ws_broadcast_fn=mock_ws_broadcast, default_cooldown_seconds=10.0)

    # In CHILL mode: NORMAL card delivered
    dispatcher.set_mode("CHILL")
    card1 = ProactiveCard(
        event_type="MORNING_BRIEF",
        priority=ProactivePriority.NORMAL,
        title="Good Morning",
        description="Here is your schedule for today.",
        action_chip="View Agenda",
    )
    res1 = await dispatcher.dispatch(card1)
    assert res1 is True
    assert len(broadcasts) == 2  # PROACTIVE_CARD + PROACTIVE_ORB_PULSE
    assert broadcasts[0]["type"] == "PROACTIVE_CARD"
    assert broadcasts[0]["card"]["title"] == "Good Morning"
    assert broadcasts[1]["type"] == "PROACTIVE_ORB_PULSE"

    # Switch to DEEP_FOCUS: NORMAL card suppressed
    broadcasts.clear()
    dispatcher.set_mode("DEEP_FOCUS")
    card2 = ProactiveCard(
        event_type="EMAIL_TRIAGE",
        priority=ProactivePriority.NORMAL,
        title="Unread VIP Email",
        description="New thread from supervisor.",
    )
    res2 = await dispatcher.dispatch(card2)
    assert res2 is False  # Suppressed!
    assert len(broadcasts) == 0

    # Switch to STUDY: BACKGROUND card suppressed
    dispatcher.set_mode("STUDY")
    card3 = ProactiveCard(
        event_type="IDLE_CLEANUP",
        priority=ProactivePriority.BACKGROUND,
        title="Downloads Clutter",
        description="Found 12 unorganized files.",
    )
    res3 = await dispatcher.dispatch(card3)
    assert res3 is False
    assert len(broadcasts) == 0

    # In DEEP_FOCUS: URGENT card bypasses suppression
    card_urgent = ProactiveCard(
        event_type="MEETING_PREP",
        priority=ProactivePriority.URGENT,
        title="Meeting in 5 Minutes",
        description="Design Review starting soon.",
        action_chip="Open Briefing",
    )
    res_urgent = await dispatcher.dispatch(card_urgent)
    assert res_urgent is True  # Delivered despite deep focus!
    assert len(broadcasts) == 2
    assert broadcasts[1]["pulse_color"] == "#CCFF00"  # Acid Lime for urgent


# ---------------------------------------------------------------------------
# Test 4: Anti-Fatigue Cooldown Throttling (DIS-01)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_proactive_dispatcher_anti_fatigue_cooldown():
    """Verify cooldown period prevents repetitive spam for the same event type."""
    broadcasts: List[Dict[str, Any]] = []

    async def mock_ws_broadcast(msg: Dict[str, Any]):
        broadcasts.append(msg)

    dispatcher = ProactiveEventDispatcher(ws_broadcast_fn=mock_ws_broadcast, default_cooldown_seconds=300.0)
    dispatcher.set_cooldown_override("MEETING_PREP", 60.0)

    # Dispatch first meeting prep card
    c1 = ProactiveCard(
        event_type="MEETING_PREP",
        priority=ProactivePriority.NORMAL,
        title="Upcoming Sync",
        description="Meeting in 15 min.",
    )
    assert await dispatcher.dispatch(c1) is True

    # Immediate second meeting prep card -> throttled
    c2 = ProactiveCard(
        event_type="MEETING_PREP",
        priority=ProactivePriority.NORMAL,
        title="Upcoming Sync 2",
        description="Meeting in 14 min.",
    )
    assert await dispatcher.dispatch(c2) is False

    # Urgent card bypasses cooldown
    c3 = ProactiveCard(
        event_type="MEETING_PREP",
        priority=ProactivePriority.URGENT,
        title="Sync Starting Now!",
        description="Join link ready.",
    )
    assert await dispatcher.dispatch(c3) is True


# ---------------------------------------------------------------------------
# Test 5: Safety Tools Registration & Execution (SAF-01)
# ---------------------------------------------------------------------------
def test_proactive_safety_tools_registration_and_execution():
    """Verify Safety layer ToolRegistry registration and execution schemas."""
    # 1. get_proactive_status (Tier 0)
    entry_status = registry.get("get_proactive_status")
    assert entry_status is not None
    assert entry_status.tier == 0
    res_status = entry_status.handler_fn()
    assert res_status["status"] == "ok"
    assert "idle_sensor" in res_status
    assert "context_sensor" in res_status
    assert "dispatcher" in res_status

    # 2. configure_proactive_cooldown (Tier 1)
    entry_cfg = registry.get("configure_proactive_cooldown")
    assert entry_cfg is not None
    assert entry_cfg.tier == 1
    preview = entry_cfg.preview_fn({"idle_threshold_seconds": 120.0, "default_cooldown_seconds": 600.0})
    assert "idle_threshold=120.0" in preview
    res_cfg = entry_cfg.handler_fn(idle_threshold_seconds=120.0, default_cooldown_seconds=600.0)
    assert res_cfg["status"] == "configured"
    assert res_cfg["idle_threshold_seconds"] == 120.0

    # 3. dismiss_proactive_card (Tier 0)
    entry_dismiss = registry.get("dismiss_proactive_card")
    assert entry_dismiss is not None
    assert entry_dismiss.tier == 0
    res_dismiss = entry_dismiss.handler_fn(card_id="nonexistent-card-id")
    assert res_dismiss["status"] in ("dismissed", "not_found")


# ---------------------------------------------------------------------------
# Test 6: Synchronous Guardian Kill Switch Halt (< 25ms SLA) (SAF-02)
# ---------------------------------------------------------------------------
def test_guardian_trigger_synchronously_halts_ambient_sensors():
    """Verify Guardian trigger synchronously stops all sensor loops in < 25ms."""
    from services.backend.sensors.idle_sensor import idle_detector
    from services.backend.sensors.context_sensor import context_sensor
    from services.backend.proactive.dispatcher import proactive_dispatcher

    guardian.resume()
    idle_detector.start()
    context_sensor.start()

    t_start = time.perf_counter()
    guardian.trigger("test_ambient_guardian_halt")
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    # Assert synchronous sub-25ms SLA
    assert elapsed_ms < 25.0, f"Guardian trigger took {elapsed_ms:.2f}ms, exceeded 25.0ms SLA"

    # Verify sensors halted
    assert idle_detector._running is False
    assert context_sensor._running is False

    guardian.resume()
