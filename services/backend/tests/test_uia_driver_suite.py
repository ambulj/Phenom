"""Unit tests for Windows UI Automation (UIA) Semantic Tree Driver & Hybrid Bezier Fallback (Milestone 45 Phase 2)."""

import pytest
from services.backend.actions.synthetic_input import synthetic_input
from services.backend.actions.uia_driver import UIADriver, UIElementNode, UIRect
from services.backend.safety.guardian import guardian


@pytest.fixture(autouse=True)
def clean_guardian_and_driver():
    """Reset guardian and driver mock state before and after each test."""
    guardian.resume()
    synthetic_input.dry_run = True
    synthetic_input.recorded_events.clear()
    yield
    guardian.resume()
    synthetic_input.dry_run = False


def create_sample_ui_tree() -> list[UIElementNode]:
    """Generates a sample desktop UI tree."""
    return [
        UIElementNode(
            name="Visual Studio Code",
            automation_id="vscode_main_window",
            control_type="Window",
            class_name="Chrome_WidgetWin_1",
            rect=UIRect(left=100, top=100, right=1200, bottom=900),
            children=[
                UIElementNode(
                    name="Run Python File",
                    automation_id="btn_run_py",
                    control_type="Button",
                    class_name="NativeButton",
                    rect=UIRect(left=1100, top=120, right=1150, bottom=150),
                    supports_invoke=True,
                ),
                UIElementNode(
                    name="Command Palette Search",
                    automation_id="input_search_box",
                    control_type="EditBox",
                    class_name="NativeEdit",
                    rect=UIRect(left=400, top=110, right=800, bottom=140),
                    supports_value=True,
                ),
                UIElementNode(
                    name="Custom Canvas Plot",
                    automation_id="canvas_plot_view",
                    control_type="Custom",
                    class_name="Direct2DCanvas",
                    rect=UIRect(left=200, top=200, right=600, bottom=600),
                    supports_invoke=False,  # Needs Bezier click fallback
                ),
            ]
        ),
        UIElementNode(
            name="PowerShell Red-Team Console",
            automation_id="ps_terminal_win",
            control_type="Window",
            class_name="ConsoleWindowClass",
            rect=UIRect(left=1220, top=100, right=1900, bottom=900),
            children=[
                UIElementNode(
                    name="Clear Terminal",
                    automation_id="btn_clear_term",
                    control_type="Button",
                    class_name="NativeButton",
                    rect=UIRect(left=1850, top=110, right=1890, bottom=130),
                    supports_invoke=True,
                )
            ]
        )
    ]


def test_element_search_by_name_id_and_control_type():
    """Tests finding UI elements by name substring, automation ID, and control type."""
    driver = UIADriver(dry_run=True)
    driver.set_mock_tree(create_sample_ui_tree())

    # Find by name
    run_btn = driver.find_first(name="Run Python")
    assert run_btn is not None
    assert run_btn.automation_id == "btn_run_py"
    assert run_btn.rect.center.x == 1125
    assert run_btn.rect.center.y == 135

    # Find by control type
    buttons = driver.find_elements(control_type="Button")
    assert len(buttons) == 2
    assert {b.name for b in buttons} == {"Run Python File", "Clear Terminal"}

    # Find by automation id
    search_box = driver.find_first(automation_id="input_search_box")
    assert search_box is not None
    assert search_box.name == "Command Palette Search"


def test_native_invoke_pattern_success():
    """Tests semantic invocation of an element supporting native InvokePattern."""
    driver = UIADriver(dry_run=True)
    driver.set_mock_tree(create_sample_ui_tree())

    run_btn = driver.find_first(name="Run Python File")
    assert run_btn is not None

    ok, message = driver.invoke_element(run_btn, force_bezier_fallback=False)
    assert ok is True
    assert "via native UIA InvokePattern" in message


def test_hybrid_bezier_fallback_on_unsupported_invoke():
    """Tests that custom canvas or elements lacking InvokePattern fall back to Bezier mouse click."""
    driver = UIADriver(dry_run=True)
    driver.set_mock_tree(create_sample_ui_tree())

    canvas = driver.find_first(name="Custom Canvas Plot")
    assert canvas is not None
    assert canvas.supports_invoke is False

    ok, message = driver.invoke_element(canvas)
    assert ok is True
    assert "via Bezier fallback" in message
    assert "(400, 400)" in message

    # Verify synthetic input recorded click event at center (400, 400)
    assert any(ev.get("action") == "click" and ev.get("target") == (400, 400) for ev in synthetic_input.recorded_events)


def test_value_pattern_and_keystroke_fallback():
    """Tests setting element text via ValuePattern and falling back to click + keystrokes."""
    driver = UIADriver(dry_run=True)
    driver.set_mock_tree(create_sample_ui_tree())

    search_box = driver.find_first(automation_id="input_search_box")
    assert search_box is not None

    # Native ValuePattern
    ok, msg = driver.set_element_value(search_box, "git status")
    assert ok is True
    assert search_box.value == "git status"
    assert "via ValuePattern" in msg

    # Fallback to click + type on non-value element
    canvas = driver.find_first(name="Custom Canvas Plot")
    assert canvas is not None
    ok, msg = driver.set_element_value(canvas, "canvas_command")
    assert ok is True
    assert "via click + keystroke fallback" in msg
    assert canvas.value == "canvas_command"


def test_guardian_kill_switch_blocks_uia_operations():
    """Tests that Guardian Kill Switch immediately aborts UI tree search and pattern invocation."""
    driver = UIADriver(dry_run=True)
    driver.set_mock_tree(create_sample_ui_tree())

    guardian.trigger("Test halt during UIA operation")

    # Search blocked
    assert driver.find_elements(control_type="Button") == []

    # Invoke blocked
    elem = create_sample_ui_tree()[0]
    ok, msg = driver.invoke_element(elem)
    assert ok is False
    assert "Guardian kill switch is active" in msg

    # Set value blocked
    ok, msg = driver.set_element_value(elem, "test")
    assert ok is False
    assert "Guardian kill switch is active" in msg
