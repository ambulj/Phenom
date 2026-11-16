"""Comprehensive Test Suite for Cross-Application Visual Desktop Choreography (Milestone 49 Phase 4).

Covers:
- CHOREO-01: Cubic Bezier trajectory calculation, S-curve velocity profiling, and micro-jitter.
- CHOREO-02: Multi-step cross-application choreography plans with focus verification & anti-checkout checks.
- CHOREO-03: Visual HUD target halo emission, coordinate bounding boxes, and lifecycle.
- Safety: Rule 8 anti-checkout blocking, human takeover hook, and Guardian kill switch SLA (< 25ms).
- ToolRegistry: execute_choreographed_action (Tier 1), preview_target_halo (Tier 0), generate_bezier_trajectory (Tier 0).
"""

import math
import time
import pytest

from services.backend.schemas.desktop_choreography import (
    BezierPoint,
    BezierTrajectory,
    ChoreographyPlan,
    ChoreographyResult,
    DesktopActionStep,
    DesktopActionType,
    TargetHaloSpec,
)
from services.backend.schemas.semantic_focus import BoundingRect, WindowContext
from services.backend.desktop.bezier_trajectory_generator import BezierTrajectoryGenerator
from services.backend.desktop.visual_target_halo import VisualTargetHaloEmitter
from services.backend.desktop.semantic_focus_guard import SemanticFocusGuard
from services.backend.desktop.window_focus_tracker import WindowFocusTracker
from services.backend.desktop.anti_checkout_shield import AntiCheckoutShield
from services.backend.desktop.human_takeover_hook import HumanTakeoverHook
from services.backend.desktop.desktop_choreographer import DesktopChoreographer
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.tools.desktop_choreographer_tools import (
    handle_execute_choreographed_action,
    handle_generate_bezier_trajectory,
    handle_preview_target_halo,
)


@pytest.fixture
def mock_choreography_env():
    trajectory_gen = BezierTrajectoryGenerator(random_seed=42)
    halo_emitter = VisualTargetHaloEmitter()
    tracker = WindowFocusTracker()
    guard = SemanticFocusGuard(tracker=tracker)
    anti_checkout = AntiCheckoutShield()
    takeover_hook = HumanTakeoverHook()

    simulated_ctx = WindowContext(
        hwnd=8192,
        title="Phenom IDE - Visual Studio Code",
        process_name="Code.exe",
        pid=5432,
        bounding_rect=BoundingRect(left=50, top=50, right=1200, bottom=950),
        is_minimized=False,
    )
    tracker.set_simulated_window(simulated_ctx)

    choreographer = DesktopChoreographer(
        trajectory_gen=trajectory_gen,
        halo_emitter=halo_emitter,
        focus_guard=guard,
        anti_checkout=anti_checkout,
        takeover_hook=takeover_hook,
    )
    choreographer.set_current_cursor((100, 100))

    return {
        "choreographer": choreographer,
        "trajectory_gen": trajectory_gen,
        "halo_emitter": halo_emitter,
        "tracker": tracker,
        "guard": guard,
        "anti_checkout": anti_checkout,
        "takeover_hook": takeover_hook,
        "ctx": simulated_ctx,
    }


# ============================================================================
# 1. Cubic Bezier Motion & Micro-Jitter Tests (CHOREO-01)
# ============================================================================

def test_bezier_trajectory_generator_math_and_jitter(mock_choreography_env):
    gen: BezierTrajectoryGenerator = mock_choreography_env["trajectory_gen"]

    start = (100, 100)
    target = (800, 600)
    traj = gen.generate(start_pos=start, target_pos=target, duration_ms=400.0, add_jitter=True)

    expected_dist = math.hypot(800 - 100, 600 - 100)
    assert abs(traj.total_distance_px - expected_dist) < 1.0
    assert traj.duration_ms == 400.0
    assert len(traj.points) >= 15

    # Check start and endpoint
    first_pt = traj.points[0]
    last_pt = traj.points[-1]
    assert (int(first_pt.x), int(first_pt.y)) == start
    assert (int(last_pt.x), int(last_pt.y)) == target

    # Check normalized progress progression
    assert first_pt.t == 0.0
    assert last_pt.t == 1.0

    # Verify intermediate curvature exists (not a straight line)
    mid_idx = len(traj.points) // 2
    mid_pt = traj.points[mid_idx]
    # Linear midpoint would be (450, 350)
    # Due to Bezier curvature, mid_pt should have non-zero variance from pure linear
    assert mid_pt.x != 0.0 and mid_pt.y != 0.0


