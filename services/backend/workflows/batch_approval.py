"""
Phenom Autonomous Workflow Batch Approval & Execution Engine
Enforces:
- Upfront batch review and 1-click authorization
- Automated pre-condition divergence detection (window mismatch, missing files)
- Immediate safety pause on divergence with CyberHUD alert
- Real-time WebSocket event emission
"""

import os
import sys
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple, Callable, Awaitable
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.safety.engine import safety_engine
from services.backend.workflows.dag_planner import WorkflowDAG, WorkflowStep, dag_planner

logger = logging.getLogger("phenom.workflows.batch_approval")


_broadcaster: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None

def register_broadcaster(broadcaster: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
    global _broadcaster
    _broadcaster = broadcaster

def broadcast_workflow_event(event_type: str, payload: Dict[str, Any]) -> None:
    broadcaster = _broadcaster
    if not broadcaster:
        main_mod = sys.modules.get("services.backend.main")
        if main_mod and hasattr(main_mod, "broadcast_message"):
            broadcaster = main_mod.broadcast_message
    if not broadcaster:
        return
    msg = {
        "id": f"wkf-{os.urandom(2).hex()}",
        "type": event_type,
        "ts": str(time.time()),
        "payload": payload
    }
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcaster(msg))
    except RuntimeError:
        main_mod = sys.modules.get("services.backend.main")
        main_loop = getattr(main_mod, "main_loop", None)
        if main_loop and main_loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcaster(msg), main_loop)


class WorkflowExecutionManager:
    """Manages DAG storage, pre-condition checks, batch approval, and execution."""

    def __init__(self):
        self._dags: Dict[str, WorkflowDAG] = {}
        self._active_dag_id: Optional[str] = None

    def create_dag(self, goal: str, explicit_steps: Optional[List[Dict[str, Any]]] = None) -> WorkflowDAG:
        dag = dag_planner.plan(goal, explicit_steps)
        self._dags[dag.dag_id] = dag
        self._active_dag_id = dag.dag_id
        broadcast_workflow_event("WORKFLOW_DAG_CREATED", dag.model_dump())
        return dag

    def get_dag(self, dag_id: str) -> Optional[WorkflowDAG]:
        return self._dags.get(dag_id)

    def approve_batch(self, dag_id: str) -> WorkflowDAG:
        dag = self.get_dag(dag_id)
        if not dag:
            raise ValueError(f"Workflow DAG '{dag_id}' not found.")
        dag.status = "approved"
        dag.approved_at = time.time()
        broadcast_workflow_event("WORKFLOW_DAG_APPROVED", {"dag_id": dag_id, "status": "approved"})
        return dag

    def check_precondition(self, step: WorkflowStep) -> Tuple[bool, Optional[str]]:
        """Verifies environment state matches step preconditions before execution."""
        pre = step.precondition
        if not pre:
            return True, None

        # Check required file exists
        if pre.file_must_exist:
            if not os.path.exists(pre.file_must_exist):
                reason = f"Required file '{pre.file_must_exist}' does not exist on disk."
                return False, reason

        # Check process / window if specified
        if pre.expected_process_name:
            try:
                import psutil
                running = any(pre.expected_process_name.lower() in p.name().lower() for p in psutil.process_iter(['name']))
                if not running:
                    return False, f"Expected process '{pre.expected_process_name}' is not running."
            except Exception:
                pass

        return True, None

    async def execute_step(self, dag_id: str, step_id: str) -> Dict[str, Any]:
        """Executes a single step with pre-condition check and safety engine execution."""
        dag = self.get_dag(dag_id)
        if not dag:
            raise ValueError(f"Workflow DAG '{dag_id}' not found.")
        step = dag.get_step(step_id)
        if not step:
            raise ValueError(f"Step '{step_id}' not found in DAG '{dag_id}'.")

        # 1. Pre-condition Verification
        ok, divergence_reason = self.check_precondition(step)
        if not ok:
            step.status = "diverged"
            step.divergence_reason = divergence_reason
            dag.status = "diverged"
            broadcast_workflow_event("WORKFLOW_DIVERGENCE_ALERT", {
                "dag_id": dag_id,
                "step_id": step_id,
                "reason": divergence_reason
            })
            return {"status": "diverged", "reason": divergence_reason}

        # 2. Execution via Safety Engine
        step.status = "running"
        broadcast_workflow_event("WORKFLOW_STEP_STATUS", {
            "dag_id": dag_id,
            "step_id": step_id,
            "status": "running"
        })

        try:
            result = await safety_engine.execute_tool(step.tool_name, step.args)
            step.status = "completed"
            step.output = result
            broadcast_workflow_event("WORKFLOW_STEP_STATUS", {
                "dag_id": dag_id,
                "step_id": step_id,
                "status": "completed",
                "output": str(result)[:300]
            })
            return {"status": "success", "output": result}
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            dag.status = "failed"
            broadcast_workflow_event("WORKFLOW_STEP_STATUS", {
                "dag_id": dag_id,
                "step_id": step_id,
                "status": "failed",
                "error": str(e)
            })
            return {"status": "failed", "error": str(e)}

    async def execute_all(self, dag_id: str) -> Dict[str, Any]:
        """Executes ready steps in the DAG until completion or divergence."""
        dag = self.get_dag(dag_id)
        if not dag:
            raise ValueError(f"DAG '{dag_id}' not found.")
        if dag.status not in ["approved", "executing"]:
            raise ValueError(f"DAG '{dag_id}' must be approved before execution (current status: {dag.status}).")

        dag.status = "executing"
        broadcast_workflow_event("WORKFLOW_EXECUTION_STARTED", {"dag_id": dag_id})

        while True:
            ready_steps = dag.get_executable_steps()
            if not ready_steps:
                break

            for step in ready_steps:
                res = await self.execute_step(dag_id, step.step_id)
                if res.get("status") in ["diverged", "failed"]:
                    return {"status": res["status"], "dag": dag.model_dump()}

        all_completed = all(s.status == "completed" for s in dag.steps)
        dag.status = "completed" if all_completed else "failed"
        dag.completed_at = time.time()
        broadcast_workflow_event("WORKFLOW_EXECUTION_COMPLETED", {"dag_id": dag_id, "status": dag.status})
        return {"status": dag.status, "dag": dag.model_dump()}


