"""
Unit Test Suite for Sovereign Neuro-Symbolic Sleep & Dream Engine (DRM-01, SAF-01, SAF-02).
Tests:
- Episodic trace recording and replay buffer mechanics
- Schema abstraction and conceptual heuristic generation
- MultiSourceKnowledgeGraph dead-link pruning and transient decay
- Duplicate entity deduplication and edge re-routing
- Idle check gating and manual force override
- Guardian kill switch synchronous halt
"""

import time
import pytest
from services.backend.memory.dream_engine import (
    DreamConsolidationEngine,
    EpisodicReplayBuffer,
    GraphCompactor,
)
from services.backend.memory.multi_source_graph import MultiSourceKnowledgeGraph
from services.backend.schemas.dream import DreamPhaseStatus, EpisodicTrace
from services.backend.schemas.graph_rag import GraphNode, GraphEdge
from services.backend.safety.guardian import GuardianKillSwitch


def test_episodic_replay_buffer_bounding():
    """Verify episodic buffer bounds to max capacity and maintains FIFO eviction."""
    buf = EpisodicReplayBuffer(max_traces=5)
    for i in range(10):
        trace = EpisodicTrace(
            trace_id=f"t_{i}",
            source="action_log",
            action_type="test_action",
            summary=f"Episode {i}",
        )
        buf.record_trace(trace)

    recent = buf.get_recent_traces(limit=10)
    assert len(recent) == 5
    assert recent[0].trace_id == "t_5"
    assert recent[-1].trace_id == "t_9"


def test_dream_cycle_schema_abstraction():
    """Verify replayed operational traces synthesize generalized conceptual schemas."""
    graph = MultiSourceKnowledgeGraph()
    engine = DreamConsolidationEngine(graph=graph, idle_threshold_seconds=0.0)

    # Record 4 recurring successful automation episodes
    for i in range(4):
        engine.record_episode(
            action_type="gui_automation",
            tool_name="gui_execute_action",
            summary=f"Automated window placement step {i}",
            status="success",
        )

    # Run dream cycle with force=True
    report = engine.run_dream_cycle(force=True, max_episodes=50)

    assert report.episodes_replayed == 4
    assert report.schemas_formed >= 1
    assert report.duration_ms >= 0.0

    # Verify schema ingested into knowledge graph
    schema_nodes = [n for n in graph._nodes.values() if n.domain == "dream_schema"]
    assert len(schema_nodes) >= 1
    assert "gui_execute_action" in schema_nodes[0].summary
    assert schema_nodes[0].metadata.get("confidence", 0) > 0.6


def test_graph_compactor_prunes_dangling_and_stale_edges():
    """Verify dead links (missing source/target) and decayed transient edges are purged."""
    graph = MultiSourceKnowledgeGraph()

    # Create 2 valid nodes
    node_a = GraphNode(node_id="node_a", domain="test", entity_type="doc", title="Node A", summary="A")
    node_b = GraphNode(node_id="node_b", domain="test", entity_type="doc", title="Node B", summary="B")
    graph.add_node(node_a)
    graph.add_node(node_b)

    # Edge 1: Valid edge
    edge_valid = GraphEdge(
        source_id="node_a", target_id="node_b", relation="references", weight=1.0, metadata={"created_at": time.time()}
    )
    graph.add_edge(edge_valid)

    # Edge 2: Dangling edge (references non-existent node_c)
    edge_dangling = GraphEdge(
        source_id="node_a", target_id="node_c", relation="references", weight=1.0, metadata={"created_at": time.time()}
    )
    graph.add_edge(edge_dangling)

    # Edge 3: Decayed transient edge (created 30 days ago)
    old_ts = time.time() - (30 * 86400.0)
    edge_decayed = GraphEdge(
        source_id="node_a", target_id="node_b", relation="transient_ref", weight=0.5, metadata={"created_at": old_ts}
    )
    graph.add_edge(edge_decayed)

    compactor = GraphCompactor(graph)
    pruned_count, pruned_ids = compactor.prune_dead_and_stale_links(decay_days_threshold=14, dry_run=False)

    assert pruned_count == 2
    assert any("node_a->node_c" in p for p in pruned_ids)
    assert any("transient_ref" in p for p in pruned_ids)
    assert edge_valid in graph._out_edges["node_a"]
    assert edge_dangling not in graph._out_edges["node_a"]
    assert edge_decayed not in graph._out_edges["node_a"]


def test_graph_compactor_merges_duplicate_entities():
    """Verify near-duplicate entity nodes with identical titles are merged and edges re-routed."""
    graph = MultiSourceKnowledgeGraph()

    node_1 = GraphNode(node_id="n_1", domain="code", entity_type="entity", title="Compiler", summary="Main compiler", tags=["v1"])
    node_2 = GraphNode(node_id="n_2", domain="code", entity_type="entity", title="  compiler  ", summary="Duplicate compiler", tags=["v2"])
    node_3 = GraphNode(node_id="n_3", domain="code", entity_type="entity", title="Target", summary="Target")

    graph.add_node(node_1)
    graph.add_node(node_2)
    graph.add_node(node_3)

    # Edge from n_2 to n_3
    edge = GraphEdge(source_id="n_2", target_id="n_3", relation="calls")
    graph.add_edge(edge)

    compactor = GraphCompactor(graph)
    merged_count, merged_ids = compactor.merge_duplicate_entities(dry_run=False)

    assert merged_count == 1
    assert "n_2" in merged_ids
    assert "n_2" not in graph._nodes
    assert "n_1" in graph._nodes

    # Verify edge re-routed to n_1
    out_edges_n1 = graph._out_edges.get("n_1", set())
    assert any(e.target_id == "n_3" and e.relation == "calls" for e in out_edges_n1)
    assert "v2" in graph._nodes["n_1"].tags


def test_idle_gating_and_force_override():
    """Verify non-idle system refuses execution without force=True."""
    engine = DreamConsolidationEngine(idle_threshold_seconds=1000.0)
    engine.record_activity()

    assert not engine.is_idle()
    with pytest.raises(ValueError, match="System is not idle"):
        engine.run_dream_cycle(force=False)

    # Force should bypass idle check
    report = engine.run_dream_cycle(force=True)
    assert report.cycle_id is not None


def test_guardian_halt_blocks_dream_cycle():
    """SAF-02: Assert Guardian halt immediately cancels and denies dream execution."""
    guardian = GuardianKillSwitch()
    engine = DreamConsolidationEngine()
    guardian.add_state_callback(lambda s: engine.halt() if s == "halted" else engine.reset())

    guardian.trigger("lockdown")
    assert engine.is_halted()

    with pytest.raises(PermissionError, match="halted"):
        engine.run_dream_cycle(force=True)

    with pytest.raises(PermissionError, match="halted"):
        engine.prune_stale_memory()

    guardian.resume()
    assert not engine.is_halted()
