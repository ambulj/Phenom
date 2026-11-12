"""Safety-Wrapped Desktop Watchdog Tools.

Registers tools with ToolRegistry for incident inspection, proactive alert resolution,
and sensitivity configuration (Phase 25-04 DOG-01 / INT-03).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.watchdog.desktop_watchdog import desktop_watchdog
from services.backend.watchdog.proactive_task_interceptor import proactive_task_interceptor


# ==========================================
# 1. Inspect Desktop Watchdog Events (Tier 0)
# ==========================================

class InspectDesktopWatchdogEventsArgs(BaseModel):
    unresolved_only: bool = Field(True, description="Whether to return only unresolved incidents")


def inspect_desktop_watchdog_events_preview(args: Dict[str, Any]) -> str:
    unresolved = args.get("unresolved_only", True)
    scope = "unresolved incidents" if unresolved else "all historical events"
    return f"Inspect desktop watchdog incident logs and health score ({scope})."


@registry.register(
    name="inspect_desktop_watchdog_events",
    tier=0,
    description="Returns current desktop watchdog incidents, system health rating, and active proactive intervention cards.",
    args_schema=InspectDesktopWatchdogEventsArgs,
    preview_fn=inspect_desktop_watchdog_events_preview,
    can_remember_per_folder=False,
)
def handle_inspect_desktop_watchdog_events(unresolved_only: bool = True) -> Dict[str, Any]:
    incidents = desktop_watchdog.get_active_incidents(unresolved_only=unresolved_only)
    cards = proactive_task_interceptor.get_active_cards()
    health = desktop_watchdog.get_system_health()
    return {
        "health": health,
        "incident_count": len(incidents),
        "incidents": [i.model_dump() for i in incidents],
        "active_cards": [c.model_dump() for c in cards],
    }


# ==========================================
# 2. Resolve Proactive Alert (Tier 1)
# ==========================================

class ResolveProactiveAlertArgs(BaseModel):
    card_id: str = Field(..., description="ID of the intervention card to resolve or dismiss")
    action: str = Field("EXECUTE", description="Action to take: 'EXECUTE' or 'DISMISS'")


def resolve_proactive_alert_preview(args: Dict[str, Any]) -> str:
    card_id = args.get("card_id", "unspecified")
    action = args.get("action", "EXECUTE")
    return f"Resolve proactive desktop intervention card '{card_id}' with action: {action}."


@registry.register(
    name="resolve_proactive_alert",
    tier=1,
    description="Executes a recommended self-healing remediation or soft-dismisses a proactive alert card.",
    args_schema=ResolveProactiveAlertArgs,
    preview_fn=resolve_proactive_alert_preview,
    can_remember_per_folder=False,
)
def handle_resolve_proactive_alert(card_id: str, action: str = "EXECUTE") -> Dict[str, Any]:
    if action.upper() == "DISMISS":
        success = proactive_task_interceptor.dismiss_intervention(card_id)
        return {"card_id": card_id, "status": "DISMISSED", "success": success}
    result = proactive_task_interceptor.execute_intervention(card_id)
    return result


# ==========================================
# 3. Configure Watchdog Policies (Tier 1)
# ==========================================

class ConfigureWatchdogPoliciesArgs(BaseModel):
    sensitivity_mode: str = Field(..., description="Alert sensitivity mode: 'CONSERVATIVE', 'BALANCED', or 'AGGRESSIVE'")


def configure_watchdog_policies_preview(args: Dict[str, Any]) -> str:
    mode = args.get("sensitivity_mode", "BALANCED")
    return f"Set desktop watchdog incident sensitivity policy to '{mode}'."


@registry.register(
    name="configure_watchdog_policies",
    tier=1,
    description="Adjusts the desktop watchdog event detection threshold and notification policy.",
    args_schema=ConfigureWatchdogPoliciesArgs,
    preview_fn=configure_watchdog_policies_preview,
    can_remember_per_folder=False,
)
def handle_configure_watchdog_policies(sensitivity_mode: str) -> Dict[str, Any]:
    updated_mode = desktop_watchdog.set_sensitivity(sensitivity_mode)
    return {"status": "UPDATED", "sensitivity_mode": updated_mode}
