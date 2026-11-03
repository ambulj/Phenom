"""
Phenom Milestone 9.0 Phase 3: Guardian Kill Switch Sub-25ms SLA & Safety Verification (SAF-01, SAF-02)

Verifies:
1. Strict ToolRegistry registration, risk tiering (Tier 0 & Tier 1), Pydantic schemas, and preview generation (SAF-01).
2. Synchronous execution time of Guardian trigger is strictly < 25.0ms SLA (< 1ms typical) across multi-source knowledge graph (SAF-02).
3. Synchronous halt cascade halts MultiSourceKnowledgeGraph and HybridGraphRAGEngine immediately.
4. Universal rejection of subsequent GraphRAG operations and tool calls with PermissionError while halted.
5. Clean state restoration and resumption via guardian.resume().
"""

import time
import pytest

from services.backend.main import on_guardian_state_change
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.memory.multi_source_graph import multi_source_graph
from services.backend.memory.graph_rag import graph_rag_engine
from services.backend.schemas.graph_rag import (
    GraphQueryArgs,
    GraphStatsArgs,
    GraphReindexArgs,
    GraphNode,
)
import services.backend.tools.graph_rag_tools as graph_rag_tools


@pytest.fixture(autouse=True)
def reset_milestone_9_phase_3_components():
    """Ensure clean state before and after each test."""
    guardian.resume()
    multi_source_graph.reset()
    graph_rag_engine.reset()
    yield
    guardian.resume()
    multi_source_graph.reset()
    graph_rag_engine.reset()


def test_tool_registry_registration_and_metadata():
    """SAF-01: Verifies all Phase 3 GraphRAG tools are registered with correct tiers, schemas, and previews."""
    # 1. graph_rag_query (Tier 0 Read-Only)
    tool_query = registry.get("graph_rag_query")
    assert tool_query is not None, "graph_rag_query not registered in ToolRegistry"
    assert tool_query.tier == 0
    assert tool_query.args_schema == GraphQueryArgs
    preview_query = tool_query.generate_preview({"query": "streaming voice engine"})
    assert "Query multi-source knowledge graph" in preview_query
    assert "Read-only" in preview_query

    # 2. graph_rag_get_stats (Tier 0 Read-Only)
    tool_stats = registry.get("graph_rag_get_stats")
    assert tool_stats is not None, "graph_rag_get_stats not registered in ToolRegistry"
    assert tool_stats.tier == 0
    assert tool_stats.args_schema == GraphStatsArgs
    preview_stats = tool_stats.generate_preview({})
    assert "Inspect multi-source knowledge graph topology" in preview_stats
    assert "Read-only" in preview_stats

    # 3. graph_rag_reindex_domain (Tier 1 Reversible Change)
    tool_reindex = registry.get("graph_rag_reindex_domain")
    assert tool_reindex is not None, "graph_rag_reindex_domain not registered in ToolRegistry"
    assert tool_reindex.tier == 1
    assert tool_reindex.args_schema == GraphReindexArgs
    preview_reindex = tool_reindex.generate_preview({"domain": "vault", "force_rebuild": True})
    assert "Reindex knowledge graph domain" in preview_reindex
    assert "Reversible change" in preview_reindex


def test_guardian_kill_switch_synchronous_sla():
    """SAF-02: Measure synchronous execution time of Guardian trigger across graph components (< 25ms SLA)."""
    # Populate a sample node
    test_node = GraphNode(
        node_id="code://phenom/test.py:SlaTestSymbol",
        domain="code",
        title="SlaTestSymbol",
        entity_type="code_symbol",
        summary="Test symbol for SLA measurement."
    )
    multi_source_graph.add_node(test_node)

    t0 = time.perf_counter()
    guardian.trigger("emergency_graph_killswitch_sla_test")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert elapsed_ms < 25.0, f"Guardian kill switch SLA breached: {elapsed_ms:.2f}ms >= 25.0ms"
    assert guardian.is_halted is True
    assert multi_source_graph.is_halted is True
    assert graph_rag_engine.is_halted is True


def test_graph_operations_blocked_while_halted():
    """Verify tool calls and operations are strictly blocked with PermissionError while halted."""
    guardian.trigger("emergency_graph_block_test")
    assert guardian.is_halted is True

    # 1. Tool calls must raise PermissionError
    with pytest.raises(PermissionError):
        graph_rag_tools.graph_rag_query(query="voice engine")

    with pytest.raises(PermissionError):
        graph_rag_tools.graph_rag_get_stats()

    with pytest.raises(PermissionError):
        graph_rag_tools.graph_rag_reindex_domain()

    # 2. Direct engine calls must raise PermissionError
    with pytest.raises(PermissionError):
        graph_rag_engine.query("voice engine")

    with pytest.raises(PermissionError):
        multi_source_graph.add_node(
            GraphNode(
                node_id="vault://test.md",
                domain="vault",
                title="test",
                entity_type="note",
                summary="test"
            )
        )


def test_clean_state_restoration_after_resume():
    """Verify clean recovery and normal operation after guardian.resume()."""
    guardian.trigger("test_halt_and_resume")
    assert guardian.is_halted is True
    assert multi_source_graph.is_halted is True

    guardian.resume()
    assert guardian.is_halted is False
    assert multi_source_graph.is_halted is False
    assert graph_rag_engine.is_halted is False

    # Tool calls succeed
    stats_res = graph_rag_tools.graph_rag_get_stats()
    assert stats_res["status"] == "success"
    assert stats_res["stats"]["is_halted"] is False
