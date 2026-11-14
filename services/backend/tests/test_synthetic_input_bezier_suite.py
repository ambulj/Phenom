"""Unit tests for Win32 Synthetic Input Controller & Cubic Bezier Trajectories (Milestone 45 Phase 1)."""

import time
import pytest
from services.backend.actions.bezier_trajectory import BezierTrajectoryGenerator
from services.backend.actions.synthetic_input import SyntheticInputController
from services.backend.safety.guardian import guardian
from services.backend.schemas.computer_use import (
    ActionSequencePayload,
    ClickAction,
    ClickType,
    DragAction,
    HotKeyAction,
    MoveAction,
    Point2D,
    ScrollAction,
    TypeAction,
)


@pytest.fixture(autouse=True)
def reset_guardian():
    """Ensure guardian is clean before and after each test."""
    guardian.resume()
    yield
    guardian.resume()


def test_bezier_trajectory_smoothness_and_endpoints():
    """Validates that cubic Bezier paths land accurately on endpoints and generate smooth samples."""
    gen = BezierTrajectoryGenerator(jitter_factor=0.2)
    start = Point2D(x=100, y=150)
    end = Point2D(x=800, y=650)

    path = gen.generate_path(start, end, duration_ms=200.0, sample_interval_ms=10.0)

    assert path.start == start
    assert path.end == end
    assert len(path.points) >= 15
    assert path.points[0].x == start.x and path.points[0].y == start.y
    assert path.points[-1].x == end.x and path.points[-1].y == end.y

    # Check monotonic timestamp progression
    timestamps = [pt.timestamp_ms for pt in path.points]
    assert timestamps == sorted(timestamps)
    assert path.total_duration_ms == 200.0


def test_synthetic_input_dry_run_dispatch():
    """Tests dry-run synthetic input events across click, move, drag, type, and hotkeys."""
    controller = SyntheticInputController(dry_run=True)

    # Click
    click_act = ClickAction(target=Point2D(x=350, y=420), click_type=ClickType.LEFT)
    assert controller.click(click_act) is True

    # Type
    type_act = TypeAction(text="Phenom Cyber Agent", press_enter=True)
    assert controller.type_text(type_act) is True

    # Hotkey
    hotkey_act = HotKeyAction(keys=["ctrl", "shift", "p"])
    assert controller.hotkey(hotkey_act) is True

    # Drag
    drag_act = DragAction(start=Point2D(x=100, y=100), end=Point2D(x=200, y=200))
    assert controller.drag(drag_act) is True

    # Scroll
    scroll_act = ScrollAction(clicks=3)
    assert controller.scroll(scroll_act) is True

    # Note: smooth_move prepends move_smooth for click and drag
    actions = [ev["action"] for ev in controller.recorded_events]
    assert "click" in actions
    assert "type" in actions
    assert "hotkey" in actions
    assert "drag" in actions
    assert "scroll" in actions
    assert "move_smooth" in actions


def test_action_sequence_execution_and_metrics():
    """Tests executing a multi-action sequence payload with duration and position tracking."""
    controller = SyntheticInputController(dry_run=True)
    payload = ActionSequencePayload(
        actions=[
            MoveAction(target=Point2D(x=200, y=300), duration_ms=50.0),
            ClickAction(target=Point2D(x=200, y=300), click_type=ClickType.LEFT),
            TypeAction(text="ls -la", press_enter=True),
            ScrollAction(clicks=-2),
        ]
    )

    result = controller.execute_sequence(payload)
    assert result.success is True
    assert result.executed_actions == 4
    assert result.total_actions == 4
    assert result.guardian_halted is False
    assert result.duration_ms >= 0.0


def test_guardian_kill_switch_synchronous_abort():
    """Tests that Guardian Kill Switch instantly aborts input sequence before or during execution."""
    controller = SyntheticInputController(dry_run=True)
    guardian.trigger()  # Engage kill switch

    payload = ActionSequencePayload(
        actions=[
            ClickAction(target=Point2D(x=500, y=500)),
            TypeAction(text="destructive command"),
        ]
    )

    t0 = time.perf_counter()
    result = controller.execute_sequence(payload)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert result.success is False
    assert result.guardian_halted is True
    assert result.executed_actions == 0
    assert "Guardian Kill Switch is active" in str(result.error)
    assert elapsed_ms < 10.0, f"Guardian abort too slow: {elapsed_ms}ms"


def test_guardian_halt_during_active_movement():
    """Tests that active cursor movement halts immediately if Guardian triggers mid-trajectory."""
    controller = SyntheticInputController(dry_run=False)  # test guardian check in movement
    guardian.trigger()

    ok, _ = controller.move_smooth(Point2D(x=999, y=999), duration_ms=200.0)
    assert ok is False
