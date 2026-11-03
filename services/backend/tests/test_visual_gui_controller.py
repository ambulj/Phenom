"""
Unit tests for Closed-Loop Visual GUI Controller and Human Takeover Interrupt.
"""

import time
import pytest
from services.backend.automation.virtual_desktop_backend import MockVirtualDesktopBackend
from services.backend.automation.virtual_desktop_manager import VirtualDesktopManager
from services.backend.automation.virtual_desktop_driver import VirtualDesktopDriver
from services.backend.automation.visual_gui_controller import VisualGuiController
from services.backend.automation.human_takeover import takeover_manager, HumanTakeoverAbort
from services.backend.safety.guardian import guardian
from services.backend.voice.sound_fx import sound_fx
from services.backend.schemas.virtual_desktop import (
    GuiActionRequest,
    ActionType,
    MouseButton,
)


@pytest.fixture
def controller_setup():
    backend = MockVirtualDesktopBackend()
    manager = VirtualDesktopManager(backend=backend)
    driver = VirtualDesktopDriver(backend=backend)
    controller = VisualGuiController(driver=driver, manager=manager)

    session = manager.create_desktop("test-closed-loop")
    pid, hwnd = manager.launch_isolated_app(session.session_id, "notepad.exe")

    yield controller, session.session_id, hwnd, backend

    manager.halt()
    takeover_manager.end_automation()


def test_closed_loop_click_action(controller_setup):
    controller, session_id, hwnd, backend = controller_setup

    req = GuiActionRequest(
        session_id=session_id,
        hwnd=hwnd,
        action_type=ActionType.CLICK,
        x=150,
        y=150,
        button=MouseButton.LEFT,
    )

    report = controller.execute_action(req, settle_delay_s=0.01)

    assert report.success is True
    assert report.pre_action_image_b64 is not None
    assert report.post_action_image_b64 is not None
    assert report.duration_ms > 0
    # In MockBackend, clicking increments click count which changes drawn canvas text
    assert report.delta_detected is True
    assert report.delta_score > 0.0


def test_closed_loop_type_text_action(controller_setup):
    controller, session_id, hwnd, backend = controller_setup

    req = GuiActionRequest(
        session_id=session_id,
        hwnd=hwnd,
        action_type=ActionType.TYPE_TEXT,
        text="Phenom Autopilot",
    )

    report = controller.execute_action(req, settle_delay_s=0.01)

    assert report.success is True
    assert report.delta_detected is True
    assert backend._windows[hwnd]["content_text"] == "Phenom Autopilot"


def test_coordinate_validation_out_of_bounds(controller_setup):
    controller, session_id, hwnd, _ = controller_setup

    # Mock window rect is (100, 100, 900, 700) -> width = 800, height = 600
    req = GuiActionRequest(
        session_id=session_id,
        hwnd=hwnd,
        action_type=ActionType.CLICK,
        x=2500,  # Far outside window bounds
        y=100,
    )

    with pytest.raises(ValueError, match="Coordinate X=2500 outside window bounds"):
        controller.execute_action(req)


def test_takeover_interrupt_abort_latency_and_broadcast(controller_setup, monkeypatch):
    controller, session_id, hwnd, _ = controller_setup

    broadcasted_messages = []

    def mock_broadcast(msg):
        broadcasted_messages.append(msg)

    controller.register_broadcaster(mock_broadcast)

    audio_played = []
    monkeypatch.setattr(sound_fx, "play_automation_halt", lambda: audio_played.append("halt"))

    # Simulate physical human takeover detected
    takeover_manager._is_automating = True
    takeover_manager._is_paused = True

    req = GuiActionRequest(
        session_id=session_id,
        hwnd=hwnd,
        action_type=ActionType.CLICK,
        x=100,
        y=100,
    )

    t0 = time.perf_counter()
    with pytest.raises(HumanTakeoverAbort, match="Physical user takeover detected"):
        controller.execute_action(req)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Must abort in well under 500ms (typically < 10ms)
    assert elapsed_ms < 500.0
    assert "halt" in audio_played
    assert len(broadcasted_messages) == 1
    assert broadcasted_messages[0]["type"] == "automation.takeover_prompt"
    assert broadcasted_messages[0]["payload"]["session_id"] == session_id


def test_guardian_halt_rejects_closed_loop_action(controller_setup):
    controller, session_id, hwnd, _ = controller_setup

    guardian._halted = True
    try:
        req = GuiActionRequest(
            session_id=session_id,
            hwnd=hwnd,
            action_type=ActionType.CLICK,
            x=100,
            y=100,
        )
        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            controller.execute_action(req)
    finally:
        guardian._halted = False
