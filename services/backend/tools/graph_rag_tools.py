"""
Phenom Multi-Source Knowledge Graph (GraphRAG) Tools
Provides tool endpoints for querying the cross-domain knowledge graph,
inspecting graph topology metrics, and reindexing domains.

Strictly respects SAFETY.md:
- graph_rag_query (Tier 0): Read-only hybrid retrieval.
- graph_rag_get_stats (Tier 0): Read-only topology statistics.
- graph_rag_reindex_domain (Tier 1): Reversible domain reindexing requiring user approval.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from services.backend.memory.graph_rag import graph_rag_engine
from services.backend.memory.multi_source_graph import multi_source_graph
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.graph_rag import (
    GraphQueryArgs,
    GraphQueryResult,
    GraphReindexArgs,
    GraphStats,
    GraphStatsArgs,
)

logger = logging.getLogger("phenom.graph_rag_tools")


@registry.register(
    name="graph_rag_query",
    tier=0,
    description="Executes hybrid GraphRAG retrieval (BM25 lexical + dense vector semantic + 1/2-hop relational expansion) across personal knowledge graph. Read-only.",
    args_schema=GraphQueryArgs,
    preview_fn=lambda a: f"Query multi-source knowledge graph for '{a.get('query')}' (Read-only)"
)
def graph_rag_query(
    query: str,
    hops: int = 1,
    domain_filter: Optional[str] = None,
    top_k: int = 5
) -> Dict[str, Any]:
    """Queries multi-source knowledge graph using hybrid GraphRAG."""
    if multi_source_graph.is_halted or getattr(guardian, "is_halted", False):
        raise PermissionError("Knowledge graph operations are halted by Guardian.")

    result: GraphQueryResult = graph_rag_engine.query(
        query=query,
        hops=hops,
        domain_filter=domain_filter,
        top_k=top_k
    )
    return {
        "status": "success",
        "result": result.model_dump()
    }


@registry.register(
    name="graph_rag_get_stats",
    tier=0,
    description="Inspects multi-source knowledge graph topology, node counts, orphan nodes, and concept hubs. Read-only.",
    args_schema=GraphStatsArgs,
    preview_fn=lambda a: "Inspect multi-source knowledge graph topology and domain metrics (Read-only)"
)
def graph_rag_get_stats() -> Dict[str, Any]:
    """Returns knowledge graph topology metrics and domain breakdown."""
    if multi_source_graph.is_halted or getattr(guardian, "is_halted", False):
        raise PermissionError("Knowledge graph operations are halted by Guardian.")

    stats: GraphStats = multi_source_graph.get_stats()
    return {
        "status": "success",
        "stats": stats.model_dump()
    }


@registry.register(
    name="graph_rag_reindex_domain",
    tier=1,
    description="Reindexes personal knowledge graph for specified domain ('vault', 'code', 'doc', 'workspace', 'all'). Reversible change.",
    args_schema=GraphReindexArgs,
    preview_fn=lambda a: f"Reindex knowledge graph domain '{a.get('domain') or 'all'}' (Reversible change)"
)
def graph_rag_reindex_domain(
    domain: Optional[str] = None,
    force_rebuild: bool = False
) -> Dict[str, Any]:
    """Reindexes specified domain or all domains across the knowledge graph."""
    if multi_source_graph.is_halted or getattr(guardian, "is_halted", False):
        raise PermissionError("Knowledge graph operations are halted by Guardian.")

    t0 = time.perf_counter()
    target_dom = (domain or "all").lower()

    if force_rebuild:
        if target_dom == "all":
            multi_source_graph.clear()
        else:
            multi_source_graph.clear_domain(target_dom)

    ingested_nodes = 0
    if target_dom in ("vault", "all"):
        ingested_nodes += multi_source_graph.index_vault()

    if target_dom in ("code", "all"):
        ingested_nodes += multi_source_graph.index_code_repo()

    if target_dom in ("workspace", "all"):
        ingested_nodes += multi_source_graph.index_workspace()

    # Synthesize cross domain links
    synthesized_edges = multi_source_graph.synthesize_cross_domain_links()

    # Refresh indices
    graph_rag_engine.refresh_indices()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    current_stats = multi_source_graph.get_stats()

    return {
        "status": "success",
        "domain": target_dom,
        "force_rebuild": force_rebuild,
        "nodes_ingested": ingested_nodes,
        "synthesized_edges": synthesized_edges,
        "elapsed_ms": round(elapsed_ms, 2),
        "total_nodes": current_stats.total_nodes,
        "total_edges": current_stats.total_edges
    }
