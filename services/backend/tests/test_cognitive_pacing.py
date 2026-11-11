"""Unit & Safety Tests for Cognitive Load Balancer & Attentional Pacing (Milestone 26 Phase 4)."""

import pytest
import time
from services.backend.pacing.cognitive_load_tracker import (
    CognitiveLoadTracker,
    Rule8ViolationError,
)
from services.backend.pacing.attentional_pacer import AttentionalPacer
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.cognitive_pacing_tools  # Ensure registered


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_cognitive_load_tracker_idle_and_burst():
    tracker = CognitiveLoadTracker()
    # Idle
    state_idle = tracker.get_state()
    assert state_idle.attentional_state == "IDLE_EXPLORING"
    assert state_idle.cognitive_load_score < 0.35

    # Burst of activity
    for _ in range(60):
        tracker.record_interaction("KEYSTROKE")
    for w in ["Code", "Terminal", "Doc"]:
        tracker.record_interaction("CLICK", window_title=w)

    state_burst = tracker.get_state()
    assert state_burst.cognitive_load_score >= 0.75
    assert state_burst.attentional_state == "DEEP_FLOW"
    assert state_burst.interaction_rate_per_min >= 60


def test_attentional_pacer_deep_flow_deferral():
    tracker = CognitiveLoadTracker()
    for _ in range(60):
        tracker.record_interaction("KEYSTROKE")
    pacer = AttentionalPacer(tracker=tracker)

    # Standard alert during deep flow should be deferred
    dec = pacer.evaluate_and_pace("Daily Digest", "Here is your morning update", priority="STANDARD_PROACTIVE")
    assert dec.decision == "DEFERRED_TO_QUEUE"
    assert dec.user_attentional_state == "DEEP_FLOW"
    assert len(pacer.get_deferred_queue()) == 1


def test_attentional_pacer_critical_safety_override():
    tracker = CognitiveLoadTracker()
    for _ in range(60):
        tracker.record_interaction("KEYSTROKE")
    pacer = AttentionalPacer(tracker=tracker)

    # Critical alert punches through regardless of load
    dec = pacer.evaluate_and_pace("High Temperature", "GPU throttling detected", priority="CRITICAL_SAFETY")
    assert dec.decision == "DISPATCH_IMMEDIATELY"
    assert "Rule 1 / Rule 3 invariant" in dec.rationale


def test_flush_deferred_queue():
    tracker = CognitiveLoadTracker()
    for _ in range(60):
        tracker.record_interaction("KEYSTROKE")
    pacer = AttentionalPacer(tracker=tracker)

    pacer.evaluate_and_pace("Note 1", "Body 1")
    pacer.evaluate_and_pace("Note 2", "Body 2")
    assert len(pacer.get_deferred_queue()) == 2

    flushed = pacer.flush_deferred_queue()
    assert len(flushed) == 2
    assert len(pacer.get_deferred_queue()) == 0


def test_rule_8_enforcement_pacing():
    tracker = CognitiveLoadTracker()
    pacer = AttentionalPacer(tracker=tracker)

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        tracker.record_interaction("checkout_click")

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        pacer.evaluate_and_pace("Payment Reminder", "Please enter credit card info")

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        pacer.evaluate_and_pace("Order", "place_order_checkout")


def test_guardian_kill_switch_sla_pacing():
    tracker = CognitiveLoadTracker()
    pacer = AttentionalPacer(tracker=tracker)
    guardian.trigger(reason="Safety test")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        tracker.get_state()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 25.0, f"Guardian SLA exceeded: {elapsed_ms:.4f}ms"

    t1 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        pacer.evaluate_and_pace("Alert", "Test")
    elapsed_ms2 = (time.perf_counter() - t1) * 1000.0
    assert elapsed_ms2 < 25.0, f"Guardian SLA exceeded: {elapsed_ms2:.4f}ms"


def test_tool_registry_cognitive_pacing_tools():
    # 1. get_cognitive_load_state (Tier 0)
    tool_get = registry.get("get_cognitive_load_state")
    assert tool_get is not None
    assert tool_get.tier == 0
    res_get = tool_get.handler_fn()
    assert "cognitive_state" in res_get
    assert "deferred_queue_length" in res_get

    # 2. pace_notification_dispatch (Tier 0)
    tool_pace = registry.get("pace_notification_dispatch")
    assert tool_pace is not None
    assert tool_pace.tier == 0
    prev_pace = tool_pace.preview_fn({"title": "Test Alert", "priority": "STANDARD_PROACTIVE"})
    assert "Test Alert" in prev_pace

    res_pace = tool_pace.handler_fn(
        title="Weekly Summary",
        body="Summary ready",
        priority="STANDARD_PROACTIVE",
    )
    assert res_pace["decision"] in ("DISPATCH_IMMEDIATELY", "DEFERRED_TO_QUEUE")

    # 3. flush_deferred_notifications (Tier 1)
    tool_flush = registry.get("flush_deferred_notifications")
    assert tool_flush is not None
    assert tool_flush.tier == 1
    res_flush = tool_flush.handler_fn()
    assert res_flush["status"] == "FLUSHED"
