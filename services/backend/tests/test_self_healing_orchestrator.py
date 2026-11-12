"""Unit & Safety Tests for Self-Healing Dynamic Workflow Orchestrator & Error Interceptor (Milestone 28 Phase 3)."""

import pytest
import time
from services.backend.planning.goal_decomposition_engine import (
    GoalDecompositionEngine,
    Rule8ViolationError,
)
from services.backend.planning.plan_tree import PlanNodeStatus
from services.backend.planning.error_interceptor import (
    ErrorInterceptor,
    ErrorTaxonomy,
)
from services.backend.planning.self_healing_orchestrator import (
    SelfHealingOrchestrator,
    HealingJournalRecord,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.self_healing_tools  # Ensure registered


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_error_interceptor_taxonomy_classification():
    interceptor = ErrorInterceptor()

    d1 = interceptor.diagnose_error("Permission denied: EACCES restricted", "tree_1", "node_1")
    assert d1.taxonomy == ErrorTaxonomy.PERMISSION_DENIED
    assert "SANDBOX" in d1.recommended_strategy

    d2 = interceptor.diagnose_error("FileNotFoundError: [Errno 2] No such file or directory: 'cache.db'", "tree_1", "node_2")
    assert d2.taxonomy == ErrorTaxonomy.RESOURCE_NOT_FOUND
    assert "RECONSTRUCT" in d2.recommended_strategy

    d3 = interceptor.diagnose_error("Operation timed out: SLA deadline exceeded 25ms", "tree_1", "node_3")
    assert d3.taxonomy == ErrorTaxonomy.TIMEOUT_INTERRUPT
    assert "CHUNKED_RETRY" in d3.recommended_strategy

    d4 = interceptor.diagnose_error("JSONDecodeError: Unexpected token '<<' in schema", "tree_1", "node_4")
    assert d4.taxonomy == ErrorTaxonomy.MALFORMED_OUTPUT
    assert "SCHEMA_REPAIR" in d4.recommended_strategy

    d5 = interceptor.diagnose_error("RuntimeError: Out of memory; device busy", "tree_1", "node_5")
    assert d5.taxonomy == ErrorTaxonomy.ENVIRONMENT_FAULT
    assert "FLUSH" in d5.recommended_strategy


def test_heal_failure_grafts_compensatory_subplan():
    engine = GoalDecompositionEngine()
    tree = engine.decompose_goal("Autonomous In-Flight Healing Verification", max_depth=4)
    orchestrator = SelfHealingOrchestrator(decomposition_engine=engine)

    # Pick a leaf node to simulate failure
    leaf_nodes = [n for n in tree.nodes.values() if n.depth == 2]
    assert len(leaf_nodes) > 0
    failing_node = leaf_nodes[0]
    initial_total_nodes = len(tree.nodes)

    result = orchestrator.heal_failure(
        target_tree_id=tree.tree_id,
        failing_node_id=failing_node.node_id,
        raw_error="ETIMEDOUT: network socket deadline exceeded",
    )

    assert result["diagnosed_taxonomy"] == ErrorTaxonomy.TIMEOUT_INTERRUPT.value
    assert result["grafted_nodes_count"] == 2
    assert result["tree_total_nodes"] == initial_total_nodes + 2

    # Verify failing node marked BLOCKED
    assert failing_node.status == PlanNodeStatus.BLOCKED
    assert len(failing_node.children_ids) == 2

    # Verify grafted node prerequisites
    grafted_nodes = [tree.get_node(gid) for gid in result["grafted_node_ids"]]
    assert all(gn is not None for gn in grafted_nodes)
    assert grafted_nodes[1].prerequisites == [grafted_nodes[0].node_id]


def test_heal_failure_permission_denied_sandbox_graft():
    engine = GoalDecompositionEngine()
    tree = engine.decompose_goal("Sandbox Isolation Healing Test", max_depth=4)
    orchestrator = SelfHealingOrchestrator(decomposition_engine=engine)

    subtask_nodes = [n for n in tree.nodes.values() if n.depth == 1]
    failing_node = subtask_nodes[0]

    result = orchestrator.heal_failure(
        target_tree_id=tree.tree_id,
        failing_node_id=failing_node.node_id,
        raw_error="PermissionDenied: Process lacks write access to /etc/phenom",
    )

    assert result["diagnosed_taxonomy"] == ErrorTaxonomy.PERMISSION_DENIED.value
    assert "SANDBOX" in result["compensation_strategy"]

    graft_1 = tree.get_node(result["grafted_node_ids"][0])
    assert "Sandbox" in graft_1.title
    assert graft_1.action_type == "VERIFY_SANDBOX"


def test_heal_failure_resource_not_found_reconstruction():
    engine = GoalDecompositionEngine()
    tree = engine.decompose_goal("Dependency Reconstruction Test", max_depth=4)
    orchestrator = SelfHealingOrchestrator(decomposition_engine=engine)

    leaf_node = [n for n in tree.nodes.values() if n.depth == 2][0]

    result = orchestrator.heal_failure(
        target_tree_id=tree.tree_id,
        failing_node_id=leaf_node.node_id,
        raw_error="ModuleNotFoundError: No module named 'phenom_core_wasm'",
    )

    assert result["diagnosed_taxonomy"] == ErrorTaxonomy.RESOURCE_NOT_FOUND.value
    assert "RECONSTRUCT" in result["compensation_strategy"]

    graft_1 = tree.get_node(result["grafted_node_ids"][0])
    assert graft_1.action_type == "RECONSTRUCT_RESOURCE"


def test_healing_journal_persistence():
    engine = GoalDecompositionEngine()
    tree = engine.decompose_goal("Journal Persistence Goal", max_depth=4)
    orchestrator = SelfHealingOrchestrator(decomposition_engine=engine)

    leaf = [n for n in tree.nodes.values() if n.depth == 2][0]
    orchestrator.heal_failure(tree.tree_id, leaf.node_id, "SyntaxError: Unexpected token")

    journal = orchestrator.get_journal()
    assert len(journal) >= 2
    latest = journal[-1]
    assert latest["target_tree_id"] == tree.tree_id
    assert latest["failing_node_id"] == leaf.node_id
    assert latest["outcome_status"] == "GRAFTED_AND_RETRYING"


def test_rule_8_anti_checkout_self_healing():
    interceptor = ErrorInterceptor()
    orchestrator = SelfHealingOrchestrator()

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        interceptor.diagnose_error("Payment failed at checkout gateway", "tree_1", "node_1")

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        orchestrator.heal_failure("tree_1", "node_1", "Stripe credit card charge failure")


def test_guardian_kill_switch_sla_self_healing():
    orchestrator = SelfHealingOrchestrator()

    guardian.trigger(reason="Test Kill Switch Halt")
    t0 = time.perf_counter()

    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        orchestrator.heal_failure("tree_1", "node_1", "Permission denied")

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 25.0, f"Guardian SLA exceeded: {elapsed_ms:.4f}ms"

    guardian.resume()
    journal = orchestrator.get_journal()
    assert len(journal) >= 1


def test_tool_registry_self_healing_tools():
    phase3_tools = [
        ("intercept_and_heal_failure", 1),
        ("diagnose_execution_error", 0),
        ("get_active_healing_journal", 0),
    ]

    for tool_name, expected_tier in phase3_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch"
        assert tool_def.preview_fn is not None
        assert tool_def.args_schema is not None
        assert tool_def.handler_fn is not None
