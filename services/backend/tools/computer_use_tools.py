"""MULTI-MODAL ACTION AGENT: Desktop Computer-Use Tools.

Milestone 45.0: Project MULTI-MODAL ACTION AGENT (Phase 3)

Registers:
1. execute_desktop_click (Tier 1):
   Dispatches a smooth Bezier mouse click to a grounded visual element or coordinate.
2. execute_desktop_keystrokes (Tier 1):
   Dispatches natural human-like keystrokes with randomized micro-delays.
3. execute_desktop_action_sequence (Tier 1):
   Executes an atomic batch sequence of clicks, keystrokes, and hotkeys.
4. resolve_visual_target_coordinates (Tier 0):
   Resolves an on-screen visual element/text to pixel coordinates with Rule 8 anti-checkout checks.
5. get_computer_use_status (Tier 0):
   Returns computer-use controller telemetry, active cursor position, and Guardian halt state.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.actions.synthetic_input import synthetic_input
from services.backend.actions.visual_grounder import visual_grounder, Rule8ViolationError, PrivacyShieldError
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.computer_use import (
    ActionSequencePayload,
    ClickAction,
    ClickType,
    ExecutionResult,
    HotKeyAction,
    MoveAction,
    Point2D,
    ScrollAction,
    TypeAction,
)


# ==========================================
# 1. Execute Desktop Click (Tier 1)
# ==========================================

class ExecuteDesktopClickArgs(BaseModel):
    target_text: Optional[str] = Field(None, description="Visual text or icon to resolve and click")
    target_x: Optional[int] = Field(None, ge=0, description="Explicit X coordinate")
    target_y: Optional[int] = Field(None, ge=0, description="Explicit Y coordinate")
    click_type: str = Field("left", description="'left', 'right', 'double', or 'middle'")
    smooth: bool = Field(True, description="Whether to glide cursor along smooth cubic Bezier curve")


def preview_execute_desktop_click(args: Dict[str, Any]) -> str:
    target = args.get("target_text") or f"({args.get('target_x')}, {args.get('target_y')})"
    return f"Click desktop element: {target} ({args.get('click_type', 'left')} click)"


@registry.register(
    name="execute_desktop_click",
    tier=1,
    description="Clicks an on-screen desktop element or coordinate with smooth human-like Bezier cursor movement (Tier 1).",
    args_schema=ExecuteDesktopClickArgs,
    preview_fn=preview_execute_desktop_click,
    can_remember_per_folder=False,
)
def handle_execute_desktop_click(
    target_text: Optional[str] = None,
    target_x: Optional[int] = None,
    target_y: Optional[int] = None,
    click_type: str = "left",
    smooth: bool = True,
) -> Dict[str, Any]:
    if guardian.is_halted:
        return {"success": False, "error": "Guardian Kill Switch is active", "guardian_halted": True}

    pt: Optional[Point2D] = None
    grounding_meta: Dict[str, Any] = {}

    if target_x is not None and target_y is not None:
        pt = Point2D(x=target_x, y=target_y)
    elif target_text:
        try:
            pt, _, grounding_meta = visual_grounder.resolve_target(target_text)
        except (Rule8ViolationError, PrivacyShieldError, Exception) as e:
            return {"success": False, "error": str(e), "target": target_text}
    else:
        return {"success": False, "error": "Must specify either target_text or target_x/target_y coordinates"}

    c_type = ClickType.LEFT
    try:
        c_type = ClickType(click_type.lower())
    except ValueError:
        pass

    action = ClickAction(target=pt, click_type=c_type, smooth_move=smooth)
    ok = synthetic_input.click(action)
    return {
        "success": ok,
        "clicked_point": {"x": pt.x, "y": pt.y},
        "click_type": c_type.value,
        "grounding": grounding_meta,
        "guardian_halted": guardian.is_halted,
    }


# ==========================================
# 2. Execute Desktop Keystrokes (Tier 1)
# ==========================================

class ExecuteDesktopKeystrokesArgs(BaseModel):
    text: str = Field(..., description="Text characters to type")
    target_text: Optional[str] = Field(None, description="Optional target element to focus/click before typing")
    press_enter: bool = Field(False, description="Whether to press Enter key after typing")


def preview_execute_desktop_keystrokes(args: Dict[str, Any]) -> str:
    preview = args.get("text", "")
    if len(preview) > 30:
        preview = preview[:30] + "..."
    return f"Type text: '{preview}'" + (" (and Enter)" if args.get("press_enter") else "")


@registry.register(
    name="execute_desktop_keystrokes",
    tier=1,
    description="Types text into the active desktop window with natural typing cadence and micro-delays (Tier 1).",
    args_schema=ExecuteDesktopKeystrokesArgs,
    preview_fn=preview_execute_desktop_keystrokes,
    can_remember_per_folder=False,
)
def handle_execute_desktop_keystrokes(
    text: str,
    target_text: Optional[str] = None,
    press_enter: bool = False,
) -> Dict[str, Any]:
    if guardian.is_halted:
        return {"success": False, "error": "Guardian Kill Switch is active", "guardian_halted": True}

    focus_pt: Optional[Point2D] = None
    if target_text:
        try:
            focus_pt, _, _ = visual_grounder.resolve_target(target_text)
        except Exception as e:
            return {"success": False, "error": f"Failed to focus '{target_text}': {e}"}

    action = TypeAction(text=text, press_enter=press_enter, focus_target=focus_pt)
    ok = synthetic_input.type_text(action)
    return {
        "success": ok,
        "characters_typed": len(text),
        "pressed_enter": press_enter,
        "focused_target": {"x": focus_pt.x, "y": focus_pt.y} if focus_pt else None,
        "guardian_halted": guardian.is_halted,
    }


# ==========================================
# 3. Execute Desktop Action Sequence (Tier 1)
# ==========================================

class ExecuteDesktopActionSequenceArgs(BaseModel):
    actions: List[Dict[str, Any]] = Field(..., description="List of action payloads (click, move, type, hotkey, scroll)")
    target_window_title: Optional[str] = Field(None, description="Optional window title to focus before execution")


def preview_execute_desktop_action_sequence(args: Dict[str, Any]) -> str:
    count = len(args.get("actions", []))
    return f"Execute batch of {count} desktop actions"


@registry.register(
    name="execute_desktop_action_sequence",
    tier=1,
    description="Executes a batch sequence of desktop clicks, keystrokes, hotkeys, and mouse moves with atomic Guardian abort (Tier 1).",
    args_schema=ExecuteDesktopActionSequenceArgs,
    preview_fn=preview_execute_desktop_action_sequence,
    can_remember_per_folder=False,
)
def handle_execute_desktop_action_sequence(
    actions: List[Dict[str, Any]],
    target_window_title: Optional[str] = None,
) -> Dict[str, Any]:
    if guardian.is_halted:
        return {"success": False, "error": "Guardian Kill Switch is active", "guardian_halted": True}

    parsed_actions = []
    for item in actions:
        act_type = item.get("action_type") or item.get("type", "click")
        if act_type == "click":
            pt = Point2D(x=item.get("x", 0), y=item.get("y", 0))
            parsed_actions.append(ClickAction(target=pt, click_type=ClickType(item.get("click_type", "left"))))
        elif act_type == "type":
            parsed_actions.append(TypeAction(text=item.get("text", ""), press_enter=item.get("press_enter", False)))
        elif act_type == "hotkey":
            parsed_actions.append(HotKeyAction(keys=item.get("keys", [])))
        elif act_type == "move":
            pt = Point2D(x=item.get("x", 0), y=item.get("y", 0))
            parsed_actions.append(MoveAction(target=pt, duration_ms=item.get("duration_ms", 200.0)))
        elif act_type == "scroll":
            parsed_actions.append(ScrollAction(clicks=item.get("clicks", 0)))

    payload = ActionSequencePayload(
        actions=parsed_actions,
        target_window_title=target_window_title,
    )
    result = synthetic_input.execute_sequence(payload)
    return result.model_dump()


# ==========================================
# 4. Resolve Visual Target Coordinates (Tier 0)
# ==========================================

class ResolveVisualTargetCoordinatesArgs(BaseModel):
    query: str = Field(..., description="Element text or icon name to resolve")
    allow_cloud_escalation: bool = Field(True, description="Whether to escalate non-text targets to Cloud Vision")


def preview_resolve_visual_target_coordinates(args: Dict[str, Any]) -> str:
    return f"Resolve coordinates for desktop target: '{args.get('query')}'"


@registry.register(
    name="resolve_visual_target_coordinates",
    tier=0,
    description="Resolves on-screen text or icon queries to pixel coordinates via local OCR or Cloud Vision with Rule 8 Anti-Checkout protection (Tier 0).",
    args_schema=ResolveVisualTargetCoordinatesArgs,
    preview_fn=preview_resolve_visual_target_coordinates,
    can_remember_per_folder=False,
)
def handle_resolve_visual_target_coordinates(
    query: str,
    allow_cloud_escalation: bool = True,
) -> Dict[str, Any]:
    if guardian.is_halted:
        return {"success": False, "error": "Guardian Kill Switch is active", "guardian_halted": True}

    try:
        pt, layer, meta = visual_grounder.resolve_target(
            query=query,
            allow_cloud_escalation=allow_cloud_escalation,
        )
        return {
            "success": True,
            "target": query,
            "coordinate": {"x": pt.x, "y": pt.y},
            "layer": layer,
            "metadata": meta,
        }
    except Rule8ViolationError as e:
        return {"success": False, "error": str(e), "rule_8_violation": True}
    except PrivacyShieldError as e:
        return {"success": False, "error": str(e), "privacy_shield_active": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==========================================
# 5. Get Computer Use Status (Tier 0)
# ==========================================

class GetComputerUseStatusArgs(BaseModel):
    pass


def preview_get_computer_use_status(args: Dict[str, Any]) -> str:
    return "Query computer-use action agent status and active cursor position"


@registry.register(
    name="get_computer_use_status",
    tier=0,
    description="Returns computer-use controller status, active cursor position, and Guardian halt state (Tier 0).",
    args_schema=GetComputerUseStatusArgs,
    preview_fn=preview_get_computer_use_status,
    can_remember_per_folder=False,
)
def handle_get_computer_use_status() -> Dict[str, Any]:
    cursor = synthetic_input.get_cursor_position()
    return {
        "is_halted": guardian.is_halted,
        "cursor_position": {"x": cursor.x, "y": cursor.y},
        "dry_run": synthetic_input.dry_run,
        "recorded_events_count": len(synthetic_input.recorded_events),
    }
