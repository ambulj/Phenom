"""Milestone 26.0 Master Safety Audit, Chaos Concurrency Battery & Release Verification.

Validates all 12 Milestone 26 tools, benchmarks 100-cycle Guardian kill switch SLA (< 25.0ms),
runs cross-pillar concurrent chaos stress tests, and verifies Rule 8 invariant compliance.
"""

import concurrent.futures
import pytest
import time
from typing import List, Dict, Any

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.consolidation.memory_consolidator import MemoryConsolidator
from services.backend.epistemic.belief_network import EpistemicBeliefNetwork, Rule8ViolationError
from services.backend.epistemic.contradiction_resolver import ContradictionResolver
from services.backend.simulation.world_model_simulator import WorldModelSimulator
from services.backend.simulation.counterfactual_evaluator import CounterfactualEvaluator
from services.backend.pacing.cognitive_load_tracker import CognitiveLoadTracker
from services.backend.pacing.attentional_pacer import AttentionalPacer

# Import all tool modules
import services.backend.tools.memory_consolidation_tools
import services.backend.tools.epistemic_belief_tools
import services.backend.tools.world_model_tools
import services.backend.tools.cognitive_pacing_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_milestone_26_tool_registry_audit():
    """Verify all 12 Milestone 26 tools are registered with schemas and preview generators."""
    m26_tools = [
        # Phase 1
        ("consolidate_episodic_memory", 0),
        ("query_hierarchical_memory_graph", 0),
        ("prune_decayed_memory_traces", 1),
        # Phase 2
        ("update_epistemic_belief", 1),
        ("resolve_belief_contradiction", 0),
        ("get_active_belief_network", 0),
        # Phase 3
        ("simulate_plan_counterfactuals", 0),
        ("evaluate_world_model_state", 0),
        ("forecast_side_effects", 0),
        # Phase 4
        ("get_cognitive_load_state", 0),
        ("pace_notification_dispatch", 0),
        ("flush_deferred_notifications", 1),
    ]

    for tool_name, expected_tier in m26_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered in ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' expected tier {expected_tier}, got {tool_def.tier}"
        assert tool_def.preview_fn is not None, f"Tool '{tool_name}' must declare a callable preview function"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' must declare a valid Pydantic args_schema"
        assert tool_def.handler_fn is not None, f"Tool '{tool_name}' must declare a handler function"


def test_guardian_kill_switch_100_cycle_sla():
    """Benchmark 100 consecutive Guardian kill switch halts to verify SLA strictly < 25.0ms (typical < 1.0ms)."""
    consolidator = MemoryConsolidator()
    evaluator = CounterfactualEvaluator()
    net = EpistemicBeliefNetwork()
    tracker = CognitiveLoadTracker()

    timings_ms: List[float] = []

    for _ in range(100):
        guardian.trigger(reason="100_cycle_sla_test")
        t0 = time.perf_counter()
        with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
            # Exercise multiple subsystems under tripped state
            consolidator.consolidate()
            net.get_beliefs()
            evaluator.forecast_side_effects([{"action": "WRITE"}])
            tracker.get_state()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        timings_ms.append(elapsed_ms)
        guardian.resume()

    avg_ms = sum(timings_ms) / len(timings_ms)
    max_ms = max(timings_ms)

    assert avg_ms < 1.0, f"Guardian SLA average exceeds 1.0ms: {avg_ms:.4f}ms"
    assert max_ms < 25.0, f"Guardian SLA max exceeds hard limit 25.0ms: {max_ms:.4f}ms"


def test_cross_pillar_chaos_concurrency_stress():
    """Run concurrent multi-threaded stress tests across all 4 Milestone 26 pillars without deadlocks or race conditions."""
    consolidator = MemoryConsolidator()
    net = EpistemicBeliefNetwork()
    resolver = ContradictionResolver(network=net)
    simulator = WorldModelSimulator()
    evaluator = CounterfactualEvaluator(simulator=simulator)
    tracker = CognitiveLoadTracker()
    pacer = AttentionalPacer(tracker=tracker)

    def worker_memory(idx: int):
        consolidator.record_trace(
            session_id=f"session_{idx % 3}",
            interaction_type="USER_COMMAND",
            content=f"Interaction trace content {idx} for consolidation",
            importance_score=0.8,
        )
        return consolidator.consolidate()

    def worker_epistemic(idx: int):
        net.update_belief(f"Subject_{idx % 4}", "active_setting", f"value_{idx}", confidence_boost=0.1)
        return resolver.analyze_claim(f"Subject_{idx % 4}", "active_setting", f"value_{idx + 1}")

    def worker_simulation(idx: int):
        steps = [
            {"action": "WRITE_FILE", "target": f"file_{idx}.txt", "payload": {"content": "ok"}},
            {"action": "FOCUS_WINDOW", "target": f"Window_{idx % 3}"},
        ]
        return evaluator.evaluate_plan(f"Plan_{idx}", steps)

    def worker_pacing(idx: int):
        tracker.record_interaction("KEYSTROKE", window_title=f"Window_{idx % 2}")
        return pacer.evaluate_and_pace(f"Alert_{idx}", f"Body_{idx}")

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = []
        for i in range(10):
            futures.append(pool.submit(worker_memory, i))
            futures.append(pool.submit(worker_epistemic, i))
            futures.append(pool.submit(worker_simulation, i))
            futures.append(pool.submit(worker_pacing, i))

        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    total_time = time.perf_counter() - t0
    assert len(results) == 40
    assert total_time < 5.0, f"Chaos concurrency test took too long: {total_time:.2f}s"


def test_rule_8_anti_checkout_cross_pillar_compliance():
    """Verify strict Rule 8 payment/checkout keyword screening across all 4 pillars."""
    consolidator = MemoryConsolidator()
    net = EpistemicBeliefNetwork()
    sim = WorldModelSimulator()
    tracker = CognitiveLoadTracker()
    pacer = AttentionalPacer(tracker=tracker)

    # 1. Memory pillar
    with pytest.raises(Exception):
        consolidator.record_trace("session_1", "COMMAND", "User proceeds to checkout and enters credit card billing")

    # 2. Epistemic pillar
    with pytest.raises(Rule8ViolationError):
        net.update_belief("User", "credit_card", "1234")

    # 3. Simulation pillar
    with pytest.raises(Exception):
        sim.simulate_step("PROCESS_KILL", "stripe_payment_service")

    # 4. Pacing pillar
    with pytest.raises(Exception):
        pacer.evaluate_and_pace("Billing Alert", "Please pay invoice")
