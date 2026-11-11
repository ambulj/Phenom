"""Safety-Wrapped Memory Consolidation Tools.

Registers tools with ToolRegistry for episodic memory consolidation,
hierarchical abstraction queries, and decay-based soft-pruning (Phase 26-01 MEM-06 / ABS-01).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.consolidation.memory_consolidator import memory_consolidator
from services.backend.consolidation.hierarchical_abstractor import hierarchical_abstractor


# ==========================================
# 1. Consolidate Episodic Memory (Tier 0)
# ==========================================

class ConsolidateEpisodicMemoryArgs(BaseModel):
    pass


def consolidate_episodic_memory_preview(args: Dict[str, Any]) -> str:
    return "Execute memory consolidation pass across recent episodic session traces."


@registry.register(
    name="consolidate_episodic_memory",
    tier=0,
    description="Compresses unconsolidated episodic interaction traces into structured semantic knowledge nodes.",
    args_schema=ConsolidateEpisodicMemoryArgs,
    preview_fn=consolidate_episodic_memory_preview,
    can_remember_per_folder=False,
)
def handle_consolidate_episodic_memory() -> Dict[str, Any]:
    nodes = memory_consolidator.consolidate()
    return {
        "consolidated_node_count": len(nodes),
        "nodes": [n.model_dump() for n in nodes],
    }


# ==========================================
# 2. Query Hierarchical Memory Graph (Tier 0)
# ==========================================

class QueryHierarchicalMemoryGraphArgs(BaseModel):
    query: str = Field(..., description="Semantic query to search across abstraction levels")
    min_level: int = Field(1, description="Minimum abstraction level (1=Micro, 2=Macro, 3=Core)")


def query_hierarchical_memory_graph_preview(args: Dict[str, Any]) -> str:
    query = args.get("query", "unspecified query")
    lvl = args.get("min_level", 1)
    return f"Query hierarchical memory graph for '{query}' (min abstraction level: {lvl})."


@registry.register(
    name="query_hierarchical_memory_graph",
    tier=0,
    description="Searches the hierarchical memory graph across micro-heuristics, macro-strategies, and core identity.",
    args_schema=QueryHierarchicalMemoryGraphArgs,
    preview_fn=query_hierarchical_memory_graph_preview,
    can_remember_per_folder=False,
)
def handle_query_hierarchical_memory_graph(query: str, min_level: int = 1) -> Dict[str, Any]:
    matched = hierarchical_abstractor.query_graph(query=query, min_level=min_level)
    return {
        "query": query,
        "match_count": len(matched),
        "results": [m.model_dump() for m in matched],
    }


# ==========================================
# 3. Prune Decayed Memory Traces (Tier 1)
# ==========================================

class PruneDecayedMemoryTracesArgs(BaseModel):
    decay_threshold: float = Field(0.20, description="Importance decay score threshold below which traces are soft-pruned (0.0 to 1.0)")


def prune_decayed_memory_traces_preview(args: Dict[str, Any]) -> str:
    thresh = args.get("decay_threshold", 0.20)
    return f"Soft-prune decayed episodic memory traces below importance threshold {thresh}."


@registry.register(
    name="prune_decayed_memory_traces",
    tier=1,
    description="Soft-prunes low-importance, decayed memory traces to cold storage without permanent data loss (Rule 7).",
    args_schema=PruneDecayedMemoryTracesArgs,
    preview_fn=prune_decayed_memory_traces_preview,
    can_remember_per_folder=False,
)
def handle_prune_decayed_memory_traces(decay_threshold: float = 0.20) -> Dict[str, Any]:
    pruned_ids = memory_consolidator.soft_prune_decayed(decay_threshold=decay_threshold)
    return {
        "pruned_count": len(pruned_ids),
        "pruned_trace_ids": pruned_ids,
        "status": "SOFT_PRUNED_TO_COLD_STORAGE",
    }
