"""
Unit tests for Virtual Desktop Schemas and Protocol models.
"""

import pytest
from services.backend.schemas.virtual_desktop import (
    ActionType,
    MouseButton,
    WindowInfo,
    VirtualDesktopSession,
    GuiActionRequest,
    VisualFeedbackReport,
    GuiLaunchAppIsolatedArgs,
    GuiExecuteActionArgs,
    GuiCaptureVirtualScreenArgs,
    GuiCloseIsolatedDesktopArgs,
)
from services.backend.schemas.protocol import (
    AutomationTakeoverPromptPayload,
    AutomationTakeoverPromptMsg,
    AutomationTakeoverReplyPayload,
    AutomationTakeoverReplyMsg,
)


def test_action_type_and_mouse_button_enums():
    assert ActionType.CLICK.value == "CLICK"
    assert ActionType.DOUBLE_CLICK.value == "DOUBLE_CLICK"
    assert ActionType.RIGHT_CLICK.value == "RIGHT_CLICK"
    assert ActionType.DRAG.value == "DRAG"
    assert ActionType.TYPE_TEXT.value == "TYPE_TEXT"
    assert ActionType.KEY_PRESS.value == "KEY_PRESS"
    assert ActionType.HOTKEY.value == "HOTKEY"

    assert MouseButton.LEFT.value == "LEFT"
    assert MouseButton.RIGHT.value == "RIGHT"
    assert MouseButton.MIDDLE.value == "MIDDLE"


def test_virtual_desktop_session_model():
    session = VirtualDesktopSession(
        session_id="vdesk-1234",
        desktop_name="PhenomVirtualDesk_1234",
        hdesk=4096,
        pids=[1001, 1002],
        is_active=True,
    )
    assert session.session_id == "vdesk-1234"
    assert session.desktop_name == "PhenomVirtualDesk_1234"
    assert session.hdesk == 4096
    assert session.pids == [1001, 1002]
    assert session.is_active is True
    assert session.created_at > 0

    dumped = session.model_dump()
    assert dumped["session_id"] == "vdesk-1234"
    restored = VirtualDesktopSession.model_validate(dumped)
    assert restored.session_id == session.session_id


def test_window_info_model():
    win = WindowInfo(
        hwnd=65538,
        title="Calculator",
        class_name="ApplicationFrameWindow",
        rect=(10, 20, 600, 400),
        is_visible=True,
        is_minimized=False,
    )
    assert win.hwnd == 65538
    assert win.title == "Calculator"
    assert win.rect == (10, 20, 600, 400)
    assert win.is_visible is True
    assert win.is_minimized is False


def test_gui_action_request_model():
    req = GuiActionRequest(
        session_id="sess-1",
        hwnd=1234,
        action_type=ActionType.CLICK,
        x=150,
        y=200,
        button=MouseButton.LEFT,
    )
    assert req.action_type == ActionType.CLICK
    assert req.x == 150
    assert req.y == 200

    type_req = GuiActionRequest(
        session_id="sess-1",
        hwnd=1234,
        action_type=ActionType.TYPE_TEXT,
        text="Hello Phenom",
    )
    assert type_req.text == "Hello Phenom"


def test_visual_feedback_report():
    report = VisualFeedbackReport(
        success=True,
        delta_detected=True,
        delta_score=0.085,
        duration_ms=120.5,
        pre_action_image_b64="data:pre",
        post_action_image_b64="data:post",
    )
    assert report.success is True
    assert report.delta_detected is True
    assert report.delta_score == 0.085
    assert report.action_id is not None
    assert report.error is None


def test_tool_argument_schemas():
    launch = GuiLaunchAppIsolatedArgs(app_path="notepad.exe", args=["test.txt"])
    assert launch.app_path == "notepad.exe"
    assert launch.args == ["test.txt"]

    exec_action = GuiExecuteActionArgs(
        session_id="s-1",
        hwnd=99,
        action_type="CLICK",
        x=50,
        y=60,
    )
    assert exec_action.hwnd == 99

    cap = GuiCaptureVirtualScreenArgs(session_id="s-1")
    assert cap.session_id == "s-1"
    assert cap.hwnd is None

    close = GuiCloseIsolatedDesktopArgs(session_id="s-1")
    assert close.session_id == "s-1"


def test_takeover_prompt_protocol_models():
    prompt = AutomationTakeoverPromptMsg(
        payload=AutomationTakeoverPromptPayload(
            reason="Physical mouse movement detected",
            session_id="sess-abc",
            app_name="Notepad",
            timestamp="2026-11-03T20:00:00Z",
        )
    )
    assert prompt.type == "automation.takeover_prompt"
    assert prompt.payload.reason == "Physical mouse movement detected"
    assert prompt.payload.session_id == "sess-abc"
    assert prompt.payload.app_name == "Notepad"

    reply = AutomationTakeoverReplyMsg(
        payload=AutomationTakeoverReplyPayload(
            decision="stop",
            session_id="sess-abc",
        )
    )
    assert reply.type == "automation.takeover_reply"
    assert reply.payload.decision == "stop"
    assert reply.payload.session_id == "sess-abc"
