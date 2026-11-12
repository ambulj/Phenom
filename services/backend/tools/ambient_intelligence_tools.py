"""
Safety-Wrapped Proactive Ambient Intelligence & Notification Tools.
Registers tools with ToolRegistry for ambient alert feeds, dynamic focus filtering,
and proactive briefing synthesis (Phase 22-04 AMB-02 / NOT-02).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.ambient.ambient_intelligence_daemon import (
    ambient_daemon,
    AmbientAlertItem,
)
from services.backend.ambient.notification_priority_hub import priority_hub


# ==========================================
# 1. Get Ambient Intelligence Feed (Tier 0)
# ==========================================

class GetAmbientIntelligenceFeedArgs(BaseModel):
    min_urgency: Optional[float] = Field(default=None, description="Optional minimum urgency threshold (0.0 to 1.0)")

def get_ambient_intelligence_feed_preview(args: Dict[str, Any]) -> str:
    u = args.get("min_urgency")
    u_txt = f" (min urgency {u})" if u is not None else ""
    return f"Inspect proactive ambient intelligence feed and focus filtering status{u_txt}."

@registry.register(
    name="get_ambient_intelligence_feed",
    tier=0,
    description="Returns prioritized ambient alerts, delivery decisions, and active focus threshold telemetry.",
    args_schema=GetAmbientIntelligenceFeedArgs,
    preview_fn=get_ambient_intelligence_feed_preview,
    can_remember_per_folder=False
)
def handle_get_ambient_intelligence_feed(
    min_urgency: Optional[float] = None
) -> Dict[str, Any]:
    if min_urgency is not None:
        alerts = ambient_daemon.get_active_alerts(min_urgency=min_urgency)
        return {
            "mode": "filtered_by_urgency",
            "min_urgency": min_urgency,
            "alerts": [a.model_dump() for a in alerts],
        }
    return priority_hub.get_filtered_feed()


# ==========================================
# 2. Configure Notification Filter (Tier 0)
# ==========================================

class ConfigureNotificationFilterArgs(BaseModel):
    mode: str = Field(..., description="Focus mode: 'deep_focus', 'balanced', 'ambient'")
    custom_threshold: Optional[float] = Field(default=None, description="Optional explicit threshold (0.0 to 1.0)")

def configure_notification_filter_preview(args: Dict[str, Any]) -> str:
    m = args.get("mode", "mode")
    return f"Set proactive notification filter mode to '{m}'."

@registry.register(
    name="configure_notification_filter",
    tier=0,
    description="Adjusts the focus threshold to regulate alert delivery during deep work or ambient monitoring.",
    args_schema=ConfigureNotificationFilterArgs,
    preview_fn=configure_notification_filter_preview,
    can_remember_per_folder=False
)
def handle_configure_notification_filter(
    mode: str,
    custom_threshold: Optional[float] = None
) -> Dict[str, Any]:
    return priority_hub.set_mode(mode=mode, custom_threshold=custom_threshold)


# ==========================================
# 3. Dismiss Ambient Alert (Tier 0)
# ==========================================

class DismissAmbientAlertArgs(BaseModel):
    alert_id: str = Field(..., description="Alert identifier to dismiss")

def dismiss_ambient_alert_preview(args: Dict[str, Any]) -> str:
    aid = args.get("alert_id", "alert")
    return f"Soft-dismiss ambient alert '{aid}' (Rule 7 non-destructive archive)."

@registry.register(
    name="dismiss_ambient_alert",
    tier=0,
    description="Soft-dismisses an active ambient alert without deleting historical telemetry.",
    args_schema=DismissAmbientAlertArgs,
    preview_fn=dismiss_ambient_alert_preview,
    can_remember_per_folder=False
)
def handle_dismiss_ambient_alert(alert_id: str) -> Dict[str, Any]:
    success = ambient_daemon.dismiss_alert(alert_id)
    return {"alert_id": alert_id, "dismissed": success}


# ==========================================
# 4. Synthesize Proactive Briefing (Tier 0)
# ==========================================

class SynthesizeProactiveBriefingArgs(BaseModel):
    pass

def synthesize_proactive_briefing_preview(args: Dict[str, Any]) -> str:
    return "Synthesize conversational overview of current ambient alerts, system health, and upcoming tasks."

@registry.register(
    name="synthesize_proactive_briefing",
    tier=0,
    description="Generates a natural-language briefing summarizing active alerts, system resources, and pending tasks.",
    args_schema=SynthesizeProactiveBriefingArgs,
    preview_fn=synthesize_proactive_briefing_preview,
    can_remember_per_folder=False
)
def handle_synthesize_proactive_briefing() -> Dict[str, Any]:
    return ambient_daemon.synthesize_proactive_briefing()


# Programmatic aliases
get_ambient_intelligence_feed = handle_get_ambient_intelligence_feed
configure_notification_filter = handle_configure_notification_filter
dismiss_ambient_alert = handle_dismiss_ambient_alert
synthesize_proactive_briefing = handle_synthesize_proactive_briefing
