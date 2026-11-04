"""
Tests for Spatial Focus Tracking & Holographic Spatial Canvas (OVR-01, SAF-02).
Verifies:
- FocusTrackingEngine window inspection, mock injection, and halt behavior
- SpatialCanvasManager overlay lifecycle, anchor calculations, and ghost annotation tracking
- TTL expiration pruning and WebSocket notifications
- Synchronous halt and reset operations
"""

import time
import pytest
from services.backend.schemas.spatial import (
    ActiveWindowTarget,
    AnchorPoint,
    AnnotationStylePreset,
    WindowRect,
)
from services.backend.spatial.focus_tracker import FocusTrackingEngine
from services.backend.spatial.canvas_manager import SpatialCanvasManager


def test_focus_tracker_mock_and_fallback():
    """Verify focus tracking engine returns target or mock window."""
    tracker = FocusTrackingEngine()
    window = tracker.get_active_window()
    assert window is not None
    assert isinstance(window.hwnd, int)
    assert window.bounds.width >= 0

    # Inject simulated IDE window
    mock = ActiveWindowTarget(
        hwnd=9999,
        title="Phenom - Visual Studio Code",
        process_name="Code.exe",
        pid=12345,
        bounds=WindowRect(left=200, top=150, right=1480, bottom=950, width=1280, height=800),
        is_minimized=False,
        is_focused=True,
    )
    tracker.set_mock_window(mock)
    retrieved = tracker.get_active_window()
    assert retrieved.hwnd == 9999
    assert retrieved.title == "Phenom - Visual Studio Code"
    assert retrieved.bounds.width == 1280
    assert retrieved.bounds.height == 800

    # Test halt
    tracker.halt()
    halted_win = tracker.get_active_window()
    assert halted_win.hwnd == 0
    assert halted_win.title == "System Halted"
    assert tracker.is_halted() is True

    # Test reset
    tracker.reset()
    assert tracker.is_halted() is False


def test_spatial_canvas_overlay_lifecycle():
    """Verify showing, hiding, and click-through toggles on spatial canvas."""
    tracker = FocusTrackingEngine()
    canvas = SpatialCanvasManager(focus_tracker=tracker)

    # Initial state
    state = canvas.get_state()
    assert state.is_active is False
    assert state.click_through is True
    assert len(state.annotations) == 0

    # Show overlay
    shown = canvas.show_overlay(click_through=False, direct_comp=True)
    assert shown.is_active is True
    assert shown.click_through is False
    assert shown.direct_composition_enabled is True

    # Toggle click-through
    ct = canvas.toggle_click_through(True)
    assert ct is True
    assert canvas.get_state().click_through is True

    # Hide overlay
    hidden = canvas.hide_overlay()
    assert hidden.is_active is False


