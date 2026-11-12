"""Unit & Safety Tests for Autonomous Goal Decomposition Tree Engine (Milestone 28 Phase 1)."""

import pytest
import time
from services.backend.planning.goal_decomposition_engine import (
    GoalDecompositionEngine,
    Rule8ViolationError,
)
from services.backend.planning.plan_tree import (
    PlanNode,
    PlanNodeStatus,
    PlanNodeType,
    PlanTree,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.goal_planning_tools  # Ensure registered


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_default_plan_tree_initialization():
    engine = GoalDecompositionEngine()
    tree = engine.get_tree()
    assert tree is not None
    assert "System Health" in tree.root_goal
    assert len(tree.nodes) >= 6

    root_nodes = [n for n in tree.nodes.values() if n.node_type == PlanNodeType.ROOT_GOAL]
    assert len(root_nodes) == 1
    root = root_nodes[0]
    assert root.depth == 0

    subtasks = [n for n in tree.nodes.values() if n.node_type == PlanNodeType.SUBTASK]
    assert len(subtasks) == 3
    assert all(st.depth == 1 for st in subtasks)


def test_decompose_custom_goal():
    engine = GoalDecompositionEngine()
    tree = engine.decompose_goal("Refactor Memory Storage & Verify Encryption", max_depth=4)
    assert tree is not None
    assert tree.root_goal == "Refactor Memory Storage & Verify Encryption"
    assert len(tree.nodes) == 7

    # Validate parent-child linkage
    root_node = next(n for n in tree.nodes.values() if n.node_type == PlanNodeType.ROOT_GOAL)
    assert len(root_node.children_ids) == 3

    # Validate DAG prerequisites
    subtasks = [n for n in tree.nodes.values() if n.node_type == PlanNodeType.SUBTASK]
    sub1 = next(st for st in subtasks if "Analyze Prerequisites" in st.title)
    sub2 = next(st for st in subtasks if "Execute Core Workflow" in st.title)
    sub3 = next(st for st in subtasks if "Verify Safety Invariants" in st.title)

    assert sub1.node_id in sub2.prerequisites
    assert sub2.node_id in sub3.prerequisites


def test_expand_node_with_child_actions():
    engine = GoalDecompositionEngine()
    tree = engine.decompose_goal("Optimize Network Cache Latency", max_depth=4)
    subtasks = [n for n in tree.nodes.values() if n.node_type == PlanNodeType.SUBTASK]
    target_subtask = subtasks[0]

    expanded = engine.expand_node(
        tree_id=tree.tree_id,
        parent_node_id=target_subtask.node_id,
        new_children=[
            {"title": "Profile socket buffer latency", "action_type": "BENCHMARK", "estimated_duration_ms": 25.0},
            {"title": "Flush stale socket connections", "action_type": "FLUSH", "estimated_duration_ms": 15.0},
        ],
    )

    assert len(expanded) == 2
    assert all(child.depth == target_subtask.depth + 1 for child in expanded)
    assert all(child.parent_id == target_subtask.node_id for child in expanded)
    assert expanded[0].node_id in target_subtask.children_ids
    assert expanded[1].node_id in target_subtask.children_ids


def test_max_depth_enforcement():
    engine = GoalDecompositionEngine()
    tree = engine.decompose_goal("Test Deep Nesting", max_depth=2)
    # Root is depth 0, subtasks depth 1, leaves depth 2
    leaves = [n for n in tree.nodes.values() if n.depth == 2]
    assert len(leaves) > 0

    # Attempting to expand a node at depth 2 in a tree with max_depth 2 must raise ValueError
    with pytest.raises(ValueError, match="max depth"):
        engine.expand_node(
            tree_id=tree.tree_id,
            parent_node_id=leaves[0].node_id,
            new_children=[{"title": "Exceeding Leaf Action"}],
        )


def test_node_status_progression_and_runnable_prerequisites():
    engine = GoalDecompositionEngine()
    tree = engine.decompose_goal("Autonomous Migration Test", max_depth=4)

    subtasks = [n for n in tree.nodes.values() if n.node_type == PlanNodeType.SUBTASK]
    sub1 = next(st for st in subtasks if "Analyze Prerequisites" in st.title)
    sub2 = next(st for st in subtasks if "Execute Core Workflow" in st.title)

    # Initially sub1 has no prerequisites so it should be runnable
    assert tree.is_runnable(sub1.node_id) is True
    # sub2 depends on sub1, which is PENDING, so sub2 is not runnable
    assert tree.is_runnable(sub2.node_id) is False

    # Mark sub1 completed
    node1 = engine.mark_node_status(tree.tree_id, sub1.node_id, PlanNodeStatus.COMPLETED)
    assert node1.status == PlanNodeStatus.COMPLETED
    assert node1.completed_at is not None

    # Now sub2 has all prerequisites satisfied, should be runnable
    assert tree.is_runnable(sub2.node_id) is True


def test_rule_8_anti_checkout_planning():
    engine = GoalDecompositionEngine()

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        engine.decompose_goal("Proceed to checkout and enter credit card billing details")

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        tree = engine.decompose_goal("Legitimate Architecture Goal")
        root_node = next(n for n in tree.nodes.values() if n.node_type == PlanNodeType.ROOT_GOAL)
        engine.expand_node(
            tree.tree_id,
            root_node.node_id,
            [{"title": "Pay invoice with stripe checkout"}],
        )


def test_guardian_kill_switch_sla_planning():
    engine = GoalDecompositionEngine()

    guardian.trigger(reason="Test Kill Switch Halt")
    t0 = time.perf_counter()

    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        engine.decompose_goal("Should be halted immediately")

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 25.0, f"Guardian SLA exceeded: {elapsed_ms:.4f}ms"

    guardian.resume()
    # Now operations resume cleanly
    tree = engine.decompose_goal("Post-trip resumption")
    assert tree is not None


def test_tool_registry_goal_planning_tools():
    phase1_tools = [
        ("decompose_hierarchical_goal", 0),
        ("expand_plan_tree_node", 1),
        ("get_active_goal_tree", 0),
    ]

    for tool_name, expected_tier in phase1_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch"
        assert tool_def.preview_fn is not None
        assert tool_def.args_schema is not None
        assert tool_def.handler_fn is not None
