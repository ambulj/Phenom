"""
Unit tests for Virtual Desktop Safety Tools and ToolRegistry compliance.
"""

import pytest
from services.backend.safety.registry import registry
from services.backend.automation.virtual_desktop_backend import MockVirtualDesktopBackend
from services.backend.automation.virtual_desktop_manager import virtual_desktop_manager
from services.backend.automation.virtual_desktop_driver import virtual_desktop_driver
from services.backend.automation.visual_gui_controller import visual_gui_controller
# Import tools to ensure registration
import services.backend.tools.virtual_gui_tools as vtools
from services.backend.schemas.virtual_desktop import (
    GuiLaunchAppIsolatedArgs,
    GuiExecuteActionArgs,
    GuiCaptureVirtualScreenArgs,
    GuiCloseIsolatedDesktopArgs,
)


@pytest.fixture(autouse=True)
def setup_mock_environment():
    backend = MockVirtualDesktopBackend()
    virtual_desktop_manager.set_backend(backend)
    virtual_desktop_driver._backend = backend
    visual_gui_controller._driver = virtual_desktop_driver
    visual_gui_controller._manager = virtual_desktop_manager
    yield
    virtual_desktop_manager.halt()


def test_tools_registered_in_registry():
    tools = registry.list_all()
    tool_names = list(tools.keys())

    assert "gui_capture_virtual_screen" in tool_names
    assert "gui_launch_app_isolated" in tool_names
    assert "gui_execute_action" in tool_names
    assert "gui_close_isolated_desktop" in tool_names


def test_tool_tiers():
    assert registry.get_tier("gui_capture_virtual_screen") == 0
    assert registry.get_tier("gui_launch_app_isolated") == 1
    assert registry.get_tier("gui_execute_action") == 1
    assert registry.get_tier("gui_close_isolated_desktop") == 1


def test_preview_functions():
    launch_def = registry.get("gui_launch_app_isolated")
    assert launch_def is not None
    launch_args = GuiLaunchAppIsolatedArgs(app_path="calc.exe", desktop_name="Sandbox")
    preview_launch = launch_def.generate_preview(launch_args.model_dump())
    assert "Launch 'calc.exe' inside isolated hidden virtual desktop 'Sandbox'" in preview_launch

    exec_def = registry.get("gui_execute_action")
    assert exec_def is not None
    exec_args = GuiExecuteActionArgs(
        session_id="s1",
        hwnd=123,
        action_type="CLICK",
        x=50,
        y=50,
    )
    preview_exec = exec_def.generate_preview(exec_args.model_dump())
    assert "Execute 'CLICK' on window 123 at (50, 50)" in preview_exec

    cap_def = registry.get("gui_capture_virtual_screen")
    assert cap_def is not None
    cap_args = GuiCaptureVirtualScreenArgs(session_id="s1")
    preview_cap = cap_def.generate_preview(cap_args.model_dump())
    assert "Capture in-memory frame of virtual desktop 's1'" in preview_cap

    close_def = registry.get("gui_close_isolated_desktop")
    assert close_def is not None
    close_args = GuiCloseIsolatedDesktopArgs(session_id="s1")
    preview_close = close_def.generate_preview(close_args.model_dump())
    assert "Terminate isolated virtual desktop session 's1'" in preview_close


@pytest.mark.asyncio
async def test_tool_execution_flow():
    # 1. Launch isolated app
    launch_res = await vtools.gui_launch_app_isolated(
        GuiLaunchAppIsolatedArgs(app_path="notepad.exe", desktop_name="TestDesk")
    )
    assert launch_res["status"] == "success"
    session_id = launch_res["session_id"]
    hwnd = launch_res["hwnd"]
    assert hwnd > 0

    # 2. Capture screen (Tier 0)
    cap_res = await vtools.gui_capture_virtual_screen(
        GuiCaptureVirtualScreenArgs(session_id=session_id, hwnd=hwnd)
    )
    assert cap_res["status"] == "success"
    assert cap_res["image_data"].startswith("data:image/jpeg;base64,")
    assert cap_res["privacy"] == "local_ram_only"

    # 3. Execute action (Tier 1)
    act_res = await vtools.gui_execute_action(
        GuiExecuteActionArgs(
            session_id=session_id,
            hwnd=hwnd,
            action_type="CLICK",
            x=200,
            y=200,
        )
    )
    assert act_res["status"] == "success"
    assert act_res["report"]["delta_detected"] is True

    # 4. Close desktop (Tier 1)
    close_res = await vtools.gui_close_isolated_desktop(
        GuiCloseIsolatedDesktopArgs(session_id=session_id)
    )
    assert close_res["status"] == "success"
    assert close_res["closed"] is True
