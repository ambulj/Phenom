"""
Unit tests for Autonomous Workflow DAG Planner & Batch Approval Engine (Phase 50-01)
Tests:
1. Natural language decomposition into topologically ordered DAG
2. Explicit step DAG compilation and risk tier derivation
3. Dependency-aware execution readiness (get_executable_steps)
4. Upfront batch approval state transitions & enforcement (cannot run unapproved)
5. Pre-condition divergence detection (missing file triggers pause with diverged status)
6. Pre-condition success and end-to-end multi-step DAG execution
7. Tool registry verification (tiers, schemas, previews)
"""

import pytest
import os
import asyncio
import services.backend.tools.file_tools
from services.backend.workflows.dag_planner import (
    WorkflowDAGPlanner,
    WorkflowDAG,
    WorkflowStep,
    StepPrecondition,
    dag_planner,
)
from services.backend.workflows.batch_approval import (
    WorkflowExecutionManager,
    workflow_manager,
    plan_workflow_dag,
    approve_workflow_batch,
    execute_workflow_dag,
)
from services.backend.safety.registry import registry


def test_dag_planner_decomposition():
    """Verify natural language decomposition generates structured DAG with dependencies."""
    planner = WorkflowDAGPlanner()
    dag = planner.plan("Write python code and verify with tests")

    assert dag.dag_id.startswith("dag_")
    assert len(dag.steps) >= 3
    assert dag.status == "created"
    assert dag.max_tier >= 1

    # Check dependency ordering
    step1 = dag.steps[0]
    step2 = dag.steps[1]
    step3 = dag.steps[2]

    assert step1.step_id == "step_1"
    assert step1.depends_on == []
    assert "step_1" in step2.depends_on
    assert "step_2" in step3.depends_on

    # Initially only step_1 is ready
    executable = dag.get_executable_steps()
    assert len(executable) == 1
    assert executable[0].step_id == "step_1"


def test_explicit_steps_planning():
    """Verify custom explicit steps with preconditions and tiers compile accurately."""
    planner = WorkflowDAGPlanner()
    explicit = [
        {
            "step_id": "init_env",
            "title": "Check Environment",
            "tool_name": "list_files",
            "args": {"directory": "."},
            "tier": 0,
            "depends_on": [],
            "precondition": {"file_must_exist": "."}
        },
        {
            "step_id": "run_audit",
            "title": "Audit Logs",
            "tool_name": "read_file",
            "args": {"path": "AGENTS.md"},
            "tier": 0,
            "depends_on": ["init_env"]
        }
    ]

    dag = planner.plan("Custom workflow", explicit_steps=explicit)
    assert len(dag.steps) == 2
    assert dag.steps[0].step_id == "init_env"
    assert dag.steps[0].precondition is not None
    assert dag.steps[0].precondition.file_must_exist == "."
    assert dag.steps[1].depends_on == ["init_env"]
    assert dag.max_tier == 0


def test_batch_approval_state_lifecycle():
    """Verify approval is mandatory before execution and transitions states correctly."""
    mgr = WorkflowExecutionManager()
    dag = mgr.create_dag("Search web and synthesize notes")

    assert dag.status == "created"
    assert dag.approved_at is None

    # Cannot execute unapproved DAG
    with pytest.raises(ValueError, match="must be approved before execution"):
        asyncio.run(mgr.execute_all(dag.dag_id))

    # Approve batch
    approved = mgr.approve_batch(dag.dag_id)
    assert approved.status == "approved"
    assert approved.approved_at is not None
    assert approved.approved_at > 0


def test_precondition_divergence_detection():
    """Verify failing precondition halts execution and flags divergence."""
    mgr = WorkflowExecutionManager()
    
    # Step requiring a non-existent file
    bogus_path = os.path.join(os.getcwd(), "non_existent_file_99999.xyz")
    explicit = [
        {
            "step_id": "step_fail_precondition",
            "title": "Access Missing File",
            "tool_name": "list_files",
            "args": {"path": "."},
            "tier": 0,
            "depends_on": [],
            "precondition": {"file_must_exist": bogus_path}
        }
    ]

    dag = mgr.create_dag("Divergence Test DAG", explicit_steps=explicit)
    mgr.approve_batch(dag.dag_id)

    # Precondition check directly
    step = dag.steps[0]
    ok, reason = mgr.check_precondition(step)
    assert ok is False
    assert "does not exist on disk" in reason

    # Execution halts on divergence
    result = asyncio.run(mgr.execute_all(dag.dag_id))
    assert result["status"] == "diverged"
    assert dag.status == "diverged"
    assert step.status == "diverged"
    assert step.divergence_reason is not None


@pytest.mark.asyncio
async def test_end_to_end_dag_execution():
    """Verify full DAG execution with passing preconditions and tier 0 tools."""
    mgr = WorkflowExecutionManager()
    explicit = [
        {
            "step_id": "step_1",
            "title": "Check current directory exists",
            "tool_name": "list_files",
            "args": {"path": "."},
            "tier": 0,
            "depends_on": [],
            "precondition": {"file_must_exist": "."}
        },
        {
            "step_id": "step_2",
            "title": "Read project agents file",
            "tool_name": "read_file",
            "args": {"path": "AGENTS.md"},
            "tier": 0,
            "depends_on": ["step_1"]
        }
    ]

    dag = mgr.create_dag("End to end test", explicit_steps=explicit)
    mgr.approve_batch(dag.dag_id)

    result = await mgr.execute_all(dag.dag_id)
    assert result["status"] == "completed"
    assert dag.status == "completed"
    assert all(s.status == "completed" for s in dag.steps)
    assert dag.completed_at is not None


def test_tool_registrations_and_safety_tiers():
    """Verify all workflow tools are registered in safety registry with required metadata."""
    t_plan = registry.get("plan_workflow_dag")
    assert t_plan is not None
    assert t_plan.tier == 0
    assert callable(t_plan.preview_fn)
    preview = t_plan.preview_fn({"goal": "Process data"})
    assert "Process data" in preview

    t_approve = registry.get("approve_workflow_batch")
    assert t_approve is not None
    assert t_approve.tier == 1
    assert callable(t_approve.preview_fn)
    preview = t_approve.preview_fn({"dag_id": "dag_123"})
    assert "dag_123" in preview

    t_execute = registry.get("execute_workflow_dag")
    assert t_execute is not None
    assert t_execute.tier == 1
    assert callable(t_execute.preview_fn)
    preview = t_execute.preview_fn({"dag_id": "dag_456"})
    assert "dag_456" in preview
