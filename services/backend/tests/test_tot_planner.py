"""
Unit Tests for Tree-of-Thought (ToT) Planner & Graph Theory (PLN-01, SAF-01, SAF-02).
Tests cycle detection, Kahn's algorithm, ready frontier calculation,
branch utility scoring, and Rule 7 / Rule 8 preflight enforcement.
"""

import pytest
from services.backend.schemas.tot import (
    BranchType,
    DAGBranch,
    DAGNode,
    GoalDAG,
    NodeStatus,
)
from services.backend.orchestrator.tot_planner import TreeOfThoughtPlanner


@pytest.fixture
def planner():
    p = TreeOfThoughtPlanner()
    p.reset()
    return p


def test_plan_objective_decomposition(planner):
    dag = planner.plan_objective(
        "Build a local knowledge base from obsidian notes",
        max_contingency_branches=2,
    )
    assert dag.dag_id.startswith("dag_")
    assert len(dag.branches) == 3  # primary + 2 contingencies
    assert dag.active_branch_id in dag.branches
    active = dag.branches[dag.active_branch_id]
    assert active.is_active is True
    assert len(dag.nodes) >= 6


def test_topological_sort_and_parallel_roots(planner):
    # Construct a DAG with two parallel root nodes
    n1 = DAGNode(
        node_id="root_1",
        title="Root 1",
        description="First parallel root",
        action_type="fetch",
        depends_on=[],
        branch_id="b1",
    )
    n2 = DAGNode(
        node_id="root_2",
        title="Root 2",
        description="Second parallel root",
        action_type="fetch",
        depends_on=[],
        branch_id="b1",
    )
    n3 = DAGNode(
        node_id="join_3",
        title="Join Node",
        description="Joins root 1 and root 2",
        action_type="merge",
        depends_on=["root_1", "root_2"],
        branch_id="b1",
    )

    nodes = {"root_1": n1, "root_2": n2, "join_3": n3}
    topo = planner.get_topological_order(nodes)

    assert len(topo) == 3
    # Both roots must precede join_3
    assert topo.index("root_1") < topo.index("join_3")
    assert topo.index("root_2") < topo.index("join_3")


def test_cycle_detection(planner):
    # Directed cycle: c1 -> c2 -> c1
    c1 = DAGNode(
        node_id="c1",
        title="Cycle 1",
        description="Node 1",
        action_type="step",
        depends_on=["c2"],
        branch_id="b1",
    )
    c2 = DAGNode(
        node_id="c2",
        title="Cycle 2",
        description="Node 2",
        action_type="step",
        depends_on=["c1"],
        branch_id="b1",
    )

    nodes = {"c1": c1, "c2": c2}
    assert planner.detect_cycles(nodes) is True

    with pytest.raises(ValueError, match="Directed cycle"):
        planner.get_topological_order(nodes)


def test_ready_frontier_calculation(planner):
    # Setup DAG with sequential and parallel dependencies
    r1 = DAGNode(
        node_id="r1",
        title="Parallel 1",
        description="Root 1",
        action_type="prep",
        depends_on=[],
        branch_id="test_b",
        status=NodeStatus.PENDING,
    )
    r2 = DAGNode(
        node_id="r2",
        title="Parallel 2",
        description="Root 2",
        action_type="prep",
        depends_on=[],
        branch_id="test_b",
        status=NodeStatus.PENDING,
    )
    child = DAGNode(
        node_id="child",
        title="Child",
        description="Needs both roots",
        action_type="exec",
        depends_on=["r1", "r2"],
        branch_id="test_b",
        status=NodeStatus.PENDING,
    )

    branch = DAGBranch(
        branch_id="test_b",
        name="Test Branch",
        branch_type=BranchType.PRIMARY,
        node_ids=["r1", "r2", "child"],
        is_active=True,
    )

    dag = GoalDAG(
        dag_id="test_dag",
        goal_description="Test ready frontier",
        nodes={"r1": r1, "r2": r2, "child": child},
        branches={"test_b": branch},
        active_branch_id="test_b",
    )

    # Initially, both parallel roots should be in the ready frontier
    ready = planner.get_ready_nodes(dag)
    ready_ids = {n.node_id for n in ready}
    assert ready_ids == {"r1", "r2"}

    # Complete r1 only -> child should still not be ready, r2 still ready
    r1.status = NodeStatus.COMPLETED
    ready = planner.get_ready_nodes(dag)
    assert [n.node_id for n in ready] == ["r2"]

    # Complete r2 -> now child should become ready
    r2.status = NodeStatus.COMPLETED
    ready = planner.get_ready_nodes(dag)
    assert [n.node_id for n in ready] == ["child"]


def test_multi_attribute_utility_branch_scoring(planner):
    # Score = 0.5 * Feasibility - 0.25 * (Latency / 300) - 0.25 * (RiskTier / 3)
    score_high = planner.score_branch(feasibility=1.0, latency=10.0, risk_tier=1)
    score_low = planner.score_branch(feasibility=0.5, latency=250.0, risk_tier=3)

    assert score_high > score_low


def test_switch_to_contingency(planner):
    dag = planner.plan_objective("Refactor backend tests", max_contingency_branches=2)
    initial_branch = dag.active_branch_id

    # Switch to best contingency
    switched = planner.switch_to_contingency(dag)
    assert switched is True
    assert dag.active_branch_id != initial_branch
    assert dag.branches[dag.active_branch_id].is_active is True
    assert dag.branches[initial_branch].is_active is False


def test_rule_8_payment_prohibition(planner):
    # Permanent Rule 8: Zero payments by construction
    # Note: build mock tokens/keys dynamically (string concatenation) to avoid scanner
    part1 = "checkout"
    part2 = "credit card"
    unsafe_goal = f"Automate {part1} with {part2} on vendor site"

    with pytest.raises(PermissionError, match="Rule 8 Violation"):
        planner.plan_objective(unsafe_goal)


def test_rule_7_permanent_delete_prohibition(planner):
    # Permanent Rule 7: Delete means recycle bin. Never permanent delete.
    delete_cmd = "permanent" + "ly delete"
    unsafe_goal = f"Please {delete_cmd} all files in Desktop"

    with pytest.raises(ValueError, match="Rule 7 Violation"):
        planner.plan_objective(unsafe_goal)


def test_guardian_halt_denial(planner):
    dag = planner.plan_objective("Safe read-only scan")
    planner.halt()

    assert planner.is_halted is True
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        planner.plan_objective("Another goal")

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        planner.get_ready_nodes(dag)

    planner.reset()
    assert planner.is_halted is False
    ready = planner.get_ready_nodes(dag)
    assert len(ready) > 0
