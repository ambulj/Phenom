"""Unit test suite for Sub-100ms Reflex Reaction Engine & Adaptive Jarvis Commentary (Milestone 51 Phase 2).

Tests:
1. JarvisCommentator word count constraint (<= 20 words) and persona phrasing.
2. ReflexRule matching hierarchy, severity filtering, and priority ordering.
3. Sub-100ms evaluation latency benchmark across 100 consecutive events.
4. Category cooldown gates and suppression state machine.
5. SuggestedAction generation and safety tier metadata.
6. Registered reflex reaction safety tools.
"""

import time
import pytest

from services.backend.schemas.reflex_events import (
    ReflexEvent,
    ReflexEventType,
    ReflexSeverity,
    VisualCueDetails,
    ToastNotificationDetails,
)
from services.backend.reflex.jarvis_commentator import JarvisCommentator
from services.backend.reflex.reflex_engine import (
    ReflexEngine,
    ReflexRule,
    ReflexReaction,
    SuggestedAction,
)
from services.backend.tools.reflex_reaction_tools import (
    evaluate_reflex_reaction,
    dispatch_jarvis_commentary,
    configure_reflex_cooldowns,
)


def test_jarvis_commentator_word_limit_and_style():
    """Verify Jarvis commentary is witty and strictly constrained to <= 20 words."""
    commentator = JarvisCommentator()

    # Test build failure event
    ev_build = ReflexEvent(
        event_type=ReflexEventType.BUILD_FAILED,
        severity=ReflexSeverity.CRITICAL,
        visual_details=VisualCueDetails(
            window_title="VS Code",
            process_name="Code.exe",
            raw_text="src/index.ts(42,10): error TS2304: Cannot find name 'int'",
        )
    )
    text_build, count_build = commentator.format_commentary(ev_build)
    assert count_build <= 20
    assert "sir" in text_build.lower()

    # Test test pass event
    ev_pass = ReflexEvent(
        event_type=ReflexEventType.TESTS_PASSED,
        severity=ReflexSeverity.SUCCESS,
    )
    text_pass, count_pass = commentator.format_commentary(ev_pass)
    assert count_pass <= 20
    assert "sir" in text_pass.lower()

    # Test long artificial sentence truncation
    long_msg = "This is a remarkably verbose commentary string that easily exceeds twenty words and would definitely cause an overflow if not properly truncated by the engine."
    condensed = commentator.condense_text(long_msg, max_words=20)
    assert commentator.count_words(condensed) <= 20


def test_reflex_rule_priority_and_matching():
    """Verify rule priority ordering and predicate evaluation."""
    engine = ReflexEngine()

    # Rules should be ordered by priority descending
    priorities = [r.priority for r in engine.rules]
    assert priorities == sorted(priorities, reverse=True)

    # Low severity event should not match critical rule
    ev_info = ReflexEvent(
        event_type=ReflexEventType.BUILD_FAILED,
        severity=ReflexSeverity.INFO,
    )
    # The default rule requires CRITICAL, so rule_build_failed should not match
    crit_rule = next(r for r in engine.rules if r.rule_id == "rule_build_failed")
    assert crit_rule.matches(ev_info) is False


def test_sub_100ms_evaluation_latency():
    """Verify 100-event evaluation benchmark strictly satisfies < 100ms SLA (target < 10ms)."""
    engine = ReflexEngine()
    engine.set_rule_cooldown("rule_build_failed", 0.0)

    ev = ReflexEvent(
        event_type=ReflexEventType.BUILD_FAILED,
        severity=ReflexSeverity.CRITICAL,
        visual_details=VisualCueDetails(
            window_title="Terminal",
            process_name="pwsh.exe",
            raw_text="error TS2322: Type 'number' is not assignable to type 'string'",
        )
    )

    latencies = []
    for _ in range(100):
        rx, lat_ms = engine.evaluate_event(ev)
        assert rx is not None
        latencies.append(lat_ms)

    mean_lat = sum(latencies) / len(latencies)
    max_lat = max(latencies)

    # SLA requirement < 100ms, typical < 5ms
    assert mean_lat < 10.0, f"Mean latency {mean_lat:.2f}ms exceeded 10ms"
    assert max_lat < 100.0, f"Max latency {max_lat:.2f}ms exceeded 100ms SLA"


def test_cooldown_and_suppression():
    """Verify category cooldown gates repeated alerts."""
    engine = ReflexEngine()
    engine.set_rule_cooldown("rule_error_dialog", 5.0)

    ev_err = ReflexEvent(
        event_type=ReflexEventType.ERROR_DIALOG,
        severity=ReflexSeverity.CRITICAL,
        toast_details=ToastNotificationDetails(
            app_name="Docker",
            title="Fatal Error",
            message="Daemon crashed",
        )
    )

    # First event: allowed
    rx1, _ = engine.evaluate_event(ev_err)
    assert rx1 is not None
    assert rx1.is_suppressed is False

    # Second event immediately: suppressed
    rx2, _ = engine.evaluate_event(ev_err)
    assert rx2 is not None
    assert rx2.is_suppressed is True
    assert "in cooldown" in rx2.suppression_reason

    # Reset cooldown: allowed again
    engine.set_rule_cooldown("rule_error_dialog", 0.0)
    rx3, _ = engine.evaluate_event(ev_err)
    assert rx3 is not None
    assert rx3.is_suppressed is False


def test_suggested_action_generation():
    """Verify build failure generates pre-staged SuggestedAction with tier classification."""
    engine = ReflexEngine()
    engine.set_rule_cooldown("rule_build_failed", 0.0)

    ev = ReflexEvent(
        event_type=ReflexEventType.BUILD_FAILED,
        severity=ReflexSeverity.CRITICAL,
        visual_details=VisualCueDetails(
            raw_text="SyntaxError: unexpected token in file main.py",
        )
    )

    rx, _ = engine.evaluate_event(ev)
    assert rx is not None
    assert rx.suggested_action is not None
    assert rx.suggested_action.tool_name == "read_file"
    assert rx.suggested_action.tier in (0, 1)
    assert len(rx.suggested_action.description) > 0


def test_registered_reflex_reaction_tools():
    """Verify registered reflex reaction tools operate cleanly."""
    # Test reaction evaluation tool
    res_rx = evaluate_reflex_reaction(
        event_type="TESTS_PASSED",
        severity="SUCCESS",
        raw_text="30 passed in 1.2s",
        process_name="pytest.exe"
    )
    assert res_rx["matched"] is True
    assert res_rx["reaction"]["voice_commentary"] != ""
    assert res_rx["reaction"]["word_count"] <= 20

    # Test voice commentary tool
    res_voice = dispatch_jarvis_commentary(
        event_type="BUILD_FAILED",
        diagnostic="TypeScript compilation failed",
        severity="CRITICAL"
    )
    assert res_voice["word_count"] <= 20
    assert res_voice["valid_limit"] is True

    # Test cooldown configuration tool
    res_cd = configure_reflex_cooldowns(
        rule_id="rule_build_failed",
        cooldown_seconds=12.5
    )
    assert res_cd["success"] is True
    assert res_cd["new_cooldown_seconds"] == 12.5
