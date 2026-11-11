"""Sovereign Cross-Application Workflow Orchestration Tools for Phenom (Milestone 32 Phase 1).

Registers 4 specialized tools in ToolRegistry:
1. create_cross_app_workflow (Tier 1)
2. execute_workflow_step (Tier 1)
3. get_workflow_execution_status (Tier 0)
4. abort_and_rollback_workflow (Tier 1)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.orchestration.workflow_engine import (
    workflow_engine,
    WorkflowStep,
    StepActionType,
    VerificationType,
    StepVerification,
)


# ==========================================
# 1. Create Cross-App Workflow (Tier 1)
# ==========================================

class CreateWorkflowStepArg(BaseModel):
    id: str = Field(..., description="Unique ID for this step in the DAG.")
    name: str = Field(..., description="Human-readable step name.")
    action_type: StepActionType = Field(..., description="Action type: SHELL_COMMAND, FILE_OPERATION, OBSIDIAN_NOTE, BROWSER_ACTION, DESKTOP_GUI, CUSTOM_TOOL.")
    target_app: str = Field("terminal", description="Target application (e.g. terminal, obsidian, browser, vscode).")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action arguments and command parameters.")
    dependencies: List[str] = Field(default_factory=list, description="IDs of prerequisite steps.")
    pre_check: Optional[Dict[str, Any]] = Field(None, description="Optional pre-execution verification.")
    post_check: Optional[Dict[str, Any]] = Field(None, description="Optional post-execution verification.")
    rollback_payload: Optional[Dict[str, Any]] = Field(None, description="Optional compensatory rollback payload.")


class CreateCrossAppWorkflowArgs(BaseModel):
    name: str = Field(..., description="Name of the cross-application workflow.")
    description: str = Field(..., description="Description of the workflow goal and applications involved.")
    steps: List[CreateWorkflowStepArg] = Field(..., description="List of DAG steps.")
    initial_variables: Optional[Dict[str, Any]] = Field(None, description="Initial key-value context variables.")


def preview_create_cross_app_workflow(args: Dict[str, Any]) -> str:
    name = args.get("name", "Workflow")
    steps = args.get("steps", [])
    return f"Create cross-app workflow '{name}' with {len(steps)} steps"


@registry.register(
    name="create_cross_app_workflow",
    tier=1,
    description="Creates and stages a multi-step cross-application workflow DAG with verification checkpoints (Tier 1 staging).",
    args_schema=CreateCrossAppWorkflowArgs,
    preview_fn=preview_create_cross_app_workflow,
    can_remember_per_folder=False,
)
def handle_create_cross_app_workflow(
    name: str,
    description: str,
    steps: List[Dict[str, Any]],
    initial_variables: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    wf_steps: List[WorkflowStep] = []
    for s_raw in steps:
        if isinstance(s_raw, dict):
            pre_check = None
            if s_raw.get("pre_check"):
                pre_c = s_raw["pre_check"]
                pre_check = StepVerification(
                    verification_type=VerificationType(pre_c["verification_type"]),
                    target=pre_c["target"],
                    expected_value=pre_c.get("expected_value"),
                )

            post_check = None
            if s_raw.get("post_check"):
                post_c = s_raw["post_check"]
                post_check = StepVerification(
                    verification_type=VerificationType(post_c["verification_type"]),
                    target=post_c["target"],
                    expected_value=post_c.get("expected_value"),
                )

            step = WorkflowStep(
                id=s_raw["id"],
                name=s_raw["name"],
                action_type=StepActionType(s_raw["action_type"]),
                target_app=s_raw.get("target_app", "terminal"),
                payload=s_raw.get("payload", {}),
                dependencies=s_raw.get("dependencies", []),
                pre_check=pre_check,
                post_check=post_check,
                rollback_payload=s_raw.get("rollback_payload"),
            )
            wf_steps.append(step)
        elif isinstance(s_raw, CreateWorkflowStepArg):
            step = WorkflowStep(
                id=s_raw.id,
                name=s_raw.name,
                action_type=s_raw.action_type,
                target_app=s_raw.target_app,
                payload=s_raw.payload,
                dependencies=s_raw.dependencies,
                rollback_payload=s_raw.rollback_payload,
            )
            wf_steps.append(step)

    dag = workflow_engine.create_workflow(
        name=name,
        description=description,
        steps=wf_steps,
        initial_variables=initial_variables,
    )
    return dag.model_dump()


# ==========================================
# 2. Execute Workflow Step (Tier 1)
# ==========================================

class ExecuteWorkflowStepArgs(BaseModel):
    workflow_id: str = Field(..., description="ID of the target workflow DAG.")
    step_id: str = Field(..., description="ID of the specific step to execute.")


def preview_execute_workflow_step(args: Dict[str, Any]) -> str:
    wf = args.get("workflow_id", "")
    step = args.get("step_id", "")
    return f"Execute step '{step}' in workflow '{wf}'"


@registry.register(
    name="execute_workflow_step",
    tier=1,
    description="Executes a verified step in a cross-application workflow DAG (Tier 1 execution).",
    args_schema=ExecuteWorkflowStepArgs,
    preview_fn=preview_execute_workflow_step,
    can_remember_per_folder=False,
)
def handle_execute_workflow_step(workflow_id: str, step_id: str) -> Dict[str, Any]:
    step = workflow_engine.execute_step(workflow_id, step_id)
    return step.model_dump()


# ==========================================
# 3. Get Workflow Execution Status (Tier 0)
# ==========================================

class GetWorkflowExecutionStatusArgs(BaseModel):
    workflow_id: str = Field(..., description="ID of the workflow to query.")


def preview_get_workflow_execution_status(args: Dict[str, Any]) -> str:
    wf = args.get("workflow_id", "")
    return f"Query status of workflow '{wf}'"


@registry.register(
    name="get_workflow_execution_status",
    tier=0,
    description="Returns read-only execution progress, step states, and variable store of a workflow (Tier 0 read-only).",
    args_schema=GetWorkflowExecutionStatusArgs,
    preview_fn=preview_get_workflow_execution_status,
    can_remember_per_folder=False,
)
def handle_get_workflow_execution_status(workflow_id: str) -> Dict[str, Any]:
    status = workflow_engine.get_workflow_status(workflow_id)
    return status


# ==========================================
# 4. Abort and Rollback Workflow (Tier 1)
# ==========================================

class AbortAndRollbackWorkflowArgs(BaseModel):
    workflow_id: str = Field(..., description="ID of the workflow to abort and roll back.")


def preview_abort_and_rollback_workflow(args: Dict[str, Any]) -> str:
    wf = args.get("workflow_id", "")
    return f"Abort and trigger compensatory rollback for workflow '{wf}'"


@registry.register(
    name="abort_and_rollback_workflow",
    tier=1,
    description="Aborts an active workflow and executes compensatory rollbacks for completed steps in reverse order (Tier 1 rollback).",
    args_schema=AbortAndRollbackWorkflowArgs,
    preview_fn=preview_abort_and_rollback_workflow,
    can_remember_per_folder=False,
)
def handle_abort_and_rollback_workflow(workflow_id: str) -> Dict[str, Any]:
    rolled_back = workflow_engine.rollback_workflow(workflow_id)
    return {
        "workflow_id": workflow_id,
        "status": "ROLLED_BACK",
        "rolled_back_steps": rolled_back,
        "count": len(rolled_back),
    }