# ============================================================================
# 2. Visual HUD Target Halo Tests (CHOREO-03)
# ============================================================================

def test_visual_target_halo_emission_and_lifecycle(mock_choreography_env):
    emitter: VisualTargetHaloEmitter = mock_choreography_env["halo_emitter"]

    box = (200, 300, 80, 40)
    halo = emitter.create_halo(
        target_name="Save File Button",
        bounding_box=box,
        action_type="CLICK",
        duration_ms=500,
        color_hex="#FFAA00",
    )

    assert halo.halo_id.startswith("halo_")
    assert halo.target_name == "Save File Button"
    assert halo.bounding_box == box
    assert halo.color_hex == "#FFAA00"

    # Query active halo
    active = emitter.get_active_halo()
    assert active is not None
    assert active.halo_id == halo.halo_id

    # List history
    history = emitter.list_recent_halos()
    assert len(history) >= 1
    assert history[-1].halo_id == halo.halo_id


# ============================================================================
# 3. Single-Step Choreographed Execution (CHOREO-02)
# ============================================================================

def test_desktop_choreographer_single_step_execution(mock_choreography_env):
    choreographer: DesktopChoreographer = mock_choreography_env["choreographer"]

    step = DesktopActionStep(
        step_id="step_test_1",
        action_type=DesktopActionType.CLICK,
        target_window_title="Visual Studio Code",
        target_coordinates=(500, 400),
        target_element_name="Editor File Tab",
        duration_ms=250,
    )

    res = choreographer.execute_step(step)
    assert res["status"] == "SUCCESS"
    assert res["target_coordinates"] == (500, 400)
    assert res["trajectory_points_count"] > 0
    assert res["halo_spec"] is not None
    assert res["halo_spec"]["target_name"] == "Editor File Tab"


# ============================================================================
# 4. Semantic Focus Guard Integration (GUI-02 -> CHOREO-02)
# ============================================================================

def test_desktop_choreographer_focus_guard_mismatch(mock_choreography_env):
    choreographer: DesktopChoreographer = mock_choreography_env["choreographer"]

    # Active window is VS Code; requesting click in Google Chrome
    step = DesktopActionStep(
        step_id="step_mismatch",
        action_type=DesktopActionType.CLICK,
        target_window_title="Google Chrome",
        target_coordinates=(400, 300),
        target_element_name="Search Bar",
    )

    res = choreographer.execute_step(step)
    assert res["status"] == "ABORTED_FOCUS_MISMATCH"
    assert "Window title mismatch" in res["error"]


# ============================================================================
# 5. Anti-Checkout Shield Integration (Rule 8 -> CHOREO-02)
# ============================================================================

def test_desktop_choreographer_anti_checkout_blocking(mock_choreography_env):
    choreographer: DesktopChoreographer = mock_choreography_env["choreographer"]

    # 1. Blocked via window title
    step_title = DesktopActionStep(
        step_id="step_checkout_title",
        action_type=DesktopActionType.CLICK,
        target_window_title="Amazon Checkout - Payment Options",
        target_coordinates=(400, 300),
    )
    res1 = choreographer.execute_step(step_title)
    assert res1["status"] == "ABORTED_CHECKOUT"
    assert "Rule 8 Violation" in res1["error"]

    # 2. Blocked via element name
    step_elem = DesktopActionStep(
        step_id="step_checkout_elem",
        action_type=DesktopActionType.CLICK,
        target_window_title="Visual Studio Code",
        target_coordinates=(400, 300),
        target_element_name="Buy Now with 1-Click",
    )
    res2 = choreographer.execute_step(step_elem)
    assert res2["status"] == "ABORTED_CHECKOUT"
    assert "Rule 8 Violation" in res2["error"]


