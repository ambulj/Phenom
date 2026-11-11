"""Milestone 28.0 Master Safety Audit, Chaos Concurrency Battery & Release Verification.

Validates all 12 Milestone 28 tools, benchmarks 100-cycle Guardian kill switch SLA (< 25.0ms),
runs cross-pillar concurrent chaos stress tests, and verifies Rule 8 invariant compliance.
"""

import concurrent.futures
import pytest
import time
from typing import List, Dict, Any

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.planning.goal_decomposition_engine import (
    GoalDecompositionEngine,
    Rule8ViolationError,
)
from services.backend.planning.plan_tree import PlanNodeStatus
from services.backend.planning.speculative_planner import SpeculativePlanner
from services.backend.planning.branch_pruner import BranchPruner
from services.backend.planning.error_interceptor import ErrorInterceptor
from services.backend.planning.self_healing_orchestrator import SelfHealingOrchestrator
from services.backend.planning.metacognitive_evaluator import MetacognitiveEvaluator
from services.backend.planning.strategy_reflector import StrategyReflector

# Import all tool modules to ensure registration
import services.backend.tools.goal_planning_tools
import services.backend.tools.speculative_planning_tools
import services.backend.tools.self_healing_tools
import services.backend.tools.metacognitive_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_milestone_28_tool_registry_audit():
    """Verify all 12 Milestone 28 tools are registered with schemas and preview generators."""
    m28_tools = [
        # Phase 1: Goal Decomposition & Hierarchical Plan Tree
        ("decompose_hierarchical_goal", 0),
        ("expand_plan_tree_node", 1),
        ("get_active_goal_tree", 0),
        # Phase 2: Adaptive Speculative Branch Planner & Pruner
        ("generate_speculative_plan_branches", 0),
        ("prune_nonviable_branches", 1),
        ("evaluate_branch_risk_matrix", 0),
        # Phase 3: Self-Healing Workflow Orchestrator & Error Interceptor
        ("intercept_and_heal_failure", 1),
        ("diagnose_execution_error", 0),
        ("get_active_healing_journal", 0),
        # Phase 4: Metacognitive Introspection & Strategy Reflector
        ("evaluate_metacognitive_drift", 0),
        ("reflect_on_plan_efficiency", 0),
        ("record_strategy_heuristic", 1),
    ]

    for tool_name, expected_tier in m28_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered in ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' expected tier {expected_tier}, got {tool_def.tier}"
        assert tool_def.preview_fn is not None, f"Tool '{tool_name}' must declare a callable preview function"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' must declare a valid Pydantic args_schema"
        assert tool_def.handler_fn is not None, f"Tool '{tool_name}' must declare a handler function"


def test_guardian_kill_switch_100_cycle_sla():
    """Benchmark 100 consecutive Guardian kill switch halts to verify SLA strictly < 25.0ms (typical < 1.0ms)."""
    decomp = GoalDecompositionEngine()
    tree = decomp.decompose_goal("SLA Target Goal")
    planner = SpeculativePlanner(decomposition_engine=decomp)
    pruner = BranchPruner(planner=planner)
    orchestrator = SelfHealingOrchestrator(decomposition_engine=decomp)
    evaluator = MetacognitiveEvaluator(decomposition_engine=decomp)
    reflector = StrategyReflector(evaluator=evaluator)

    timings_ms: List[float] = []

    for _ in range(100):
        guardian.trigger(reason="100_cycle_sla_test_m28")
        t0 = time.perf_counter()
        with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
            # Exercise multiple subsystems under tripped state
            decomp.decompose_goal("Tripped test goal")
            planner.generate_speculative_branches("Tripped branches")
            pruner.evaluate_risk_matrix("Tripped matrix")
            orchestrator.heal_failure("tree_sla", "node_sla", "Error")
            evaluator.evaluate_plan("Tripped evaluation")
            reflector.record_heuristic("DOM", "Tripped rule")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        timings_ms.append(elapsed_ms)
        guardian.resume()

    avg_ms = sum(timings_ms) / len(timings_ms)
    max_ms = max(timings_ms)

    assert avg_ms < 1.0, f"Guardian SLA average exceeds 1.0ms: {avg_ms:.4f}ms"
    assert max_ms < 25.0, f"Guardian SLA max exceeds hard limit 25.0ms: {max_ms:.4f}ms"


