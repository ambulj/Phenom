"""End-to-end integration and Guardian kill switch SLA benchmark for Neural Perception & Active Desktop Reflexes (Milestone 51 Phase 5).

Tests:
1. End-to-end reflex flow: Frame sampling -> ReflexEvent -> ReflexReaction -> Proposal -> Telemetry.
2. Telegram alert formatting and strict Rule 11 secret redaction.
3. Telegram alert debounce state machine.
4. Registered reflex telemetry safety tools.
5. 100-cycle Guardian kill switch emergency halt SLA benchmark (< 25.0ms) under active reflex load.
"""

import time
import pytest

from services.backend.schemas.reflex_events import (
    ReflexEvent,
    ReflexEventType,
    ReflexSeverity,
    VisualCueDetails,
)
from services.backend.schemas.semantic_focus import WindowContext, BoundingRect
from services.backend.reflex import (
    visual_sentinel,
    reflex_engine,
    contextual_anchor_manager,
    action_suggester,
    telegram_alert_stream,
)
from services.backend.safety.guardian import guardian
from services.backend.tools.reflex_telemetry_tools import (
    broadcast_reflex_telemetry,
    dispatch_telegram_reflex_alert,
)


def test_end_to_end_reflex_pipeline():
    """Verify full reflex chain from perceptual frame capture to telemetry broadcast."""
    # 1. Set active mock window
    mock_ctx = WindowContext(
        hwnd=9001,
        title="main.py - Phenom - Visual Studio Code",
        process_name="Code.exe",
        pid=1234,
        bounding_rect=BoundingRect(left=0, top=0, right=1920, bottom=1080),
    )
    contextual_anchor_manager.tracker.set_simulated_window(mock_ctx)

    # 2. Process frame containing a TypeScript build failure
    ts_error_frame = "src/main.ts(20,5): error TS2322: Type 'string' is not assignable to type 'number'."
    event, lat_sentinel = visual_sentinel.process_frame(
        image_or_buffer="hash_test_1",
        extracted_text=ts_error_frame,
        window_title="main.py - Phenom - Visual Studio Code",
        process_name="Code.exe",
        force_process=True,
    )
    assert event is not None
    assert event.event_type == ReflexEventType.BUILD_FAILED

    # 3. Evaluate reaction in engine (<100ms)
    reaction, lat_rx = reflex_engine.evaluate_event(event)
    assert reaction is not None
    assert reaction.word_count <= 20
    assert lat_rx < 100.0

    # 4. Resolve anchor & proposals
    anchor = contextual_anchor_manager.resolve_anchor()
    assert anchor.active_file == "main.py"
    proposals = action_suggester.generate_proposals(anchor=anchor, event=event)
    assert len(proposals) >= 1

    # 5. Verify telemetry gather
    telemetry = broadcast_reflex_telemetry(include_proposals=True)
    assert telemetry["active_app"] == "Code.exe"
    assert telemetry["active_file"] == "main.py"
    assert len(telemetry["proposals"]) >= 1


def test_telegram_alert_formatting_and_redaction():
    """Verify Telegram alert markdown formatting and Rule 11 secret scrubbing."""
    stream = telegram_alert_stream
    stream.debounce_seconds = 0.0  # Disable debounce for test

    event_with_secret = ReflexEvent(
        event_type=ReflexEventType.BUILD_FAILED,
        severity=ReflexSeverity.CRITICAL,
        visual_details=VisualCueDetails(
            window_title="Code.exe",
            process_name="Code.exe",
            raw_text="Build error: secret_key = 'sk-1234567890abcdef1234567890abcdef' failed validation",
        )
    )

    alert = stream.format_alert(event_with_secret)
    assert alert is not None
    assert "🚨 *CRITICAL REFLEX ALERT*" in alert.text
    # Rule 11 credential protection
    assert "sk-1234567890" not in alert.text
    assert "[REDACTED_OPENAI_KEY]" in alert.text or "[REDACTED_SECRET]" in alert.text or "[REDACTED" in alert.text
    assert len(alert.inline_buttons) == 2


def test_telegram_alert_debouncing():
    """Verify rapid repeated Telegram alerts are throttled by debounce timer."""
    stream = telegram_alert_stream
    stream.debounce_seconds = 10.0

    ev = ReflexEvent(
        event_type=ReflexEventType.TERMINAL_COMPLETED,
        severity=ReflexSeverity.SUCCESS,
        visual_details=VisualCueDetails(raw_text="Deploy finished successfully"),
    )

    alert1 = stream.format_alert(ev)
    assert alert1 is not None

    # Immediate second alert must be debounced
    alert2 = stream.format_alert(ev)
    assert alert2 is None


def test_registered_reflex_telemetry_tools():
    """Verify registered reflex telemetry and alert tools operate cleanly."""
    # Test broadcast tool
    res_bcast = broadcast_reflex_telemetry(include_proposals=True)
    assert "active_app" in res_bcast
    assert "cpu_percent" in res_bcast

    # Test telegram dispatch tool
    res_tg = dispatch_telegram_reflex_alert(
        event_type="BUILD_FAILED",
        severity="CRITICAL",
        raw_text="TypeScript compilation failed on 2 files",
        process_name="Code.exe"
    )
    assert "success" in res_tg


def test_guardian_kill_switch_sla_under_reflex_load():
    """Benchmark: 100 consecutive Guardian kill switch emergency halts under active reflex load.
    
    Hard invariant: Max halt latency must be strictly < 25.0ms.
    """
    halt_latencies = []

    for i in range(100):
        # Reset guardian
        guardian.resume()
        assert guardian.is_halted is False

        # Simulate concurrent reflex sampling
        visual_sentinel.process_frame(
            image_or_buffer=f"hash_{i}",
            extracted_text=f"Progress step {i}",
            force_process=(i % 5 == 0)
        )

        # Trigger emergency halt and benchmark duration
        t0 = time.perf_counter()
        guardian.trigger(f"Benchmark iteration {i}")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert guardian.is_halted is True
        halt_latencies.append(elapsed_ms)

    # Cleanup guardian state
    guardian.resume()

    mean_latency = sum(halt_latencies) / len(halt_latencies)
    max_latency = max(halt_latencies)

    # Strict SLA verification
    assert max_latency < 25.0, f"Max Guardian halt {max_latency:.3f}ms breached 25.0ms hard SLA!"
    assert mean_latency < 1.0, f"Mean Guardian halt {mean_latency:.3f}ms exceeded 1.0ms target!"
