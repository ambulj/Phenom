"""Semantic Focus & Window Guardian Tools Registration for Phenom (Milestone 49 Phase 3, GUI-01, GUI-02, GUI-03).

Exposes:
1. `verify_window_focus` (Tier 0) - Pre-action semantic verification of window title, PID, and bounds.
2. `get_active_window_context` (Tier 0) - Retrieves current foreground window context.
3. `check_anti_checkout_boundary` (Tier 0) - Evaluates window title and UI elements against Rule 8/5 barriers.
"""

from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.schemas.semantic_focus import (
    FocusVerificationRequest,
    FocusVerificationResult,
    WindowContext,
)
from services.backend.desktop.window_focus_tracker import WindowFocusTracker
from services.backend.desktop.semantic_focus_guard import SemanticFocusGuard
from services.backend.desktop.anti_checkout_shield import AntiCheckoutShield
from services.backend.desktop.human_takeover_hook import HumanTakeoverHook

# Singletons
focus_tracker = WindowFocusTracker()
semantic_guard = SemanticFocusGuard(tracker=focus_tracker)
anti_checkout_shield = AntiCheckoutShield()
takeover_hook = HumanTakeoverHook()


# ============================================================================
# 1. verify_window_focus (Tier 0)
# ============================================================================

class VerifyWindowFocusArgs(BaseModel):
    expected_title_contains: Optional[str] = Field(default=None, description="Expected substring in window title")
    expected_pid: Optional[int] = Field(default=None, description="Expected process ID")
    expected_process_name: Optional[str] = Field(default=None, description="Expected process executable name")
    target_x: Optional[int] = Field(default=None, description="Screen X coordinate")
    target_y: Optional[int] = Field(default=None, description="Screen Y coordinate")
    action_type: str = Field(default="CLICK", description="Action type")


def verify_window_focus_preview(args: Dict[str, Any]) -> str:
    title = args.get("expected_title_contains", "*")
    return f"Verify active desktop window matches expected target '{title}'."


@registry.register(
    name="verify_window_focus",
    tier=0,
    description="Pre-action verification ensuring target window title, PID, and coordinate bounds match expectations before input dispatch.",
    args_schema=VerifyWindowFocusArgs,
    preview_fn=verify_window_focus_preview,
    can_remember_per_folder=False,
)
def handle_verify_window_focus(
    expected_title_contains: Optional[str] = None,
    expected_pid: Optional[int] = None,
    expected_process_name: Optional[str] = None,
    target_x: Optional[int] = None,
    target_y: Optional[int] = None,
    action_type: str = "CLICK",
) -> Dict[str, Any]:
    coords = (target_x, target_y) if (target_x is not None and target_y is not None) else None
    req = FocusVerificationRequest(
        expected_title_contains=expected_title_contains,
        expected_pid=expected_pid,
        expected_process_name=expected_process_name,
        target_coordinates=coords,
        action_type=action_type,
    )
    res = semantic_guard.verify_focus(req)
    return {
        "status": "success" if res.is_valid else "mismatch",
        "is_valid": res.is_valid,
        "error_reason": res.error_reason,
        "latency_ms": res.latency_ms,
        "active_title": res.active_window.title if res.active_window else None,
        "active_pid": res.active_window.pid if res.active_window else None,
    }


# ============================================================================
# 2. get_active_window_context (Tier 0)
# ============================================================================

class GetActiveWindowContextArgs(BaseModel):
    pass


def get_active_window_context_preview(args: Dict[str, Any]) -> str:
    return "Query active foreground window title, PID, and bounding screen coordinates."


@registry.register(
    name="get_active_window_context",
    tier=0,
    description="Inspects and returns the active foreground desktop window context.",
    args_schema=GetActiveWindowContextArgs,
    preview_fn=get_active_window_context_preview,
    can_remember_per_folder=False,
)
def handle_get_active_window_context() -> Dict[str, Any]:
    ctx = focus_tracker.get_active_window()
    return {
        "hwnd": ctx.hwnd,
        "title": ctx.title,
        "process_name": ctx.process_name,
        "pid": ctx.pid,
        "bounds": ctx.bounding_rect.model_dump(),
        "is_minimized": ctx.is_minimized,
    }


# ============================================================================
# 3. check_anti_checkout_boundary (Tier 0)
# ============================================================================

class CheckAntiCheckoutBoundaryArgs(BaseModel):
    window_title: str = Field(..., description="Window title string to inspect")
    element_text: str = Field(default="", description="Text or label of control to interact with")


def check_anti_checkout_boundary_preview(args: Dict[str, Any]) -> str:
    title = args.get("window_title", "")
    return f"Inspect window '{title[:30]}' against Rule 8/5 payment and trading boundaries."


@registry.register(
    name="check_anti_checkout_boundary",
    tier=0,
    description="Inspects window title and element labels to guarantee automation does not touch checkout, payment, or trading screens.",
    args_schema=CheckAntiCheckoutBoundaryArgs,
    preview_fn=check_anti_checkout_boundary_preview,
    can_remember_per_folder=False,
)
def handle_check_anti_checkout_boundary(
    window_title: str,
    element_text: str = "",
) -> Dict[str, Any]:
    try:
        anti_checkout_shield.inspect_window_title(window_title)
        if element_text:
            from services.backend.schemas.semantic_focus import UIAElementDescriptor
            anti_checkout_shield.inspect_element(UIAElementDescriptor(name=element_text))
        return {"status": "safe", "is_safe": True, "message": "No payment or checkout indicators detected."}
    except Exception as e:
        return {"status": "blocked", "is_safe": False, "violation": str(e)}
