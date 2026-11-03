"""
Unit Tests for Metacognitive Reflector (PLN-01, SAF-01, SAF-02).
Tests outcome signature hashing, stagnation detection (>= 3 identical failures),
oscillation detection (2-cycle and 3-cycle ping-pong), and dynamic branch pruning.
"""

import pytest
from services.backend.schemas.tot import (
    BranchType,
    DAGBranch,
    DAGNode,
    GoalDAG,
    NodeStatus,
)
from services.backend.orchestrator.metacognition import MetacognitiveReflector


@pytest.fixture
def reflector():
    r = MetacognitiveReflector(history_window_size=10)
    r.reset()
    return r


@pytest.fixture
def sample_dag():
    n1 = DAGNode(
        node_id="node_a",
        title="Node A",
        description="First node",
        action_type="fetch",
        branch_id="b_primary",
        status=NodeStatus.PENDING,
    )
    n2 = DAGNode(
        node_id="node_b",
        title="Node B",
        description="Second node",
        action_type="transform",
        branch_id="b_primary",
        depends_on=["node_a"],
        status=NodeStatus.PENDING,
    )
    c1 = DAGNode(
        node_id="node_c_contingency",
        title="Contingency Node",
        description="Fallback node",
        action_type="fallback",
        branch_id="b_contingency",
        status=NodeStatus.PENDING,
    )

    primary_b = DAGBranch(
        branch_id="b_primary",
        name="Primary Branch",
        branch_type=BranchType.PRIMARY,
        node_ids=["node_a", "node_b"],
        is_active=True,
    )
    contingency_b = DAGBranch(
        branch_id="b_contingency",
        name="Contingency Branch",
        branch_type=BranchType.CONTINGENCY,
        node_ids=["node_c_contingency"],
        is_active=False,
    )

    return GoalDAG(
        dag_id="dag_meta_test",
        goal_description="Test metacognitive loop detection",
        nodes={"node_a": n1, "node_b": n2, "node_c_contingency": c1},
        branches={"b_primary": primary_b, "b_contingency": contingency_b},
        active_branch_id="b_primary",
    )


def test_signature_computation(reflector):
    node = DAGNode(
        node_id="test_node_1",
        title="Test",
        description="Desc",
        action_type="test_action",
        branch_id="b1",
    )
    sig1 = reflector.compute_signature(node, "COMPLETED", None)
    sig2 = reflector.compute_signature(node, "COMPLETED", None)
    sig_fail = reflector.compute_signature(node, "FAILED", "Connection timeout")

    assert sig1 == sig2
    assert sig1 != sig_fail
    assert len(sig1) == 16


def test_stagnation_detection(reflector, sample_dag):
    node_a = sample_dag.nodes["node_a"]

    # First failure -> retry recommended
    node_a.retry_count = 0
    node_a.max_retries = 3
    r1 = reflector.reflect_on_step(sample_dag, node_a, status=NodeStatus.FAILED, error="File missing")
    assert r1.detected_loop is False
    assert r1.recommended_action == "RETRY_STEP"

    # Second failure
    r2 = reflector.reflect_on_step(sample_dag, node_a, status=NodeStatus.FAILED, error="File missing")
    assert r2.detected_loop is False

    # Third identical failure -> stagnation detected!
    r3 = reflector.reflect_on_step(sample_dag, node_a, status=NodeStatus.FAILED, error="File missing")
    assert r3.detected_loop is True
    assert r3.stagnation_detected is True
    assert r3.loop_type == "stagnation"
    assert r3.recommended_action == "PRUNE_BRANCH"

    # Verify branch was pruned and contingency branch activated
    assert sample_dag.branches["b_primary"].pruned is True
    assert sample_dag.nodes["node_b"].status == NodeStatus.PRUNED
    assert sample_dag.active_branch_id == "b_contingency"


def test_oscillation_2cycle_detection(reflector, sample_dag):
    node_a = sample_dag.nodes["node_a"]
    node_b = sample_dag.nodes["node_b"]

    # Sequence: A fail, B fail, A fail, B fail (2-cycle [X, Y, X, Y])
    reflector.reflect_on_step(sample_dag, node_a, status=NodeStatus.FAILED, error="Oscillating err 1")
    reflector.reflect_on_step(sample_dag, node_b, status=NodeStatus.FAILED, error="Oscillating err 2")
    reflector.reflect_on_step(sample_dag, node_a, status=NodeStatus.FAILED, error="Oscillating err 1")
    r4 = reflector.reflect_on_step(sample_dag, node_b, status=NodeStatus.FAILED, error="Oscillating err 2")

    assert r4.detected_loop is True
    assert r4.loop_type == "oscillation_2cycle"
    assert r4.recommended_action == "PRUNE_BRANCH"
    assert sample_dag.branches["b_primary"].pruned is True


def test_guardian_halt(reflector, sample_dag):
    reflector.halt()
    assert reflector.is_halted is True

    node_a = sample_dag.nodes["node_a"]
    with pytest.raises(PermissionError, match="MetacognitiveReflector is halted"):
        reflector.reflect_on_step(sample_dag, node_a, status=NodeStatus.COMPLETED)

    reflector.reset()
    assert reflector.is_halted is False
    res = reflector.reflect_on_step(sample_dag, node_a, status=NodeStatus.COMPLETED)
    assert res.recommended_action == "CONTINUE"
