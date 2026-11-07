"""
Phenom Hybrid Screen Vision & GUI Automation Tools (SAF-01 & SAF-02).
Registers Milestone 19 Phase 2 tools in ToolRegistry:
1. capture_smart_screen (Tier 0)
2. gui_find_and_click_element (Tier 0 for safe navigation, Tier 1 if mutating)
3. gui_type_text (Tier 1)
4. get_focused_window_info (Tier 0)
All tools enforce strict Rule 8 checkout/password shields and Guardian SLA integration.
"""

from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.vision.screen_capture import smart_screen_capture
from services.backend.automation.gui_controller import (
    hybrid_gui_controller,
    Rule8ViolationError,
    GuardianHaltedError,
)


class CaptureSmartScreenArgs(BaseModel):
    mode: str = Field(
        default="focused_window",
        description="Capture mode: 'focused_window' for active app or 'full_desktop' for primary display"
    )
    mask_privacy: bool = Field(
        default=True,
        description="Whether to apply Rule 4/8 privacy masking to sensitive cards and password fields"
    )


class GuiFindAndClickElementArgs(BaseModel):
    target_name: str = Field(
        ...,
        description="Name, label, or visual descriptor of the UI element to click"
    )
    autonomous_silent: bool = Field(
        default=True,
        description="Whether safe navigation clicks execute autonomously without prompting"
    )


class GuiTypeTextArgs(BaseModel):
    text: str = Field(
        ...,
        description="Text string to type into the active field (Rule 8: passwords permanently blocked)"
    )
    target_field: Optional[str] = Field(
        default=None,
        description="Optional name of the target text input field"
    )


class GetFocusedWindowInfoArgs(BaseModel):
    pass


@registry.register(
    name="capture_smart_screen",
    tier=0,
    description="Captures active window or full desktop in RAM with privacy masking. Zero disk writes.",
    args_schema=CaptureSmartScreenArgs,
    preview_fn=lambda a: f"Capture screen context ({getattr(a, 'mode', 'focused_window')}) in memory"
)
async def capture_smart_screen(
    mode: str = "focused_window",
    mask_privacy: bool = True
) -> Dict[str, Any]:
    """Captures the screen and returns metadata with base64 data URI."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    img, metadata = smart_screen_capture.capture(mode=mode, mask_privacy=mask_privacy)
    data_uri = smart_screen_capture.to_base64_data_uri(img, quality=80)
    img.close()  # Memory isolation
    return {
        **metadata,
        "data_uri_preview": data_uri[:100] + "...",
        "image_bytes_len": len(data_uri)
    }


@registry.register(
    name="gui_find_and_click_element",
    tier=0,
    description="Locates and clicks a desktop UI element via deterministic UIA tree with visual fallback. Protected by Rule 8.",
    args_schema=GuiFindAndClickElementArgs,
    preview_fn=lambda a: f"Click UI element '{getattr(a, 'target_name', 'element')}'"
)
async def gui_find_and_click_element(
    target_name: str,
    autonomous_silent: bool = True
) -> Dict[str, Any]:
    """Clicks an element using hybrid UIA and visual resolution."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    res = await hybrid_gui_controller.click_element(target_name, autonomous_silent=autonomous_silent)
    return {
        "status": res.status,
        "target": res.target,
        "strategy": res.resolution_strategy,
        "coords": res.coords,
        "bounding_rect": res.bounding_rect,
        "latency_ms": res.latency_ms,
        "error": res.error
    }


@registry.register(
    name="gui_type_text",
    tier=1,
    description="Types text into an active input field. Rule 8 forbids typing passwords or CVVs.",
    args_schema=GuiTypeTextArgs,
    preview_fn=lambda a: f"Type text into '{getattr(a, 'target_field', 'active field') or 'active field'}'"
)
async def gui_type_text(
    text: str,
    target_field: Optional[str] = None
) -> Dict[str, Any]:
    """Injects keyboard input into active application field."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    res = await hybrid_gui_controller.type_text(text, target_field=target_field)
    return {
        "status": res.status,
        "target": res.target,
        "latency_ms": res.latency_ms,
        "error": res.error
    }


@registry.register(
    name="get_focused_window_info",
    tier=0,
    description="Returns metadata about the active foreground window (title, rect, sensitivity).",
    args_schema=GetFocusedWindowInfoArgs,
    preview_fn=lambda a: "Inspect active foreground window details (Read-only)"
)
async def get_focused_window_info() -> Dict[str, Any]:
    """Returns foreground window inspection data."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    return smart_screen_capture.get_focused_window_info()