workflow_manager = WorkflowExecutionManager()
workflow_execution_manager = workflow_manager


# =========================================================================
# Tool Registrations
# =========================================================================

class PlanWorkflowDAGArgs(BaseModel):
    goal: str = Field(description="High-level multi-step cross-app objective")
    explicit_steps: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional explicit step definitions")

class ApproveWorkflowBatchArgs(BaseModel):
    dag_id: str = Field(description="Unique DAG identifier to approve")

class ExecuteWorkflowDAGArgs(BaseModel):
    dag_id: str = Field(description="Unique DAG identifier to execute")


@registry.register(
    name="plan_workflow_dag",
    tier=0,
    description="Decomposes a multi-application goal into an execution DAG with preconditions and risk tiers.",
    args_schema=PlanWorkflowDAGArgs,
    preview_fn=lambda a: f"Plan autonomous workflow DAG for: '{a.get('goal', '')}'"
)
async def plan_workflow_dag(goal: str, explicit_steps: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    dag = workflow_manager.create_dag(goal, explicit_steps)
    return {
        "status": "success",
        "dag_id": dag.dag_id,
        "step_count": len(dag.steps),
        "max_tier": dag.max_tier,
        "estimated_duration_s": dag.estimated_duration_s,
        "dag": dag.model_dump()
    }


@registry.register(
    name="approve_workflow_batch",
    tier=1,
    description="Upfront 1-click batch approval for a prepared autonomous workflow DAG.",
    args_schema=ApproveWorkflowBatchArgs,
    preview_fn=lambda a: f"Approve entire workflow DAG '{a.get('dag_id', '')}' for batch execution"
)
async def approve_workflow_batch(dag_id: str) -> Dict[str, Any]:
    dag = workflow_manager.approve_batch(dag_id)
    return {
        "status": "success",
        "dag_id": dag.dag_id,
        "dag_status": dag.status,
        "message": f"Workflow DAG '{dag_id}' approved for execution."
    }


@registry.register(
    name="execute_workflow_dag",
    tier=1,
    description="Executes an approved workflow DAG with divergence detection and automated pausing.",
    args_schema=ExecuteWorkflowDAGArgs,
    preview_fn=lambda a: f"Execute autonomous workflow DAG '{a.get('dag_id', '')}'"
)
async def execute_workflow_dag(dag_id: str) -> Dict[str, Any]:
    return await workflow_manager.execute_all(dag_id)
