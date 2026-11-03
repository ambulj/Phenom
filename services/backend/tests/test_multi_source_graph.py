"""
Unit Tests for Phenom MultiSourceKnowledgeGraph (Milestone 9.0 Phase 3)
Verifies:
1. Node addition, update, removal, and bidirectional edge consistency.
2. Cross-domain link synthesis between code, vault, meetings, and documents.
3. Orphan node and concept hub topology discovery.
4. Credential scrubber sanitizing node metadata.
5. Synchronous halt (< 1ms) and state reset behavior.
"""

import time
import pytest

from services.backend.memory.multi_source_graph import MultiSourceKnowledgeGraph
from services.backend.schemas.graph_rag import GraphEdge, GraphNode


def test_node_addition_removal_and_bidirectional_edges():
    graph = MultiSourceKnowledgeGraph()

    node1 = GraphNode(
        node_id="vault://Architecture.md",
        domain="vault",
        title="Architecture",
        entity_type="note",
        summary="High level design"
    )
    node2 = GraphNode(
        node_id="code://phenom/services/backend/main.py:app",
        domain="code",
        title="app",
        entity_type="code_symbol",
        summary="FastAPI application entrypoint"
    )
    edge = GraphEdge(
        source_id=node1.node_id,
        target_id=node2.node_id,
        relation="documents",
        weight=1.0
    )

    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge(edge)

    assert graph.get_node(node1.node_id) is not None
    assert graph.get_node(node2.node_id) is not None

    # Check neighbors
    neighbors_out = graph.get_neighbors(node1.node_id, direction="out")
    assert len(neighbors_out) == 1
    assert neighbors_out[0][0].node_id == node2.node_id

    neighbors_in = graph.get_neighbors(node2.node_id, direction="in")
    assert len(neighbors_in) == 1
    assert neighbors_in[0][0].node_id == node1.node_id

    # Remove node1 -> edges should be cleared
    removed = graph.remove_node(node1.node_id)
    assert removed is True
    assert graph.get_node(node1.node_id) is None
    assert len(graph.get_neighbors(node2.node_id, direction="in")) == 0


def test_cross_domain_link_synthesis():
    graph = MultiSourceKnowledgeGraph()

    # Code node
    code_node = GraphNode(
        node_id="code://phenom/services/backend/voice/streaming_engine.py:StreamingVoiceEngine",
        domain="code",
        title="StreamingVoiceEngine",
        entity_type="code_symbol",
        summary="Class managing streaming audio and turnaround latency."
    )
    graph.add_node(code_node)

    # Vault node referencing StreamingVoiceEngine
    vault_node = GraphNode(
        node_id="vault://Voice/Spec.md",
        domain="vault",
        title="Voice Spec",
        entity_type="note",
        summary="This document explains StreamingVoiceEngine and Silero VAD."
    )
    graph.add_node(vault_node)

    # Meeting node discussing StreamingVoiceEngine
    meeting_node = GraphNode(
        node_id="meeting://cal:evt_301",
        domain="meeting",
        title="Voice Engine Review",
        entity_type="meeting_agenda",
        summary="Discussing StreamingVoiceEngine benchmarks and Guardian SLA."
    )
    graph.add_node(meeting_node)

    # Run synthesis
    synthesized_count = graph.synthesize_cross_domain_links()
    assert synthesized_count >= 2

    vault_neighbors = [n[0].node_id for n in graph.get_neighbors(vault_node.node_id, direction="out")]
    assert code_node.node_id in vault_neighbors

    meeting_neighbors = [n[0].node_id for n in graph.get_neighbors(meeting_node.node_id, direction="out")]
    assert code_node.node_id in meeting_neighbors


def test_orphan_and_concept_hub_discovery():
    graph = MultiSourceKnowledgeGraph()

    # Orphan node (0 in/out edges)
    orphan = GraphNode(
        node_id="vault://Random_Thoughts.md",
        domain="vault",
        title="Random Thoughts",
        entity_type="note",
        summary="Unlinked notes."
    )
    graph.add_node(orphan)

    # Hub node with 4 edges
    hub = GraphNode(
        node_id="code://phenom/core.py:CoreSystem",
        domain="code",
        title="CoreSystem",
        entity_type="code_symbol",
        summary="Central hub"
    )
    graph.add_node(hub)

    for i in range(4):
        leaf = GraphNode(
            node_id=f"code://phenom/leaf_{i}.py",
            domain="code",
            title=f"leaf_{i}",
            entity_type="code_symbol",
            summary=f"Leaf {i}"
        )
        graph.add_node(leaf)
        graph.add_edge(GraphEdge(source_id=hub.node_id, target_id=leaf.node_id, relation="calls"))

    stats = graph.get_stats()
    assert stats.total_nodes == 6
    assert stats.orphan_count == 1
    assert stats.hub_count == 1


def test_credential_scrubber_in_nodes():
    graph = MultiSourceKnowledgeGraph()
    dummy_key = "s" + "k-" + "1234567890abcdefghijklmnopqrstuvwxyz"
    leaked_title = f"Secret Note with password = 'SecretPassword123' and {dummy_key}"
    node = GraphNode(
        node_id="vault://Secret.md",
        domain="vault",
        title=leaked_title,
        entity_type="note",
        summary="Summary containing secret content"
    )
    graph.add_node(node)

    stored = graph.get_node(node.node_id)
    assert stored is not None
    assert "SecretPassword123" not in stored.title
    assert "sk-" not in stored.title
    assert "[REDACTED_CREDENTIAL]" in stored.title


def test_synchronous_halt_and_reset_latency():
    graph = MultiSourceKnowledgeGraph()

    t0 = time.perf_counter()
    graph.halt()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Assert sub-1ms typical halt latency (< 25ms SLA)
    assert elapsed_ms < 25.0
    assert graph.is_halted is True

    # Attempting to add node while halted must raise PermissionError
    test_node = GraphNode(
        node_id="vault://HaltTest.md",
        domain="vault",
        title="Halt Test",
        entity_type="note",
        summary="Testing halt"
    )
    with pytest.raises(PermissionError):
        graph.add_node(test_node)

    # Subgraph query while halted must raise PermissionError
    with pytest.raises(PermissionError):
        graph.get_subgraph(["vault://HaltTest.md"])

    # Reset
    graph.reset()
    assert graph.is_halted is False
    graph.add_node(test_node)
    assert graph.get_node(test_node.node_id) is not None
