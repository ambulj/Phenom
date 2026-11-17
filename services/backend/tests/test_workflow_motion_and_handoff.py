"""
Unit tests for Observable Motion Choreography & Dual Handoff Briefing (Phase 50-05)
Tests:
1. Smooth cubic Bezier cursor trajectory calculation at 1.2x human speed (WKF-05.1)
2. Target bounding box halo formulation before click dispatch (WKF-05.2)
3. Sub-10ms low-level human takeover displacement detection (WKF-05.3)
4. Spoken witty Jarvis debrief strictly <= 25 words (WKF-05.4)
5. Rich Telegram companion card markdown formatting (WKF-05.4)
6. Tool registry verification (Tier 1 motion, Tier 0 handoff)
"""

import pytest
import time
from services.backend.desktop.observable_motion_driver import (
    ObservableMotionDriver,
    MotionExecutionResult,
    observable_motion_driver,
)
from services.backend.workflows.dual_handoff_briefing import (
    DualHandoffGenerator,
    DualHandoffBriefing,
    dual_handoff_generator,
)
from services.backend.tools.workflow_handoff_tools import (
    drive_observable_motion,
    generate_dual_handoff_briefing,
)
from services.backend.safety.registry import registry


def test_bezier_motion_1_2x_speed_scaling():
    """Verify cubic Bezier curve generation properly scales to 1.2x human speed."""
    driver = ObservableMotionDriver()
    start_pos = (100, 100)
    target_pos = (800, 600)
    bbox = (780, 580, 40, 40)

    res = driver.plan_and_drive_motion(
        start_pos=start_pos,
        target_pos=target_pos,
        target_name="Save Document Button",
        bounding_box=bbox
    )

    assert res.success is True
    assert res.speed_factor == 1.2
    assert res.waypoint_count >= 10
    assert res.duration_ms > 0.0
    assert res.human_takeover_triggered is False


def test_target_halo_emission_and_bounds():
    """Verify target halo overlay bounding box is correctly emitted."""
    driver = ObservableMotionDriver()
    start_pos = (50, 50)
    target_pos = (350, 450)
    bbox = (330, 430, 60, 30)

    res = driver.plan_and_drive_motion(
        start_pos=start_pos,
        target_pos=target_pos,
        target_name="Download PDF",
        bounding_box=bbox
    )

    halo = res.target_halo
    assert halo.target_name == "Download PDF"
    assert halo.bounding_box == (330, 430, 60, 30)
    assert halo.color_hex == "#00FFCC"
    assert halo.duration_ms >= 300


def test_human_takeover_hook_benchmark_under_10ms_sla():
    """Verify physical operator mouse displacement >15px yields control in < 10ms."""
    driver = ObservableMotionDriver()
    start_pos = (200, 200)
    target_pos = (500, 500)
    bbox = (480, 480, 40, 40)

    # Simulate physical mouse divergence of 60px (>15px threshold)
    diverged_physical_pos = (260, 200)

    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        res = driver.plan_and_drive_motion(
            start_pos=start_pos,
            target_pos=target_pos,
            target_name="Cancel Button",
            bounding_box=bbox,
            physical_cursor_pos=diverged_physical_pos
        )
        lat = (time.perf_counter() - t0) * 1000.0
        latencies.append(lat)
        assert res.human_takeover_triggered is True
        assert res.success is False

    avg_lat = sum(latencies) / len(latencies)
    assert avg_lat < 10.0  # SLA < 10ms


def test_dual_handoff_briefing_word_count_limit():
    """Verify spoken voice summary strictly complies with <= 25 words constraint."""
    gen = DualHandoffGenerator()

    # Success briefing
    b_success = gen.generate_briefing(
        dag_id="dag_test_01",
        goal="Extract stock research and summarize to Obsidian",
        step_count=5,
        success=True,
        duration_s=8.4
    )

    assert b_success.success is True
    assert b_success.word_count <= 25
    words_actual = len(b_success.spoken_summary.split())
    assert words_actual <= 25
    assert "sir" in b_success.spoken_summary.lower()

    # Diverged briefing
    b_partial = gen.generate_briefing(
        dag_id="dag_test_02",
        goal="Deploy code changes to production",
        step_count=3,
        success=False,
        duration_s=4.1
    )

    assert b_partial.success is False
    assert b_partial.word_count <= 25
    assert len(b_partial.spoken_summary.split()) <= 25


def test_telegram_card_markdown_formatting():
    """Verify Telegram companion card formats rich Markdown with metrics and ASCII."""
    gen = DualHandoffGenerator()
    briefing = gen.generate_briefing(
        dag_id="dag_sync_888",
        goal="Synchronize project sprint tasks",
        step_count=6,
        success=True,
        duration_s=12.3,
        screenshots_attached=2
    )

    card = briefing.telegram_card_markdown
    assert "*Phenom Autonomous Workflow Debrief*" in card
    assert "Synchronize project sprint tasks" in card
    assert "✅ COMPLETED" in card
    assert "12.3s" in card
    assert "6" in card
    assert "[UNTRUSTED_TAINT] Isolated" in card
    assert "2 attached" in card
    assert briefing.spoken_summary in card


def test_motion_and_handoff_tool_registrations():
    """Verify tool definitions, argument schemas, and preview generators."""
    t_motion = registry.get("drive_observable_motion")
    assert t_motion is not None
    assert t_motion.tier == 1
    assert callable(t_motion.preview_fn)
    preview = t_motion.preview_fn({"target_name": "Submit", "target_x": 400, "target_y": 500})
    assert "Submit" in preview
    assert "1.2x" in preview

    t_briefing = registry.get("generate_dual_handoff_briefing")
    assert t_briefing is not None
    assert t_briefing.tier == 0
    assert callable(t_briefing.preview_fn)
    preview = t_briefing.preview_fn({"dag_id": "dag_999"})
    assert "dag_999" in preview
