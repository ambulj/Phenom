"""
Phenom Virtual Desktop Schemas and Protocol Models
Pydantic V2 models for isolated Win32 virtual desktop automation,
RAM-only window capture, action injection, and visual feedback reporting.
"""

from enum import Enum
import time
import uuid
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    CLICK = "CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    RIGHT_CLICK = "RIGHT_CLICK"
    DRAG = "DRAG"
    TYPE_TEXT = "TYPE_TEXT"
    KEY_PRESS = "KEY_PRESS"
    HOTKEY = "HOTKEY"


class MouseButton(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    MIDDLE = "MIDDLE"


class WindowInfo(BaseModel):
    hwnd: int
    title: str = ""
    class_name: str = ""
    rect: Tuple[int, int, int, int] = (0, 0, 0, 0)  # (left, top, right, bottom)
    is_visible: bool = True
    is_minimized: bool = False


class VirtualDesktopSession(BaseModel):
    session_id: str
    desktop_name: str
    hdesk: Optional[int] = None
    pids: List[int] = Field(default_factory=list)
    is_active: bool = True
    created_at: float = Field(default_factory=time.time)


class GuiActionRequest(BaseModel):
    session_id: str
    hwnd: int
    action_type: ActionType
    x: Optional[int] = None
    y: Optional[int] = None
    x2: Optional[int] = None
    y2: Optional[int] = None
    text: Optional[str] = None
    key_code: Optional[int] = None
    key_name: Optional[str] = None
    button: MouseButton = MouseButton.LEFT


class VisualFeedbackReport(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    success: bool
    delta_detected: bool = False
    delta_score: float = 0.0
    duration_ms: float = 0.0
    error: Optional[str] = None
    pre_action_image_b64: Optional[str] = None
    post_action_image_b64: Optional[str] = None


# Tool Argument Schemas for ToolRegistry
class GuiLaunchAppIsolatedArgs(BaseModel):
    app_path: str = Field(..., description="Absolute path or executable name to launch")
    args: Optional[List[str]] = Field(default=None, description="Optional command-line arguments")
    desktop_name: Optional[str] = Field(default=None, description="Optional custom virtual desktop name")


class GuiExecuteActionArgs(BaseModel):
    session_id: str = Field(..., description="Target virtual desktop session ID")
    hwnd: int = Field(..., description="Window handle to receive the action")
    action_type: str = Field(..., description="Type of action: CLICK, DOUBLE_CLICK, RIGHT_CLICK, DRAG, TYPE_TEXT, KEY_PRESS, HOTKEY")
    x: Optional[int] = Field(default=None, description="Client-relative X coordinate")
    y: Optional[int] = Field(default=None, description="Client-relative Y coordinate")
    text: Optional[str] = Field(default=None, description="Text string for TYPE_TEXT")
    key: Optional[str] = Field(default=None, description="Key name or combo (e.g. 'enter', 'tab', 'ctrl+s')")


class GuiCaptureVirtualScreenArgs(BaseModel):
    session_id: str = Field(..., description="Target virtual desktop session ID")
    hwnd: Optional[int] = Field(default=None, description="Optional specific window handle to capture (default: top window)")


class GuiCloseIsolatedDesktopArgs(BaseModel):
    session_id: str = Field(..., description="Virtual desktop session ID to terminate and clean up")
