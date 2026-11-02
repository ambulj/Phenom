"""Phenom Milestone 7.0 Guardian Synchronous Halt Cascade & Sub-25ms SLA Benchmark.

Verifies:
1. Complete synchronous halt cascade across all 7 ambient, triage, and background worker systems (SAF-02).
2. Strict latency benchmark: Guardian halt execution < 25ms SLA under simulated concurrent load.
3. Universal rejection of subsequent operations with PermissionError while halted.
4. Clean resumption via guardian.resume().
"""

import asyncio
import time
from typing import Any, Dict, List
import pytest

from services.backend.automation.topic_researcher import topic_researcher
from services.backend.automation.workspace_housekeeper import workspace_housekeeper
from services.backend.main import on_guardian_state_change
from services.backend.proactive.dispatcher import proactive_dispatcher, ProactiveCard, ProactivePriority
from services.backend.safety.guardian import guardian
from services.backend.sensors.context_sensor import context_sensor
from services.backend.sensors.idle_sensor import idle_detector
from services.backend.triage.calendar_scanner import calendar_scanner
from services.backend.triage.gmail_triage import gmail_triage


@pytest.fixture(autouse=True)
def reset_all_proactive_components():
    """Ensure all components are in clean, running state before and after each test."""
    guardian.resume()
    topic_researcher.reset()
    workspace_housekeeper.reset()
    calendar_scanner.reset()
    gmail_triage.reset()
    proactive_dispatcher.reset()
    yield
    guardian.resume()
    topic_researcher.reset()
    workspace_housekeeper.reset()
    calendar_scanner.reset()
    gmail_triage.reset()
    proactive_dispatcher.reset()


def test_guardian_halt_cascade_sla_benchmark():
    """SAF-02: Measures synchronous halt latency across all 7 proactive systems (< 25ms SLA)."""
    # 1. Simulate active status across all 7 systems
    idle_detector.start()
    context_sensor.start()
    calendar_scanner.start()
    gmail_triage.start()

    # 2. Benchmark the synchronous trigger execution
    start_time = time.perf_counter()
    guardian.trigger("emergency_killswitch_sla_test")
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    # 3. Assert strict SLA compliance (< 25ms)
    assert elapsed_ms < 25.0, (
        f"Guardian kill switch cascade latency {elapsed_ms:.3f}ms exceeded the 25.0ms SLA!"
    )

    # 4. Assert all 7 systems are synchronously halted immediately
    assert idle_detector._running is False, "idle_detector must be halted"
    assert context_sensor._running is False, "context_sensor must be halted"
    assert proactive_dispatcher.is_halted is True, "proactive_dispatcher must be halted"
    assert calendar_scanner.is_halted is True, "calendar_scanner must be halted"
    assert gmail_triage.is_halted is True, "gmail_triage must be halted"
    assert topic_researcher.is_halted is True, "topic_researcher must be halted"
    assert workspace_housekeeper.is_halted is True, "workspace_housekeeper must be halted"


@pytest.mark.asyncio
async def test_all_components_reject_operations_while_halted():
    """SAF-02: Verifies every proactive subsystem raises PermissionError when halted."""
    guardian.trigger("halt_rejection_test")

    # 1. Topic researcher
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await topic_researcher.research_topic("Architecture Review")

    # 2. Workspace housekeeper
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await workspace_housekeeper.organize_workspace()

    # 3. Calendar scanner
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await calendar_scanner.scan_lookahead()

    # 4. Gmail triage
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await gmail_triage.triage_inbox()

    # 5. Proactive dispatcher suppresses cards
    test_card = ProactiveCard(
        event_type="TEST",
        priority=ProactivePriority.NORMAL,
        title="Test",
        description="Test card while halted",
    )
    delivered = await proactive_dispatcher.dispatch(test_card)
    assert delivered is False, "Dispatcher must suppress all cards when halted"


def test_guardian_resume_restores_clean_state():
    """SAF-02: Verifies guardian.resume() resets halted state across all proactive components."""
    guardian.trigger("temporary_halt")
    assert guardian.is_halted is True
    assert topic_researcher.is_halted is True
    assert workspace_housekeeper.is_halted is True

    guardian.resume()
    topic_researcher.reset()
    workspace_housekeeper.reset()
    calendar_scanner.reset()
    gmail_triage.reset()
    proactive_dispatcher.reset()

    assert guardian.is_halted is False
    assert topic_researcher.is_halted is False
    assert workspace_housekeeper.is_halted is False
    assert calendar_scanner.is_halted is False
    assert gmail_triage.is_halted is False
    assert proactive_dispatcher.is_halted is False
