"""Contextual Action Suggester & Focus Guard (Milestone 51 Phase 4).

Synthesizes validated 1-click suggested action proposals based on active desktop
context and reflex events, enforcing strict window focus verification prior to dispatch.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.schemas.reflex_events import ReflexEvent, ReflexEventType
from services.backend.reflex.contextual_anchor import ActiveContextAnchor, ApplicationCategory, ContextualAnchorManager
from services.backend.reflex.clipboard_sentinel import ClipboardItem
from services.backend.reflex.clipboard_classifier import ClipboardContentType
from services.backend.desktop.window_focus_tracker import WindowFocusTracker


class ContextualProposal(BaseModel):
    """Actionable 1-click remediation proposal staged for operator authorization."""
    proposal_id: str = Field(default_factory=lambda: f"prop_{uuid.uuid4().hex[:8]}")
    title: str = Field(description="Action title shown on CyberHUD button")
    tool_name: str = Field(description="Safety-registered tool name to execute")
    tool_args: Dict[str, Any] = Field(default_factory=dict, description="Pre-computed arguments")
    tier: int = Field(default=0, description="Risk tier: Tier 0 (auto/read-only) or Tier 1 (reversible)")
    target_hwnd: int = Field(default=0, description="Target window handle")
    target_process: str = Field(default="", description="Expected process name")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    explanation: str = Field(default="", description="Why this action is proposed")
    timestamp: float = Field(default_factory=time.time)


class ContextualActionSuggester:
    """Fuses desktop context with reflex events to generate verified proposals."""

    def __init__(
        self,
        anchor_mgr: Optional[ContextualAnchorManager] = None,
        tracker: Optional[WindowFocusTracker] = None
    ) -> None:
        self.tracker = tracker or WindowFocusTracker()
        self.anchor_mgr = anchor_mgr or ContextualAnchorManager(tracker=self.tracker)

    def generate_proposals(
        self,
        anchor: ActiveContextAnchor,
        event: Optional[ReflexEvent] = None,
        clipboard_item: Optional[ClipboardItem] = None
    ) -> List[ContextualProposal]:
        """Synthesizes actionable proposals from active context anchor and recent signals."""
        proposals: List[ContextualProposal] = []

        # 1. Evaluate from ReflexEvent
        if event:
            if event.event_type == ReflexEventType.TESTS_FAILED:
                proposals.append(ContextualProposal(
                    title="Re-run Failed Tests with Diagnostics",
                    tool_name="simulate_reflex_event",
                    tool_args={"event_type": "TESTS_FAILED", "message": "Re-running with verbose traceback"},
                    tier=0,
                    target_hwnd=anchor.hwnd,
                    target_process=anchor.process_name,
                    confidence=0.95,
                    explanation="Tests failed in active window. Proposing instant diagnostic re-run.",
                ))
            elif event.event_type == ReflexEventType.BUILD_FAILED:
                target_path = anchor.active_file or "src/index.ts"
                proposals.append(ContextualProposal(
                    title=f"Inspect Build Error in {target_path}",
                    tool_name="read_file",
                    tool_args={"path": target_path},
                    tier=0,
                    target_hwnd=anchor.hwnd,
                    target_process=anchor.process_name,
                    confidence=0.92,
                    explanation="Compilation error detected. Proposing automated file review.",
                ))
            elif event.event_type == ReflexEventType.TERMINAL_COMPLETED and event.is_success:
                proposals.append(ContextualProposal(
                    title="Acknowledge Clean Completion",
                    tool_name="inspect_reflex_sentinel_state",
                    tool_args={"include_recent": False},
                    tier=0,
                    target_hwnd=anchor.hwnd,
                    target_process=anchor.process_name,
                    confidence=0.88,
                    explanation="Long-running terminal task completed with code 0.",
                ))

        # 2. Evaluate from ClipboardItem
        if clipboard_item:
            c_type = clipboard_item.classification.content_type
            if c_type == ClipboardContentType.CODE and anchor.app_category == ApplicationCategory.IDE:
                proposals.append(ContextualProposal(
                    title=f"Stage Copied {clipboard_item.classification.sub_type or 'Code'} to Editor",
                    tool_name="capture_and_classify_clipboard",
                    tool_args={"content": clipboard_item.sanitized_text[:100]},
                    tier=0,
                    target_hwnd=anchor.hwnd,
                    target_process=anchor.process_name,
                    confidence=0.89,
                    explanation="Code snippet copied to clipboard while IDE is focused.",
                ))
            elif c_type == ClipboardContentType.JSON_DATA:
                proposals.append(ContextualProposal(
                    title="Format & Mirror Copied JSON",
                    tool_name="sync_clipboard_to_knowledge_graph",
                    tool_args={"item_id": clipboard_item.item_id},
                    tier=1,
                    target_hwnd=anchor.hwnd,
                    target_process=anchor.process_name,
                    confidence=0.91,
                    explanation="Valid JSON detected on clipboard; ready to persist in Knowledge Graph.",
                ))

        return proposals

    def validate_target_focus(self, target_hwnd: int, expected_process: str) -> Tuple[bool, str]:
        """Focus Guard: verifies target window is currently foreground before action dispatch.
        
        Guarantees that actions are never sent to shifted or misfocused windows (REFLEX-04.3).
        """
        current_ctx = self.tracker.get_active_window()

        if target_hwnd != 0 and current_ctx.hwnd != target_hwnd:
            return False, f"Focus divergence: Active HWND ({current_ctx.hwnd}) does not match target ({target_hwnd})"

        if expected_process and current_ctx.process_name.lower() != expected_process.lower():
            return False, f"Process divergence: Active '{current_ctx.process_name}' does not match target '{expected_process}'"

        return True, "Focus verified: Foreground window matches target."
