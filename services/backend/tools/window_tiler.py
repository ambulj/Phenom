"""
Phenom Smart Window Tiler & Layout Staging Orchestrator
Provides Win32 native window management, multi-monitor tiling presets (Dev Mode,
Research Mode, Chill Mode), granular window snapping, and custom layout snapshotting.
Strictly conforms to SAFETY.md Tier 1 for window position modifications with preview confirmation.
"""

import sys
import os
import time
import asyncio
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry

# Win32 Constants
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040
SW_RESTORE = 9
SW_MAXIMIZE = 3
SW_MINIMIZE = 6

# In-memory saved custom layouts dictionary
_saved_custom_layouts: Dict[str, List[Dict[str, Any]]] = {}

# Mock test state for non-Windows or unit testing isolation
_mock_windows_mode: bool = False
_mock_window_store: List[Dict[str, Any]] = []


def set_mock_windows_mode(enabled: bool, mock_windows: Optional[List[Dict[str, Any]]] = None):
    """Enables or disables mock mode for automated headless testing."""
    global _mock_windows_mode, _mock_window_store
    _mock_windows_mode = enabled
    if mock_windows is not None:
        _mock_window_store = mock_windows


def get_screen_resolution() -> Dict[str, int]:
    """Retrieves primary display resolution or fallback 1920x1080."""
    if _mock_windows_mode or sys.platform != "win32":
        return {"x": 0, "y": 0, "width": 1920, "height": 1080}
    try:
        user32 = sys.modules.get("ctypes", None)
        import ctypes
        user32 = ctypes.windll.user32
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return {"x": 0, "y": 0, "width": max(w, 800), "height": max(h, 600)}
    except Exception:
        return {"x": 0, "y": 0, "width": 1920, "height": 1080}


def enumerate_visible_windows() -> List[Dict[str, Any]]:
    """Enumerates visible top-level application windows."""
    if _mock_windows_mode or sys.platform != "win32":
        if _mock_window_store:
            return [dict(w) for w in _mock_window_store]
        return [
            {"hwnd": 101, "title": "Visual Studio Code - Phenom", "rect": {"left": 0, "top": 0, "width": 800, "height": 600}},
            {"hwnd": 102, "title": "Brave - GitHub Pull Requests", "rect": {"left": 800, "top": 0, "width": 800, "height": 600}},
            {"hwnd": 103, "title": "Windows PowerShell", "rect": {"left": 0, "top": 600, "width": 800, "height": 400}},
        ]

    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    windows = []

    def enum_windows_proc(hwnd, lParam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()

        # Filter out noisy shell / desktop / background overlay windows
        ignored_titles = {
            "Program Manager", "Settings", "Windows Shell Experience Host",
            "Microsoft Text Input Application", "Task Manager"
        }
        if title in ignored_titles or len(title) < 2:
            return True

        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        # Filter out 0-size or off-screen artifacts
        if width > 100 and height > 100:
            windows.append({
                "hwnd": hwnd,
                "title": title,
                "rect": {
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom,
                    "width": width,
                    "height": height
                }
            })
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)
    return windows


def set_window_geometry(hwnd: int, x: int, y: int, width: int, height: int) -> bool:
    """Restores and repositions a specific window."""
    if _mock_windows_mode or sys.platform != "win32":
        for w in _mock_window_store:
            if w.get("hwnd") == hwnd:
                w["rect"] = {"left": x, "top": y, "width": width, "height": height}
                return True
        return True

    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.ShowWindow(hwnd, SW_RESTORE)
        res = user32.SetWindowPos(
            hwnd,
            0,
            int(x),
            int(y),
            int(width),
            int(height),
            SWP_NOZORDER | SWP_SHOWWINDOW
        )
        return bool(res)
    except Exception as e:
        print(f"[WindowTiler] Error setting window pos for {hwnd}: {e}")
        return False