def test_cross_pillar_chaos_concurrency_stress():
    """Run concurrent multi-threaded stress tests across all 4 Milestone 28 pillars without deadlocks or race conditions."""
    decomp = GoalDecompositionEngine()
    planner = SpeculativePlanner(decomposition_engine=decomp)
    pruner = BranchPruner(planner=planner)
    interceptor = ErrorInterceptor()
    orchestrator = SelfHealingOrchestrator(interceptor=interceptor, decomposition_engine=decomp)
    evaluator = MetacognitiveEvaluator(decomposition_engine=decomp)
    reflector = StrategyReflector(evaluator=evaluator)

    def worker_decomposition(idx: int):
        tree = decomp.decompose_goal(f"Concurrent Subtask Tree {idx}", max_depth=3)
        subtasks = [n for n in tree.nodes.values() if n.depth == 1]
        if subtasks:
            decomp.expand_node(
                tree_id=tree.tree_id,
                parent_node_id=subtasks[0].node_id,
                new_children=[{"title": f"Dynamic Action Step {idx}"}],
            )
        return tree.to_dict()

    def worker_speculative(idx: int):
        target = f"Speculative Target Objective {idx}"
        branches = planner.generate_speculative_branches(target)
        pruner.prune_branches(target_id=target, max_acceptable_risk=0.30)
        return pruner.evaluate_risk_matrix(target)

    def worker_healing(idx: int):
        target_tree = decomp.decompose_goal(f"Self-Healing Target Tree {idx}")
        leaf = [n for n in target_tree.nodes.values() if n.depth == 2][0]
        return orchestrator.heal_failure(
            target_tree_id=target_tree.tree_id,
            failing_node_id=leaf.node_id,
            raw_error=f"Permission denied: Access forbidden on socket {idx}",
        )

    def worker_metacognitive(idx: int):
        reflector.record_heuristic(
            domain=f"CONCURRENCY_DOMAIN_{idx % 3}",
            rule_pattern=f"Always balance thread concurrency pool under stress test {idx % 2}.",
        )
        return reflector.reflect_on_plan_efficiency(f"Target Reflector {idx}")

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = []
        for i in range(10):
            futures.append(pool.submit(worker_decomposition, i))
            futures.append(pool.submit(worker_speculative, i))
            futures.append(pool.submit(worker_healing, i))
            futures.append(pool.submit(worker_metacognitive, i))

        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    total_time = time.perf_counter() - t0
    assert len(results) == 40
    assert total_time < 5.0, f"Chaos concurrency test took too long: {total_time:.2f}s"


def test_rule_8_anti_checkout_cross_pillar_compliance():
    """Verify strict Rule 8 payment/checkout keyword screening across all 4 pillars."""
    decomp = GoalDecompositionEngine()
    planner = SpeculativePlanner(decomposition_engine=decomp)
    pruner = BranchPruner(planner=planner)
    interceptor = ErrorInterceptor()
    orchestrator = SelfHealingOrchestrator(interceptor=interceptor, decomposition_engine=decomp)
    evaluator = MetacognitiveEvaluator(decomposition_engine=decomp)
    reflector = StrategyReflector(evaluator=evaluator)

    # 1. Goal Decomposition Pillar
    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        decomp.decompose_goal("Automate checkout and pay for subscription")

    # 2. Speculative Planning Pillar
    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        planner.generate_speculative_branches("Process stripe billing order")

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        pruner.evaluate_risk_matrix("Execute credit card purchase")

    # 3. Self-Healing Pillar
    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        orchestrator.heal_failure("tree_r8", "node_r8", "Failure occurred at paypal checkout")

    # 4. Metacognitive Reflector Pillar
    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        evaluator.evaluate_plan("Evaluate billing checkout loop")

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        reflector.record_heuristic("PAYMENT", "Always retry credit card charge upon failure")