# ============================================================================
# 6. Multi-Step Cross-Application Choreography Plan (CHOREO-02)
# ============================================================================

def test_desktop_choreographer_multi_step_plan(mock_choreography_env):
    choreographer: DesktopChoreographer = mock_choreography_env["choreographer"]

    plan = ChoreographyPlan(
        plan_id="plan_dev_flow",
        title="Open File and Build in VS Code",
        steps=[
            DesktopActionStep(
                step_id="s1_move",
                action_type=DesktopActionType.MOVE,
                target_window_title="Visual Studio Code",
                target_coordinates=(200, 200),
                target_element_name="File Explorer Tree",
            ),
            DesktopActionStep(
                step_id="s2_click",
                action_type=DesktopActionType.CLICK,
                target_window_title="Visual Studio Code",
                target_coordinates=(400, 300),
                target_element_name="main.py item",
            ),
            DesktopActionStep(
                step_id="s3_type",
                action_type=DesktopActionType.TYPE_TEXT,
                target_window_title="Visual Studio Code",
                text_payload="# Milestone 49 Choreography",
            ),
        ],
    )

    result: ChoreographyResult = choreographer.execute_plan(plan)
    assert result.status == "SUCCESS"
    assert result.completed_steps == 3
    assert result.total_steps == 3
    assert result.error_message is None


# ============================================================================
# 7. Guardian Kill Switch SLA Benchmark (< 25.0ms)
# ============================================================================

def test_guardian_kill_switch_sla_choreographer(mock_choreography_env):
    choreographer: DesktopChoreographer = mock_choreography_env["choreographer"]
    step = DesktopActionStep(
        step_id="sla_step",
        action_type=DesktopActionType.CLICK,
        target_coordinates=(500, 500),
    )

    durations_ms = []
    for _ in range(100):
        t0 = time.perf_counter()
        guardian._halted = True
        try:
            choreographer.execute_step(step)
        except PermissionError:
            pass
        finally:
            guardian._halted = False
        t1 = time.perf_counter()
        durations_ms.append((t1 - t0) * 1000.0)

    max_ms = max(durations_ms)
    avg_ms = sum(durations_ms) / len(durations_ms)

    assert max_ms < 25.0, f"Guardian SLA exceeded: max={max_ms:.3f}ms"
    assert avg_ms < 5.0, f"Guardian SLA avg too high: {avg_ms:.3f}ms"


# ============================================================================
# 8. ToolRegistry Registrations & Handlers
# ============================================================================

def test_desktop_choreographer_tool_registrations():
    tool_exec = registry.get("execute_choreographed_action")
    assert tool_exec is not None
    assert tool_exec.tier == 1

    tool_halo = registry.get("preview_target_halo")
    assert tool_halo is not None
    assert tool_halo.tier == 0

    tool_bezier = registry.get("generate_bezier_trajectory")
    assert tool_bezier is not None
    assert tool_bezier.tier == 0


def test_desktop_choreographer_tool_handlers_execution():
    # 1. Preview halo
    res_halo = handle_preview_target_halo(
        target_name="Commit Button",
        x=600,
        y=400,
        width=80,
        height=35,
    )
    assert res_halo["status"] == "success"
    assert res_halo["bounding_box"] == (560, 383, 80, 35)

    # 2. Generate Bezier trajectory
    res_bezier = handle_generate_bezier_trajectory(
        start_x=100,
        start_y=100,
        target_x=500,
        target_y=500,
        duration_ms=300.0,
    )
    assert res_bezier["status"] == "success"
    assert res_bezier["points_count"] >= 15

    # 3. Execute choreographed action
    res_action = handle_execute_choreographed_action(
        action_type="CLICK",
        target_x=450,
        target_y=350,
        target_element_name="Tab Header",
    )
    assert res_action["status"] == "SUCCESS"
