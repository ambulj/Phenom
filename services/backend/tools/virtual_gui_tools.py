"""
Phenom Virtual Desktop Tools
Registers Tier 0 and Tier 1 tools in the Safety ToolRegistry for isolated
virtual desktop automation, zero cursor disruption, RAM capture, and process teardown.
"""

from typing import Dict, Any, Optional, List
from services.backend.safety.registry import registry
from services.backend.schemas.virtual_desktop import (
    GuiLaunchAppIsolatedArgs,
    GuiExecuteActionArgs,
    GuiCaptureVirtualScreenArgs,
    GuiCloseIsolatedDesktopArgs,
    GuiActionRequest,
    ActionType,
    MouseButton,
)
from services.backend.automation.virtual_desktop_manager import virtual_desktop_manager
from services.backend.automation.virtual_desktop_driver import virtual_desktop_driver
from services.backend.automation.visual_gui_controller import visual_gui_controller


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="gui_capture_virtual_screen",
    tier=0,
    description="Captures in-memory visual frame of an isolated virtual desktop window (strictly RAM only, read-only)",
    args_schema=GuiCaptureVirtualScreenArgs,
    preview_fn=lambda a: f"Capture in-memory frame of virtual desktop '{a.get('session_id') if isinstance(a, dict) else getattr(a, 'session_id', '')}' (RAM only, read-only)",
)
async def gui_capture_virtual_screen(args: GuiCaptureVirtualScreenArgs) -> Dict[str, Any]:
    session = virtual_desktop_manager.get_session(args.session_id)
    if not session or not session.is_active:
        return {"status": "error", "error": f"Session '{args.session_id}' not found or inactive."}

    target_hwnd = args.hwnd
    if not target_hwnd:
        windows = virtual_desktop_manager.enum_windows(args.session_id)
        visible_windows = [w for w in windows if w.is_visible]
        if not visible_windows:
            return {"status": "error", "error": "No visible windows found on target virtual desktop."}
        target_hwnd = visible_windows[0].hwnd

    b64_image = virtual_desktop_driver.capture_window_base64(target_hwnd)
    return {
        "status": "success",
        "session_id": args.session_id,
        "hwnd": target_hwnd,
        "image_data": b64_image,
        "privacy": "local_ram_only",
    }


# ==========================================
# Tier 1 Tools (Reversible Changes)
# ==========================================

@registry.register(
    name="gui_launch_app_isolated",
    tier=1,
    description="Launches an application inside a dedicated isolated virtual desktop without physical cursor movement",
    args_schema=GuiLaunchAppIsolatedArgs,
    preview_fn=lambda a: f"Launch '{a.get('app_path') if isinstance(a, dict) else getattr(a, 'app_path', '')}' inside isolated hidden virtual desktop '{(a.get('desktop_name') if isinstance(a, dict) else getattr(a, 'desktop_name', '')) or 'auto'}'",
)
async def gui_launch_app_isolated(args: GuiLaunchAppIsolatedArgs) -> Dict[str, Any]:
    # Check if there is an existing active session with matching desktop name, else create one
    target_session = None
    if args.desktop_name:
        for s in virtual_desktop_manager.list_active_sessions():
            if s.desktop_name == args.desktop_name:
                target_session = s
                break

    if target_session is None:
        target_session = virtual_desktop_manager.create_desktop(name=args.desktop_name)

    pid, hwnd = virtual_desktop_manager.launch_isolated_app(
        session_id=target_session.session_id,
        app_path=args.app_path,
        args=args.args,
    )

    win_title = virtual_desktop_manager.backend.get_window_title(hwnd) if hwnd else ""

    return {
        "status": "success",
        "session_id": target_session.session_id,
        "desktop_name": target_session.desktop_name,
        "pid": pid,
        "hwnd": hwnd,
        "window_title": win_title,
    }


@registry.register(
    name="gui_execute_action",
    tier=1,
    description="Injects mouse click, drag, text, or key press directly into target window on virtual desktop with visual delta verification",
    args_schema=GuiExecuteActionArgs,
    preview_fn=lambda a: f"Execute '{a.get('action_type') if isinstance(a, dict) else getattr(a, 'action_type', '')}' on window {a.get('hwnd') if isinstance(a, dict) else getattr(a, 'hwnd', '')} at ({a.get('x') if isinstance(a, dict) else getattr(a, 'x', None)}, {a.get('y') if isinstance(a, dict) else getattr(a, 'y', None)}) inside virtual desktop",
)
async def gui_execute_action(args: GuiExecuteActionArgs) -> Dict[str, Any]:
    try:
        act_enum = ActionType(args.action_type.upper())
    except ValueError:
        return {
            "status": "error",
            "error": f"Invalid action_type '{args.action_type}'. Valid values: {[e.value for e in ActionType]}",
        }

    btn = MouseButton.LEFT
    if act_enum == ActionType.RIGHT_CLICK:
        btn = MouseButton.RIGHT

    request = GuiActionRequest(
        session_id=args.session_id,
        hwnd=args.hwnd,
        action_type=act_enum,
        x=args.x,
        y=args.y,
        text=args.text,
        key_name=args.key,
        button=btn,
    )

    report = await visual_gui_controller.execute_action_async(request)
    return {
        "status": "success" if report.success else "error",
        "report": report.model_dump(),
    }


@registry.register(
    name="gui_close_isolated_desktop",
    tier=1,
    description="Terminates all child processes running in the isolated virtual desktop and closes the desktop handle",
    args_schema=GuiCloseIsolatedDesktopArgs,
    preview_fn=lambda a: f"Terminate isolated virtual desktop session '{a.get('session_id') if isinstance(a, dict) else getattr(a, 'session_id', '')}' and clean up all child processes",
)
async def gui_close_isolated_desktop(args: GuiCloseIsolatedDesktopArgs) -> Dict[str, Any]:
    closed = virtual_desktop_manager.close_desktop(args.session_id)
    return {
        "status": "success" if closed else "error",
        "session_id": args.session_id,
        "closed": closed,
    }