def test_spatial_canvas_anchor_calculations():
    """Verify screen coordinate calculations across anchor points."""
    tracker = FocusTrackingEngine()
    mock_window = ActiveWindowTarget(
        hwnd=777,
        title="Terminal - pwsh",
        process_name="WindowsTerminal.exe",
        pid=5555,
        bounds=WindowRect(left=100, top=100, right=1100, bottom=900, width=1000, height=800),
        is_minimized=False,
        is_focused=True,
    )
    tracker.set_mock_window(mock_window)
    canvas = SpatialCanvasManager(focus_tracker=tracker)

    card_w = 320
    card_h = 180
    offset_x = 25
    offset_y = 30

    # 1. TOP_LEFT: left + offset_x, top + offset_y
    ann_tl = canvas.add_annotation(
        title="Doc Hint",
        content="Read instructions",
        anchor="top-left",
        offset_x=offset_x,
        offset_y=offset_y,
    )
    assert ann_tl.screen_x == 100 + offset_x
    assert ann_tl.screen_y == 100 + offset_y

    # 2. TOP_RIGHT: right - offset_x - card_w, top + offset_y
    ann_tr = canvas.add_annotation(
        title="Test Status",
        content="100% tests passing",
        anchor="top-right",
        offset_x=offset_x,
        offset_y=offset_y,
    )
    assert ann_tr.screen_x == 1100 - offset_x - card_w
    assert ann_tr.screen_y == 100 + offset_y

    # 3. BOTTOM_LEFT: left + offset_x, bottom - offset_y - card_h
    ann_bl = canvas.add_annotation(
        title="Resource Gauge",
        content="GPU VRAM 4.2 GB",
        anchor="bottom-left",
        offset_x=offset_x,
        offset_y=offset_y,
    )
    assert ann_bl.screen_x == 100 + offset_x
    assert ann_bl.screen_y == 900 - offset_y - card_h

    # 4. BOTTOM_RIGHT: right - offset_x - card_w, bottom - offset_y - card_h
    ann_br = canvas.add_annotation(
        title="Guardian Status",
        content="Armed and ready",
        anchor="bottom-right",
        offset_x=offset_x,
        offset_y=offset_y,
    )
    assert ann_br.screen_x == 1100 - offset_x - card_w
    assert ann_br.screen_y == 900 - offset_y - card_h

    # 5. CUSTOM
    ann_custom = canvas.add_annotation(
        title="Custom Coordinates",
        content="Pin at (500, 400)",
        anchor="custom",
        offset_x=500,
        offset_y=400,
    )
    assert ann_custom.screen_x == 500
    assert ann_custom.screen_y == 400


def test_ghost_annotation_lifecycle_and_ttl():
    """Verify adding, dismissing, and TTL expiration pruning of ghost annotations."""
    tracker = FocusTrackingEngine()
    canvas = SpatialCanvasManager(focus_tracker=tracker)

    # Add 2 annotations
    ann1 = canvas.add_annotation(
        title="Temporary Hint",
        content="Expiring soon",
        ttl_seconds=1.0,
        style_preset="neon_amber",
    )
    ann2 = canvas.add_annotation(
        title="Persistent Note",
        content="Should stay active",
        ttl_seconds=None,
        style_preset="matrix_green",
    )

    state = canvas.get_state()
    assert len(state.annotations) == 2
    assert state.is_active is True

    # Dismiss ann2 explicitly
    dismissed = canvas.dismiss_annotation(ann2.id)
    assert dismissed is True
    assert len(canvas.get_state().annotations) == 1

    # Fake TTL expiry by backdating ann1.created_at
    ann1.created_at = time.time() - 10.0
    pruned = canvas.prune_expired()
    assert pruned == 1
    assert len(canvas.get_state().annotations) == 0


def test_spatial_canvas_broadcaster():
    """Verify WebSocket state broadcast callback invocation."""
    tracker = FocusTrackingEngine()
    canvas = SpatialCanvasManager(focus_tracker=tracker)

    events = []
    canvas.register_broadcaster(lambda msg: events.append(msg))

    canvas.show_overlay()
    assert len(events) == 1
    assert events[0]["type"] == "spatial_state_update"
    assert events[0]["payload"]["is_active"] is True

    canvas.add_annotation(title="Alert", content="Broadcast received")
    assert len(events) == 2


def test_spatial_canvas_guardian_halt():
    """Verify Guardian halt immediately dismisses all annotations and locks operations."""
    tracker = FocusTrackingEngine()
    canvas = SpatialCanvasManager(focus_tracker=tracker)

    canvas.add_annotation(title="Test", content="Halt test")
    assert len(canvas.get_state().annotations) == 1
    assert canvas.get_state().is_active is True

    # Halt
    canvas.halt()
    assert canvas.is_halted() is True
    assert canvas.get_state().is_active is False
    assert len(canvas.get_state().annotations) == 0

    # Operations should raise PermissionError
    with pytest.raises(PermissionError):
        canvas.show_overlay()

    with pytest.raises(PermissionError):
        canvas.add_annotation(title="Fail", content="Must fail")

    # Reset
    canvas.reset()
    assert canvas.is_halted() is False
    canvas.show_overlay()
    assert canvas.get_state().is_active is True
