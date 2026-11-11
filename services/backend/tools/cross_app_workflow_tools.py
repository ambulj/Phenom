"""Safety-Wrapped Cross-App Workflow Tools.

Registers tools with ToolRegistry for multi-application data pipelining,
window focus synchronization, and ambient workflow tracking (Phase 25-03 AUT-05 / WIN-02).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.orchestrator.cross_app_orchestrator import (
    cross_app_orchestrator,
    CrossAppStep,
)
from services.backend.orchestrator.window_focus_synchronizer import window_focus_synchronizer


# ==========================================
# 1. Orchestrate Cross-App Workflow (Tier 1)
# ==========================================

class OrchestrateCrossAppWorkflowArgs(BaseModel):
    title: str = Field(..., description="Title of the cross-app workflow")
    steps: List[Dict[str, Any]] = Field(..., description="List of step dictionaries with app_name, action, and input_payload")


def orchestrate_cross_app_workflow_preview(args: Dict[str, Any]) -> str:
    title = args.get("title", "cross-app workflow")
    step_count = len(args.get("steps", []))
    return f"Orchestrate cross-app workflow '{title}' across {step_count} application step(s)."


@registry.register(
    name="orchestrate_cross_app_workflow",
    tier=1,
    description="Coordinates data extraction, transformation, and execution across multiple desktop applications.",
    args_schema=OrchestrateCrossAppWorkflowArgs,
    preview_fn=orchestrate_cross_app_workflow_preview,
    can_remember_per_folder=False,
)
def handle_orchestrate_cross_app_workflow(title: str, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    app_steps = [
        CrossAppStep(
            step_id=i + 1,
            app_name=s.get("app_name", "App"),
            action=s.get("action", "SYNC_STATE"),
            input_payload=s.get("input_payload"),
            output_variable=s.get("output_variable"),
        )
        for i, s in enumerate(steps)
    ]
    wf = cross_app_orchestrator.create_workflow(title=title, steps=app_steps)
    executed = cross_app_orchestrator.execute_workflow(wf.workflow_id)
    return executed.model_dump()


# ==========================================
# 2. Sync Window Workspace Focus (Tier 0)
# ==========================================

class SyncWindowWorkspaceFocusArgs(BaseModel):
    target_window: Optional[str] = Field(None, description="Window ID, process name, or title keyword to focus; omit to query layout")


def sync_window_workspace_focus_preview(args: Dict[str, Any]) -> str:
    target = args.get("target_window")
    if target:
        return f"Synchronize foreground window focus to target: '{target}'"
    return "Query active desktop window hierarchy and foreground focus layout."


@registry.register(
    name="sync_window_workspace_focus",
    tier=0,
    description="Queries desktop window layout or switches foreground focus to a specified application window.",
    args_schema=SyncWindowWorkspaceFocusArgs,
    preview_fn=sync_window_workspace_focus_preview,
    can_remember_per_folder=False,
)
def handle_sync_window_workspace_focus(target_window: Optional[str] = None) -> Dict[str, Any]:
    if target_window:
        focused = window_focus_synchronizer.switch_focus(target_window)
        return {"action": "FOCUS_SWITCHED", "window": focused.model_dump()}
    layout = window_focus_synchronizer.get_layout()
    return layout.model_dump()


# ==========================================
# 3. Get Ambient Workflow Status (Tier 0)
# ==========================================

class GetAmbientWorkflowStatusArgs(BaseModel):
    pass


def get_ambient_workflow_status_preview(args: Dict[str, Any]) -> str:
    return "Query ambient cross-application workflow state, shared context variables, and step execution progress."


@registry.register(
    name="get_ambient_workflow_status",
    tier=0,
    description="Returns the status, step results, and shared pipeline context of the active cross-app workflow.",
    args_schema=GetAmbientWorkflowStatusArgs,
    preview_fn=get_ambient_workflow_status_preview,
    can_remember_per_folder=False,
)
def handle_get_ambient_workflow_status() -> Dict[str, Any]:
    wf = cross_app_orchestrator.get_active_workflow()
    if not wf:
        return {"status": "NO_ACTIVE_WORKFLOW", "context": {}}
    return wf.model_dump()
