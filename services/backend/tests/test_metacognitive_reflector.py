"""Unit & Safety Tests for Metacognitive Introspection & Autonomous Strategy Reflector (Milestone 28 Phase 4)."""

import pytest
import time
from services.backend.planning.goal_decomposition_engine import (
    GoalDecompositionEngine,
    Rule8ViolationError,
)
from services.backend.planning.plan_tree import PlanNodeStatus
from services.backend.planning.metacognitive_evaluator import (
    MetacognitiveEvaluator,
    MetacognitiveReport,
)
from services.backend.planning.strategy_reflector import (
    StrategyReflector,
    StrategyHeuristic,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.metacognitive_tools  # Ensure registered


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_default_metacognitive_report_initialization():
    evaluator = MetacognitiveEvaluator()
    reports = evaluator.get_reports()
    assert len(reports) >= 1
    default_report = reports[0]
    assert default_report.reasoning_efficiency >= 0.90
    assert default_report.cognitive_drift_score < 0.10
    assert default_report.hallucination_risk_score < 0.05
    assert len(default_report.reflection_notes) >= 3


def test_evaluate_plan_trajectory_clean():
    engine = GoalDecompositionEngine()
    tree = engine.decompose_goal("Clean Architecture Refactor", max_depth=4)
    evaluator = MetacognitiveEvaluator(decomposition_engine=engine)

    # Mark some nodes completed
    for node in list(tree.nodes.values())[:3]:
        node.status = PlanNodeStatus.COMPLETED

    report = evaluator.evaluate_plan(tree.tree_id)
    assert report.target_id == tree.tree_id
    assert report.reasoning_efficiency >= 0.90
    assert report.cognitive_drift_score <= 0.10
    assert report.convergence_rate > 0.40


def test_evaluate_plan_trajectory_with_blocked_nodes():
    engine = GoalDecompositionEngine()
    tree = engine.decompose_goal("Failing Workflow Goal", max_depth=4)
    evaluator = MetacognitiveEvaluator(decomposition_engine=engine)

    # Inject blocked/failed nodes
    nodes = list(tree.nodes.values())
    nodes[1].status = PlanNodeStatus.FAILED
    nodes[2].status = PlanNodeStatus.BLOCKED

    report = evaluator.evaluate_plan(tree.tree_id)
    assert report.reasoning_efficiency < 0.85
    assert report.cognitive_drift_score > 0.10
    assert report.hallucination_risk_score > 0.05


def test_record_and_reinforce_heuristic():
    reflector = StrategyReflector()
    domain = "AST_MANIPULATION"
    rule = "Always validate syntax tokens before emitting AST node transformations."

    # First observation
    h1 = reflector.record_heuristic(domain, rule, initial_confidence=0.85)
    assert h1.domain == "AST_MANIPULATION"
    assert h1.confidence_weight == 0.85
    assert h1.observation_count == 1

    # Second observation: reinforces confidence and increments count
    h2 = reflector.record_heuristic(domain, rule)
    assert h2.heuristic_id == h1.heuristic_id
    assert h2.observation_count == 2
    assert h2.confidence_weight > 0.85


def test_reflect_on_plan_efficiency_synthesis():
    engine = GoalDecompositionEngine()
    tree = engine.decompose_goal("Strategic Reflection Target", max_depth=4)
    evaluator = MetacognitiveEvaluator(decomposition_engine=engine)
    reflector = StrategyReflector(evaluator=evaluator)

    result = reflector.reflect_on_plan_efficiency(tree.tree_id)
    assert result["target_id"] == tree.tree_id
    assert "reasoning_efficiency" in result
    assert "strategic_recommendations" in result
    assert len(result["strategic_recommendations"]) >= 1
    assert len(result["matched_heuristics"]) >= 1


def test_list_heuristics_domain_filtering():
    reflector = StrategyReflector()
    heuristics = reflector.list_heuristics()
    assert len(heuristics) >= 3

    dag_heuristics = reflector.list_heuristics(domain="DAG_DECOMPOSITION")
    assert len(dag_heuristics) >= 1
    assert all(h.domain == "DAG_DECOMPOSITION" for h in dag_heuristics)


def test_rule_8_anti_checkout_metacognitive():
    evaluator = MetacognitiveEvaluator()
    reflector = StrategyReflector()

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        evaluator.evaluate_plan("Checkout payment verification loop")

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        reflector.record_heuristic("BILLING", "Always charge credit card upon completion")

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        reflector.reflect_on_plan_efficiency("Stripe payment order dispatch")


def test_guardian_kill_switch_sla_metacognitive():
    evaluator = MetacognitiveEvaluator()
    reflector = StrategyReflector()

    guardian.trigger(reason="Test Kill Switch Halt")
    t0 = time.perf_counter()

    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        evaluator.evaluate_plan("Should be halted immediately")

    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        reflector.record_heuristic("GENERAL", "Should be halted immediately")

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 25.0, f"Guardian SLA exceeded: {elapsed_ms:.4f}ms"

    guardian.resume()
    res = evaluator.evaluate_plan("Resumed plan")
    assert res is not None


def test_tool_registry_metacognitive_tools():
    phase4_tools = [
        ("evaluate_metacognitive_drift", 0),
        ("reflect_on_plan_efficiency", 0),
        ("record_strategy_heuristic", 1),
    ]

    for tool_name, expected_tier in phase4_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch"
        assert tool_def.preview_fn is not None
        assert tool_def.args_schema is not None
        assert tool_def.handler_fn is not None
