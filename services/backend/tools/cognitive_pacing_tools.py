"""Safety-Wrapped Cognitive Pacing Tools.

Registers tools with ToolRegistry for checking cognitive load states,
evaluating notification pacing decisions, and flushing deferred queues (Phase 26-04 COG-03 / PAC-01).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.pacing.cognitive_load_tracker import (
    cognitive_load_tracker,
    CognitiveStateReport,
)
from services.backend.pacing.attentional_pacer import (
    attentional_pacer,
    PacingDecision,
    PacedNotification,
)


# ==========================================
# 1. Get Cognitive Load State (Tier 0)
# ==========================================

class GetCognitiveLoadStateArgs(BaseModel):
    pass


def get_cognitive_load_state_preview(args: Dict[str, Any]) -> str:
    return "Retrieve user real-time cognitive load index, attentional focus state, and pacing queue."


@registry.register(
    name="get_cognitive_load_state",
    tier=0,
    description="Inspects real-time cognitive load score, attentional state, and deferred notification queue.",
    args_schema=GetCognitiveLoadStateArgs,
    preview_fn=get_cognitive_load_state_preview,
    can_remember_per_folder=False,
)
def handle_get_cognitive_load_state() -> Dict[str, Any]:
    state = cognitive_load_tracker.get_state()
    queue = attentional_pacer.get_deferred_queue()
    return {
        "cognitive_state": state.model_dump(),
        "deferred_queue_length": len(queue),
        "queued_notifications": [n.model_dump() for n in queue],
    }


# ==========================================
# 2. Pace Notification Dispatch (Tier 0)
# ==========================================

class PaceNotificationDispatchArgs(BaseModel):
    title: str = Field(..., description="Notification headline")
    body: str = Field(..., description="Notification body content")
    priority: str = Field("STANDARD_PROACTIVE", description="Priority level: CRITICAL_SAFETY, STANDARD_PROACTIVE, LOW_AMBIENT")


def pace_notification_dispatch_preview(args: Dict[str, Any]) -> str:
    title = args.get("title", "Untitled Notification")
    priority = args.get("priority", "STANDARD_PROACTIVE")
    return f"Evaluate cognitive pacing for notification '{title}' (priority: {priority})."


@registry.register(
    name="pace_notification_dispatch",
    tier=0,
    description="Evaluates cognitive load to determine whether to deliver notification immediately or queue it.",
    args_schema=PaceNotificationDispatchArgs,
    preview_fn=pace_notification_dispatch_preview,
    can_remember_per_folder=False,
)
def handle_pace_notification_dispatch(
    title: str,
    body: str,
    priority: str = "STANDARD_PROACTIVE",
) -> Dict[str, Any]:
    decision = attentional_pacer.evaluate_and_pace(title=title, body=body, priority=priority)
    return decision.model_dump()


# ==========================================
# 3. Flush Deferred Notifications (Tier 1)
# ==========================================

class FlushDeferredNotificationsArgs(BaseModel):
    pass


def flush_deferred_notifications_preview(args: Dict[str, Any]) -> str:
    return "Flush all queued deferred notifications to user desktop."


@registry.register(
    name="flush_deferred_notifications",
    tier=1,
    description="Flushes and delivers all pending notifications deferred during deep flow states.",
    args_schema=FlushDeferredNotificationsArgs,
    preview_fn=flush_deferred_notifications_preview,
    can_remember_per_folder=False,
)
def handle_flush_deferred_notifications() -> Dict[str, Any]:
    flushed = attentional_pacer.flush_deferred_queue()
    return {
        "status": "FLUSHED",
        "flushed_count": len(flushed),
        "notifications": [n.model_dump() for n in flushed],
    }
