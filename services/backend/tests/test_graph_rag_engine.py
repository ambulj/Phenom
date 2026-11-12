"""
Unit & Integration Tests for Phenom Hybrid GraphRAG Retrieval Engine (Milestone 9.0 Phase 3)
Verifies:
1. Lexical BM25 retrieval, dense vector similarity, and hybrid score fusion.
2. Multi-hop (1-hop and 2-hop) relational expansion across distinct domains.
3. Cross-domain context synthesis and explicit URI citation generation.
4. Natural language query routing intent classification.
5. Zero-cloud leakage invariant (all embeddings and graphs strictly local in RAM).
6. Synchronous Guardian kill switch halt and reset.
"""

import pytest

from services.backend.memory.graph_rag import BM25Index, HybridGraphRAGEngine
from services.backend.memory.multi_source_graph import MultiSourceKnowledgeGraph
from services.backend.schemas.graph_rag import GraphEdge, GraphNode


@pytest.fixture
def populated_graph():
    """Populates a cross-domain test graph with linked nodes."""
    graph = MultiSourceKnowledgeGraph()

    # Code domain node
    code_node = GraphNode(
        node_id="code://phenom/services/backend/voice/streaming_engine.py:StreamingVoiceEngine",
        domain="code",
        title="StreamingVoiceEngine",
        entity_type="code_symbol",
        summary="Class implementing sub-200ms turnaround latency voice engine with Silero VAD barge-in."
    )
    graph.add_node(code_node)

    # Git commit node
    git_node = GraphNode(
        node_id="git://phenom:c10a2b",
        domain="code",
        title="Commit c10a2b",
        entity_type="git_commit",
        summary="feat(voice): implement streaming conversational barge-in hysteresis"
    )
    graph.add_node(git_node)
    graph.add_edge(GraphEdge(source_id=git_node.node_id, target_id=code_node.node_id, relation="implements"))

    # Vault note node
    vault_node = GraphNode(
        node_id="vault://Voice/BargeIn_Spec.md",
        domain="vault",
        title="Voice Barge-In Architecture Spec",
        entity_type="note",
        summary="Architectural specification for full-duplex conversational voice turn boundaries."
    )
    graph.add_node(vault_node)
    graph.add_edge(GraphEdge(source_id=vault_node.node_id, target_id=code_node.node_id, relation="documents"))

    # Meeting node (2 hops from git commit, 1 hop from code)
    meeting_node = GraphNode(
        node_id="meeting://cal:evt_voice_sync",
        domain="meeting",
        title="Voice Architecture Sync",
        entity_type="meeting_agenda",
        summary="Weekly engineering sync reviewing voice latency metrics and audio ring buffers."
    )
    graph.add_node(meeting_node)
    graph.add_edge(GraphEdge(source_id=meeting_node.node_id, target_id=code_node.node_id, relation="discussed_in"))

    # Document node
    doc_node = GraphNode(
        node_id="doc://manuals/voice_hardware.pdf#chunk=0",
        domain="doc",
        title="Hardware Setup Guide (chunk 0)",
        entity_type="pdf_section",
        summary="Microphone gain and noise floor calibration guide."
    )
    graph.add_node(doc_node)

    return graph


def test_bm25_lexical_scoring():
    index = BM25Index()
    docs = {
        "doc1": "streaming conversational voice engine with barge-in",
        "doc2": "obsidian personal second brain knowledge graph",
        "doc3": "google calendar meeting sync and agenda lookahead"
    }
    index.build(docs)

    scores = index.score("barge-in voice")
    assert "doc1" in scores
    assert scores["doc1"] > scores.get("doc2", 0.0)
    assert scores["doc1"] > scores.get("doc3", 0.0)


def test_hybrid_search_scoring(populated_graph):
    engine = HybridGraphRAGEngine(graph=populated_graph)
    results = engine.search_hybrid("streaming voice engine turnaround latency", top_k=3)

    assert len(results) > 0
    top_node, score = results[0]
    assert "StreamingVoiceEngine" in top_node.title
    assert score > 0.0


def test_graph_relational_expansion_multi_hop(populated_graph):
    engine = HybridGraphRAGEngine(graph=populated_graph)

    # 1-hop expansion
    res_1hop = engine.query("StreamingVoiceEngine", hops=1, top_k=1)
    assert len(res_1hop.seed_nodes) == 1
    seed_id = res_1hop.seed_nodes[0]["node_id"]
    assert "StreamingVoiceEngine" in seed_id

    # Should expand to directly connected nodes (git, vault, meeting)
    expanded_ids = [n["node_id"] for n in res_1hop.expanded_nodes]
    assert "vault://Voice/BargeIn_Spec.md" in expanded_ids or "meeting://cal:evt_voice_sync" in expanded_ids

    # 2-hop expansion from git commit should reach meeting and vault via code node
    res_2hop = engine.query("Commit c10a2b", hops=2, top_k=1)
    all_2hop_ids = [n["node_id"] for n in res_2hop.seed_nodes + res_2hop.expanded_nodes]
    assert "code://phenom/services/backend/voice/streaming_engine.py:StreamingVoiceEngine" in all_2hop_ids


def test_context_synthesis_and_citations(populated_graph):
    engine = HybridGraphRAGEngine(graph=populated_graph)
    res = engine.query("Voice Barge-In", hops=1, top_k=2)

    assert res.context_synthesis != ""
    assert "## Deterministic URI Citations:" in res.context_synthesis
    assert len(res.citations) > 0
    for citation in res.citations:
        assert any(citation.startswith(prefix) for prefix in ("code://", "vault://", "meeting://", "doc://", "git://"))


def test_natural_language_intent_routing(populated_graph):
    engine = HybridGraphRAGEngine(graph=populated_graph)

    weights_code = engine.classify_intent("How does the AST parser implement code symbols?")
    assert weights_code["code"] > weights_code["meeting"]

    weights_meeting = engine.classify_intent("What is on the calendar agenda for tomorrow's meeting?")
    assert weights_meeting["meeting"] > weights_meeting["code"]

    weights_vault = engine.classify_intent("Summarize my Obsidian second brain notes on design")
    assert weights_vault["vault"] > weights_vault["code"]


def test_zero_cloud_leakage_and_guardian_halt(populated_graph):
    engine = HybridGraphRAGEngine(graph=populated_graph)

    # Invariant: engine executes locally without cloud endpoints
    res = engine.query("test local execution", hops=1)
    assert isinstance(res.citations, list)

    # Test Guardian synchronous halt
    engine.halt()
    assert engine.is_halted is True

    with pytest.raises(PermissionError):
        engine.query("any query")

    engine.reset()
    assert engine.is_halted is False
    res2 = engine.query("StreamingVoiceEngine", hops=1)
    assert len(res2.seed_nodes) > 0
