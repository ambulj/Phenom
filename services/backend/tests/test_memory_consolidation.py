"""Unit and Safety Integration Tests for Episodic Memory Consolidation & Hierarchical Abstractor.

Validates episodic trace recording, consolidation passes, exponential decay, access reinforcement,
hierarchical abstraction graph tiers, soft-pruning (Rule 7), Rule 8 defenses, and Guardian SLA.
Phase 26-01 (MEM-06, ABS-01, SAF-01, SAF-02).
"""

import time
import pytest

from services.backend.consolidation.memory_consolidator import (
    MemoryConsolidator,
    EpisodicTrace,
    SemanticKnowledgeNode,
    Rule8ViolationError as ConsolidationR8,
    memory_consolidator,
)
from services.backend.consolidation.hierarchical_abstractor import (
    HierarchicalAbstractor,
    Rule8ViolationError as AbstractorR8,
    hierarchical_abstractor,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.memory_consolidation_tools  # Ensure tools are loaded


@pytest.fixture(autouse=True)
def reset_state():
    guardian.resume()
    yield
    guardian.resume()


def test_episodic_trace_recording_and_consolidation():
    """Verify episodic traces record properly and consolidate into clustered semantic nodes."""
    consolidator = MemoryConsolidator()

    # Record 3 related traces
    t1 = consolidator.record_trace("sess_01", "CODE_EDIT", "Fixed Python AST visitor node parsing bug", 0.7)
    t2 = consolidator.record_trace("sess_01", "USER_CORRECTION", "User prefers explicit AST traversal sequence in python", 0.8)
    t3 = consolidator.record_trace("sess_01", "TOOL_CALL", "Ran python pytest suite with AST code changes", 0.6)

    assert len(consolidator.get_traces()) == 3
    assert not t1.is_consolidated

    # Consolidate
    nodes = consolidator.consolidate()
    assert len(nodes) >= 1
    python_node = next((n for n in nodes if "Python" in n.cluster_topic), None)
    assert python_node is not None
    assert len(python_node.source_trace_ids) == 3
    assert python_node.confidence >= 0.85
    assert t1.is_consolidated is True


def test_exponential_importance_decay_and_access_reinforcement():
    """Verify decay formula I(t) decreases with delta time and reinforces with access count."""
    consolidator = MemoryConsolidator()
    t0 = time.time()

    trace = EpisodicTrace(
        session_id="sess_02",
        interaction_type="QUERY",
        content="Transient search for utility function",
        importance_score=0.80,
        timestamp=t0,
        access_count=1,
    )

    # Immediate calculation (0 hours)
    score_now = consolidator.compute_decayed_importance(trace, current_time=t0)
    assert score_now >= 0.80

    # Decayed after 24 hours (approx delta_hours = 24)
    t_future = t0 + (24 * 3600.0)
    score_future = consolidator.compute_decayed_importance(trace, current_time=t_future)
    assert score_future < score_now

    # Reinforcement: with high access count, decay is countered
    trace_reinforced = trace.model_copy()
    trace_reinforced.access_count = 10
    score_reinforced = consolidator.compute_decayed_importance(trace_reinforced, current_time=t_future)
    assert score_reinforced > score_future


def test_hierarchical_graph_levels_and_querying():
    """Verify memory hierarchy contains micro, macro, and core tiers, and supports semantic querying."""
    consolidator = MemoryConsolidator()
    # Add multiple traces to generate multiple micro nodes
    consolidator.record_trace("s1", "CODE_EDIT", "Refactored React HUD component state management", 0.8)
    consolidator.record_trace("s1", "TOOL_CALL", "Vite build successful for frontend HUD", 0.7)
    consolidator.consolidate()

    abstractor = HierarchicalAbstractor(consolidator=consolidator)
    graph = abstractor.build_graph()

    assert graph.total_node_count >= 5  # Core rules (4) + micro nodes + macro
    assert 1 in graph.abstraction_levels  # Micro
    assert 3 in graph.abstraction_levels  # Core Rules

    # Query core rule
    results_rule = abstractor.query_graph("Safety confirmation tiers", min_level=3)
    assert len(results_rule) >= 1
    assert any("Rule 1" in r.distilled_heuristic for r in results_rule)

    # Query frontend
    results_frontend = abstractor.query_graph("React frontend", min_level=1)
    assert len(results_frontend) >= 1


def test_soft_pruning_rule_7():
    """Verify soft-pruning marks decayed traces pruned without permanent deletion."""
    consolidator = MemoryConsolidator()
    t0 = time.time()

    trace = consolidator.record_trace("s3", "QUERY", "Old temporary test trace", 0.15)
    trace.timestamp = t0 - (48 * 3600.0)  # 48 hours ago

    pruned = consolidator.soft_prune_decayed(decay_threshold=0.20, current_time=t0)
    assert trace.trace_id in pruned

    # Active traces exclude pruned
    active = consolidator.get_traces(include_pruned=False)
    assert trace.trace_id not in [t.trace_id for t in active]

    # Cold storage retains trace
    cold = consolidator.get_traces(include_pruned=True)
    assert trace.trace_id in [t.trace_id for t in cold]


def test_rule_8_anti_checkout_enforcement():
    """Verify payment and checkout memory operations are blocked with Rule8ViolationError."""
    consolidator = MemoryConsolidator()
    abstractor = HierarchicalAbstractor(consolidator=consolidator)

    with pytest.raises(ConsolidationR8, match="Rule 8"):
        consolidator.record_trace("s4", "QUERY", "Checkout shopping cart with saved credit card")

    with pytest.raises(AbstractorR8, match="Rule 8"):
        abstractor.query_graph("How to pay and complete checkout automatically")


def test_guardian_kill_switch_sla_halt():
    """Verify Guardian kill switch synchronously interrupts memory consolidation in < 25.0ms SLA."""
    guardian.trigger("Emergency Memory Consolidation Halt")
    assert guardian.is_halted

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        memory_consolidator.consolidate()
    halt_duration_ms = (time.perf_counter() - t0) * 1000.0

    assert halt_duration_ms < 25.0, f"Halt latency {halt_duration_ms:.4f}ms exceeded 25.0ms SLA"

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        hierarchical_abstractor.build_graph()

    guardian.resume()
    assert not guardian.is_halted


def test_tool_registry_and_previews():
    """Verify tool registration, tier classifications, and preview generations."""
    cons_tool = registry.get("consolidate_episodic_memory")
    assert cons_tool is not None
    assert cons_tool.tier == 0
    preview_cons = cons_tool.generate_preview({})
    assert "memory consolidation pass" in preview_cons

    query_tool = registry.get("query_hierarchical_memory_graph")
    assert query_tool is not None
    assert query_tool.tier == 0
    preview_query = query_tool.generate_preview({"query": "python style", "min_level": 2})
    assert "python style" in preview_query

    prune_tool = registry.get("prune_decayed_memory_traces")
    assert prune_tool is not None
    assert prune_tool.tier == 1
    preview_prune = prune_tool.generate_preview({"decay_threshold": 0.25})
    assert "0.25" in preview_prune