def get_foreground_window_info() -> Optional[Dict[str, Any]]:
    """Gets currently active foreground window info."""
    if _mock_windows_mode or sys.platform != "win32":
        windows = enumerate_visible_windows()
        return windows[0] if windows else None

    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    title = buffer.value.strip()

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return {
        "hwnd": hwnd,
        "title": title,
        "rect": {
            "left": rect.left,
            "top": rect.top,
            "right": rect.right,
            "bottom": rect.bottom,
            "width": rect.right - rect.left,
            "height": rect.bottom - rect.top
        }
    }


def broadcast_window_event(event_type: str, payload: Dict[str, Any]):
    """Broadcasts window layout events to connected Electron clients."""
    try:
        from services.backend.main import broadcast_message
        msg = {
            "id": f"win-{os.urandom(2).hex()}",
            "type": event_type,
            "ts": str(time.time()),
            "payload": payload
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(broadcast_message(msg))
        except RuntimeError:
            try:
                new_loop = asyncio.new_event_loop()
                new_loop.run_until_complete(broadcast_message(msg))
                new_loop.close()
            except Exception:
                pass
    except Exception:
        pass


# =========================================================================
# Pydantic Argument Schemas
# =========================================================================

class ApplyWindowLayoutArgs(BaseModel):
    layout_name: str = Field(
        description="Name of the layout preset: 'dev_mode', 'research_mode', 'chill_mode', or a custom saved name."
    )
    monitor_index: int = Field(default=0, ge=0, description="Target monitor index (0 for primary display)")


class SaveWindowLayoutArgs(BaseModel):
    layout_name: str = Field(
        description="Unique name to save current desktop window arrangement snapshot."
    )


class ListWindowLayoutsArgs(BaseModel):
    pass


class SnapWindowArgs(BaseModel):
    snap_zone: Literal["left", "right", "top", "bottom", "maximize", "center"] = Field(
        description="Target snap zone on screen"
    )
    window_title: Optional[str] = Field(
        default=None,
        description="Substring of target window title. If omitted, targets currently focused/active window."
    )


# =========================================================================
# Tool Registrations
# =========================================================================

@registry.register(
    name="apply_window_layout",
    tier=1,
    description="Arranges desktop windows according to a smart layout preset ('dev_mode', 'research_mode', 'chill_mode') or restored snapshot.",
    args_schema=ApplyWindowLayoutArgs,
    preview_fn=lambda a: f"Arrange desktop windows into '{a.get('layout_name', 'dev_mode')}' layout"
)
async def apply_window_layout(layout_name: str, monitor_index: int = 0) -> Dict[str, Any]:
    """Applies specified layout preset or saved snapshot to visible windows."""
    screen = get_screen_resolution()
    w, h = screen["width"], screen["height"]
    windows = enumerate_visible_windows()
    normalized_layout = layout_name.lower().strip()
    actions = []

    if normalized_layout in _saved_custom_layouts:
        snapshot = _saved_custom_layouts[normalized_layout]
        for item in snapshot:
            title_sub = item.get("title", "")
            target_win = next((w for w in windows if title_sub.lower() in w["title"].lower()), None)
            if target_win:
                r = item.get("rect", {})
                set_window_geometry(target_win["hwnd"], r.get("left", 0), r.get("top", 0), r.get("width", 800), r.get("height", 600))
                actions.append({"window": target_win["title"], "geometry": r})

    elif normalized_layout in ("dev_mode", "dev", "developer"):
        # IDE left 60%, Browser top-right 40%/50%, Terminal bottom-right 40%/50%
        ide_keywords = ["visual studio", "code", "cursor", "pycharm", "sublime", "intellij"]
        browser_keywords = ["chrome", "brave", "edge", "firefox", "opera"]
        term_keywords = ["powershell", "terminal", "cmd", "bash", "command"]

        ide_win = next((win for win in windows if any(k in win["title"].lower() for k in ide_keywords)), None)
        browser_win = next((win for win in windows if any(k in win["title"].lower() for k in browser_keywords) and win != ide_win), None)
        term_win = next((win for win in windows if any(k in win["title"].lower() for k in term_keywords) and win not in (ide_win, browser_win)), None)

        # Fallback to top 3 visible windows if specific apps not identified
        available = [win for win in windows if win not in (ide_win, browser_win, term_win)]
        if not ide_win and available:
            ide_win = available.pop(0)
        if not browser_win and available:
            browser_win = available.pop(0)
        if not term_win and available:
            term_win = available.pop(0)

        if ide_win:
            geom = {"left": 0, "top": 0, "width": int(w * 0.60), "height": h}
            set_window_geometry(ide_win["hwnd"], geom["left"], geom["top"], geom["width"], geom["height"])
            actions.append({"role": "IDE (Left 60%)", "title": ide_win["title"], "rect": geom})

        if browser_win:
            geom = {"left": int(w * 0.60), "top": 0, "width": int(w * 0.40), "height": int(h * 0.50)}
            set_window_geometry(browser_win["hwnd"], geom["left"], geom["top"], geom["width"], geom["height"])
            actions.append({"role": "Browser (Top-Right)", "title": browser_win["title"], "rect": geom})

        if term_win:
            geom = {"left": int(w * 0.60), "top": int(h * 0.50), "width": int(w * 0.40), "height": int(h * 0.50)}
            set_window_geometry(term_win["hwnd"], geom["left"], geom["top"], geom["width"], geom["height"])
            actions.append({"role": "Terminal (Bottom-Right)", "title": term_win["title"], "rect": geom})

    elif normalized_layout in ("research_mode", "research", "study"):
        # Browser left 50%, Notes/Obsidian right 50%
        browser_keywords = ["chrome", "brave", "edge", "firefox"]
        notes_keywords = ["obsidian", "notepad", "notes", "word", "document", "pdf"]

        browser_win = next((win for win in windows if any(k in win["title"].lower() for k in browser_keywords)), None)
        notes_win = next((win for win in windows if any(k in win["title"].lower() for k in notes_keywords) and win != browser_win), None)

        available = [win for win in windows if win not in (browser_win, notes_win)]
        if not browser_win and available:
            browser_win = available.pop(0)
        if not notes_win and available:
            notes_win = available.pop(0)

        if browser_win:
            geom = {"left": 0, "top": 0, "width": int(w * 0.50), "height": h}
            set_window_geometry(browser_win["hwnd"], geom["left"], geom["top"], geom["width"], geom["height"])
            actions.append({"role": "Browser (Left 50%)", "title": browser_win["title"], "rect": geom})

        if notes_win:
            geom = {"left": int(w * 0.50), "top": 0, "width": int(w * 0.50), "height": h}
            set_window_geometry(notes_win["hwnd"], geom["left"], geom["top"], geom["width"], geom["height"])
            actions.append({"role": "Notes (Right 50%)", "title": notes_win["title"], "rect": geom})

    elif normalized_layout in ("chill_mode", "chill", "media"):
        # Centered active/media window 60%w, 80%h
        target_win = windows[0] if windows else None
        if target_win:
            geom = {"left": int(w * 0.20), "top": int(h * 0.10), "width": int(w * 0.60), "height": int(h * 0.80)}
            set_window_geometry(target_win["hwnd"], geom["left"], geom["top"], geom["width"], geom["height"])
            actions.append({"role": "Centered Media (60%x80%)", "title": target_win["title"], "rect": geom})

    else:
        return {
            "status": "error",
            "message": f"Unknown layout preset '{layout_name}'. Available: 'dev_mode', 'research_mode', 'chill_mode', or saved custom layouts."
        }

    broadcast_window_event("WINDOW_LAYOUT_APPLIED", {"layout": normalized_layout, "actions": actions})
    return {
        "status": "success",
        "layout": normalized_layout,
        "windows_arranged": len(actions),
        "actions": actions,
        "message": f"Applied '{normalized_layout}' layout to {len(actions)} windows."
    }


@registry.register(
    name="save_window_layout",
    tier=0,
    description="Saves a snapshot of current visible desktop window positions under a custom name.",
    args_schema=SaveWindowLayoutArgs,
    preview_fn=lambda a: f"Save current window layout as '{a.get('layout_name', 'custom')}'"
)
async def save_window_layout(layout_name: str) -> Dict[str, Any]:
    """Captures and stores active window coordinates."""
    windows = enumerate_visible_windows()
    snapshot = []
    for win in windows:
        snapshot.append({
            "title": win["title"],
            "rect": win["rect"]
        })
    normalized = layout_name.lower().strip()
    _saved_custom_layouts[normalized] = snapshot
    return {
        "status": "success",
        "layout_name": normalized,
        "windows_captured": len(snapshot),
        "message": f"Saved layout snapshot '{normalized}' with {len(snapshot)} window positions."
    }


@registry.register(
    name="list_window_layouts",
    tier=0,
    description="Lists all built-in window layout presets and saved user layout snapshots.",
    args_schema=ListWindowLayoutsArgs,
    preview_fn=lambda a: "List window layouts and presets"
)
async def list_window_layouts() -> Dict[str, Any]:
    """Lists built-in presets and user saved layouts."""
    presets = [
        {"name": "dev_mode", "description": "IDE left 60%, Browser top-right 40%, Terminal bottom-right 40%"},
        {"name": "research_mode", "description": "Browser left 50%, Notes/Obsidian right 50%"},
        {"name": "chill_mode", "description": "Media player / active window centered 60%x80%"}
    ]
    custom = [{"name": name, "window_count": len(wins)} for name, wins in _saved_custom_layouts.items()]
    return {
        "status": "success",
        "presets": presets,
        "custom_layouts": custom
    }


@registry.register(
    name="snap_window",
    tier=1,
    description="Snaps a target window (or active foreground window) to a specific screen zone ('left', 'right', 'top', 'bottom', 'maximize', 'center').",
    args_schema=SnapWindowArgs,
    preview_fn=lambda a: f"Snap {a.get('window_title') or 'active window'} to '{a.get('snap_zone', 'left')}'"
)
async def snap_window(snap_zone: Literal["left", "right", "top", "bottom", "maximize", "center"], window_title: Optional[str] = None) -> Dict[str, Any]:
    """Snaps a single window to specified zone."""
    screen = get_screen_resolution()
    w, h = screen["width"], screen["height"]
    windows = enumerate_visible_windows()

    target_win = None
    if window_title:
        target_win = next((win for win in windows if window_title.lower() in win["title"].lower()), None)
    if not target_win:
        fg = get_foreground_window_info()
        if fg:
            target_win = next((win for win in windows if win["hwnd"] == fg["hwnd"]), None)
    if not target_win and windows:
        target_win = windows[0]

    if not target_win:
        return {"status": "error", "message": "No active window found to snap."}

    zone_map = {
        "left": {"left": 0, "top": 0, "width": int(w / 2), "height": h},
        "right": {"left": int(w / 2), "top": 0, "width": int(w / 2), "height": h},
        "top": {"left": 0, "top": 0, "width": w, "height": int(h / 2)},
        "bottom": {"left": 0, "top": int(h / 2), "width": w, "height": int(h / 2)},
        "center": {"left": int(w * 0.15), "top": int(h * 0.10), "width": int(w * 0.70), "height": int(h * 0.80)},
        "maximize": {"left": 0, "top": 0, "width": w, "height": h}
    }
    geom = zone_map.get(snap_zone, zone_map["left"])
    success = set_window_geometry(target_win["hwnd"], geom["left"], geom["top"], geom["width"], geom["height"])

    broadcast_window_event("WINDOW_SNAPPED", {
        "window": target_win["title"],
        "zone": snap_zone,
        "geometry": geom
    })

    return {
        "status": "success" if success else "warning",
        "window": target_win["title"],
        "snap_zone": snap_zone,
        "geometry": geom,
        "message": f"Snapped '{target_win['title']}' to {snap_zone}."
    }
