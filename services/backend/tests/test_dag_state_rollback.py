"""
Unit Tests for Self-Healing DAG State Rollback Engine (PLN-01, SAF-01, SAF-02).
Tests deep-copy checkpoint immutability, context rollback, status restoration,
retry budgets, automatic contingency handoff, and Guardian halt enforcement.
"""

import pytest
from services.backend.schemas.tot import (
    BranchType,
    DAGBranch,
    DAGNode,
    GoalDAG,
    NodeStatus,
)
from services.backend.orchestrator.dag_state import DAGStateManager
from services.backend.orchestrator.metacognition import metacognitive_reflector


@pytest.fixture
def state_mgr():
    mgr = DAGStateManager()
    mgr.reset()
    metacognitive_reflector.reset()
    return mgr


@pytest.fixture
def mock_dag():
    n1 = DAGNode(
        node_id="step_1",
        title="Setup step",
        description="Initialize context",
        action_type="setup",
        branch_id="b_primary",
        is_checkpoint=True,
        status=NodeStatus.PENDING,
    )
    n2 = DAGNode(
        node_id="step_2",
        title="Action step",
        description="Perform speculative work",
        action_type="speculative",
        branch_id="b_primary",
        depends_on=["step_1"],
        max_retries=2,
        status=NodeStatus.PENDING,
    )
    c1 = DAGNode(
        node_id="c_step_1",
        title="Contingency step",
        description="Fallback work",
        action_type="fallback",
        branch_id="b_contingency",
        status=NodeStatus.PENDING,
    )

    b_primary = DAGBranch(
        branch_id="b_primary",
        name="Primary Branch",
        branch_type=BranchType.PRIMARY,
        node_ids=["step_1", "step_2"],
        is_active=True,
    )
    b_contingency = DAGBranch(
        branch_id="b_contingency",
        name="Contingency Branch",
        branch_type=BranchType.CONTINGENCY,
        node_ids=["c_step_1"],
        is_active=False,
    )

    return GoalDAG(
        dag_id="dag_test_state",
        goal_description="Test state rollback and self-healing",
        nodes={"step_1": n1, "step_2": n2, "c_step_1": c1},
        branches={"b_primary": b_primary, "b_contingency": b_contingency},
        active_branch_id="b_primary",
        context_data={"staged_files": ["init.txt"], "balance": 100},
    )


def test_checkpoint_deep_copy_immutability(state_mgr, mock_dag):
    # Enforce Plan Checker Recommendation #1: deep-copy checkpoint immutability
    ckpt = state_mgr.create_checkpoint(mock_dag, step_index=1)
    assert ckpt.context_snapshot["staged_files"] == ["init.txt"]

    # In-place modification to dag.context_data
    mock_dag.context_data["staged_files"].append("mutated.txt")
    mock_dag.context_data["balance"] = 999

    # The checkpoint snapshot MUST remain unmodified
    assert ckpt.context_snapshot["staged_files"] == ["init.txt"]
    assert ckpt.context_snapshot["balance"] == 100


def test_rollback_to_checkpoint(state_mgr, mock_dag):
    # Create baseline checkpoint
    state_mgr.create_checkpoint(mock_dag, step_index=1)

    # Simulate node execution failure & context mutation
    mock_dag.nodes["step_1"].status = NodeStatus.COMPLETED
    mock_dag.nodes["step_2"].status = NodeStatus.FAILED
    mock_dag.context_data["corrupted_key"] = "bad_value"

    # Execute rollback
    res = state_mgr.rollback_to_checkpoint(mock_dag)
    assert res is True

    # Corrupted key must be reverted
    assert "corrupted_key" not in mock_dag.context_data
    assert mock_dag.context_data["staged_files"] == ["init.txt"]

    # Failed node must be marked ROLLED_BACK
    assert mock_dag.nodes["step_2"].status == NodeStatus.ROLLED_BACK


def test_execute_node_success_and_progress(state_mgr, mock_dag):
    def dummy_success(node, context):
        return {"written": 42}

    step_1 = mock_dag.nodes["step_1"]
    res = state_mgr.execute_node_with_retry(mock_dag, step_1, dummy_success)

    assert res["success"] is True
    assert step_1.status == NodeStatus.COMPLETED
    assert step_1.result_data == {"written": 42}
    # Checkpoint should have been created because step_1.is_checkpoint is True
    assert len(mock_dag.checkpoints) >= 1
    # Active branch has 2 nodes, 1 completed -> 50%
    assert mock_dag.overall_progress_pct == 50.0


def test_automatic_rollback_on_retries_exhausted(state_mgr, mock_dag):
    # Complete step 1
    mock_dag.nodes["step_1"].status = NodeStatus.COMPLETED
    state_mgr.create_checkpoint(mock_dag, step_index=1)

    def dummy_failure(node, context):
        context["scratch"] = "tainted"
        raise RuntimeError("Transient network failure")

    step_2 = mock_dag.nodes["step_2"]
    step_2.max_retries = 2

    # Attempt 1: failure -> retry budget remaining
    res1 = state_mgr.execute_node_with_retry(mock_dag, step_2, dummy_failure)
    assert res1["success"] is False
    assert step_2.retry_count == 1
    assert mock_dag.branches["b_primary"].pruned is False

    # Attempt 2: failure -> retries exhausted -> auto rollback and switch to contingency
    res2 = state_mgr.execute_node_with_retry(mock_dag, step_2, dummy_failure)
    assert res2["success"] is False
    assert step_2.retry_count == 2
    assert mock_dag.branches["b_primary"].pruned is True
    assert mock_dag.active_branch_id == "b_contingency"
    assert "scratch" not in mock_dag.context_data  # rolled back!


def test_guardian_halt(state_mgr, mock_dag):
    state_mgr.halt()
    assert state_mgr.is_halted is True

    with pytest.raises(PermissionError, match="DAGStateManager is halted"):
        state_mgr.create_checkpoint(mock_dag, 1)

    with pytest.raises(PermissionError, match="DAGStateManager is halted"):
        state_mgr.execute_node_with_retry(mock_dag, mock_dag.nodes["step_1"], lambda n, c: None)

    state_mgr.reset()
    assert state_mgr.is_halted is False
