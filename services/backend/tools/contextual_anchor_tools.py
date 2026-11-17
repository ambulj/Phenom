"""
Phenom Active Desktop Focus & Contextual Semantic Anchor Tools (Milestone 51 Phase 4).

Registers:
- resolve_active_context_anchor (Tier 0)
- generate_contextual_action_proposals (Tier 0)
- validate_target_window_focus (Tier 0)
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.reflex import (
    contextual_anchor_manager,
    action_suggester,
    visual_sentinel,
    clipboard_sentinel,
)
from services.backend.schemas.reflex_events import ReflexEvent, ReflexEventType, ReflexSeverity, VisualCueDetails


class ResolveActiveContextAnchorArgs(BaseModel):
    window_title: Optional[str] = Field(default=None, description="Override window title for testing")
    process_name: Optional[str] = Field(default=None, description="Override process name for testing")


class GenerateContextualActionProposalsArgs(BaseModel):
    event_type: Optional[str] = Field(default=None, description="Optional ReflexEventType to correlate")
    active_file: Optional[str] = Field(default=None, description="Active editing file override")


class ValidateTargetWindowFocusArgs(BaseModel):
    target_hwnd: int = Field(default=0, description="Expected HWND")
    expected_process: str = Field(description="Expected executable name")


@registry.register(
    name="resolve_active_context_anchor",
    tier=0,
    description="Resolves active desktop foreground window into semantic project files and application categories.",
    args_schema=ResolveActiveContextAnchorArgs,
    preview_fn=lambda a: "Resolve active desktop foreground workspace and application context"
)
def resolve_active_context_anchor(
    window_title: Optional[str] = None,
    process_name: Optional[str] = None
) -> Dict[str, Any]:
    if window_title or process_name:
        from services.backend.schemas.semantic_focus import WindowContext, BoundingRect
        mock_ctx = WindowContext(
            hwnd=12345,
            title=window_title or "Code.exe",
            process_name=process_name or "Code.exe",
            pid=9999,
            bounding_rect=BoundingRect(left=0, top=0, right=1920, bottom=1080),
        )
        anchor = contextual_anchor_manager.resolve_anchor(mock_ctx)
    else:
        anchor = contextual_anchor_manager.resolve_anchor()

    return anchor.model_dump()


@registry.register(
    name="generate_contextual_action_proposals",
    tier=0,
    description="Synthesizes 1-click suggested remediation actions correlating active window and reflex events.",
    args_schema=GenerateContextualActionProposalsArgs,
    preview_fn=lambda a: f"Synthesize contextual action proposals for '{a.get('event_type') or 'active workspace'}'"
)
def generate_contextual_action_proposals(
    event_type: Optional[str] = None,
    active_file: Optional[str] = None
) -> Dict[str, Any]:
    anchor = contextual_anchor_manager.resolve_anchor()
    if active_file:
        anchor.active_file = active_file

    ev: Optional[ReflexEvent] = None
    if event_type:
        try:
            ev_type = ReflexEventType(event_type)
        except ValueError:
            ev_type = ReflexEventType.UNKNOWN

        ev = ReflexEvent(
            event_type=ev_type,
            severity=ReflexSeverity.CRITICAL if "FAIL" in event_type else ReflexSeverity.INFO,
            visual_details=VisualCueDetails(
                window_title=anchor.window_title,
                process_name=anchor.process_name,
            )
        )

    latest_clip = clipboard_sentinel.get_latest_item()
    proposals = action_suggester.generate_proposals(
        anchor=anchor,
        event=ev,
        clipboard_item=latest_clip,
    )

    return {
        "count": len(proposals),
        "anchor": anchor.model_dump(),
        "proposals": [p.model_dump() for p in proposals],
    }


@registry.register(
    name="validate_target_window_focus",
    tier=0,
    description="Focus Guard: Verifies target window is foreground before executing suggested actions.",
    args_schema=ValidateTargetWindowFocusArgs,
    preview_fn=lambda a: f"Verify target window focus on '{a.get('expected_process')}' (HWND {a.get('target_hwnd')})"
)
def validate_target_window_focus(target_hwnd: int, expected_process: str) -> Dict[str, Any]:
    valid, reason = action_suggester.validate_target_focus(target_hwnd, expected_process)
    return {
        "is_valid": valid,
        "message": reason,
        "target_hwnd": target_hwnd,
        "expected_process": expected_process,
    }
