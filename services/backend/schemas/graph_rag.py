"""
Pydantic Schemas for Phenom Autonomous Multi-Source Personal Knowledge Graph & GraphRAG
Strict typing for 4-domain nodes, typed relational edges, hybrid retrieval results,
topology statistics, and ToolRegistry invocation arguments.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GraphEdge(BaseModel):
    """
    Directed typed edge connecting two knowledge graph nodes.
    Supports relations: references, implements, discussed_in, authored_by, documents, calls, contains.
    """
    source_id: str = Field(..., description="Deterministic URI of source node")
    target_id: str = Field(..., description="Deterministic URI of target node")
    relation: str = Field(
        default="references",
        description="Edge semantic type (e.g. references, implements, discussed_in, authored_by, documents, calls, contains)"
    )
    weight: float = Field(default=1.0, ge=0.0, description="Edge strength / confidence weight")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary edge metadata")

    def __hash__(self) -> int:
        return hash((self.source_id, self.target_id, self.relation))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, GraphEdge):
            return False
        return (
            self.source_id == other.source_id
            and self.target_id == other.target_id
            and self.relation == other.relation
        )


class GraphNode(BaseModel):
    """
    Universal knowledge node identified by deterministic URI.
    Domains: vault, code, doc, meeting, email.
    """
    node_id: str = Field(..., description="Deterministic URI (e.g. vault://..., code://...)")
    domain: str = Field(..., description="Domain category: 'vault', 'code', 'doc', 'meeting', 'email'")
    title: str = Field(..., description="Human-readable title or symbol name")
    entity_type: str = Field(
        ...,
        description="Entity type: note, code_symbol, git_commit, pdf_section, meeting_agenda, email_thread"
    )
    summary: str = Field(default="", description="Sanitized summary or text snippet")
    tags: List[str] = Field(default_factory=list, description="Categorical tags or keywords")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Domain-specific metadata")
    edges: List[GraphEdge] = Field(default_factory=list, description="Associated outgoing edges")


class GraphQueryResult(BaseModel):
    """
    Result of a Hybrid GraphRAG query combining lexical, vector semantic,
    and relational graph traversal across multiple domains.
    """
    query: str = Field(..., description="Original natural language query")
    seed_nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Top-K seed nodes retrieved via hybrid search")
    expanded_nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Neighbor nodes reached via N-hop relational expansion")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="Traversed edges connecting seeds and expanded nodes")
    context_synthesis: str = Field(default="", description="Unified synthesized prompt context with explicit URI citations")
    citations: List[str] = Field(default_factory=list, description="Explicit deterministic URI citations referenced in synthesis")
    traversal_depth: int = Field(default=1, description="Graph traversal hop depth (1 or 2)")


class GraphStats(BaseModel):
    """
    Knowledge graph topological statistics and status.
    """
    total_nodes: int = Field(default=0, description="Total indexed nodes in the knowledge graph")
    total_edges: int = Field(default=0, description="Total indexed relational edges")
    domain_breakdown: Dict[str, int] = Field(default_factory=dict, description="Node count per domain")
    orphan_count: int = Field(default=0, description="Number of disconnected nodes with zero in/out edges")
    hub_count: int = Field(default=0, description="Number of high-degree concept hub nodes")
    is_indexing: bool = Field(default=False, description="Whether active background indexing is running")
    is_halted: bool = Field(default=False, description="Whether knowledge graph is halted by Guardian")


class GraphQueryArgs(BaseModel):
    """Arguments for graph_rag_query tool."""
    query: str = Field(..., description="Natural language search query across personal knowledge graph")
    hops: int = Field(default=1, ge=1, le=2, description="Relational graph traversal depth (1 or 2 hops)")
    domain_filter: Optional[str] = Field(
        default=None,
        description="Optional domain filter ('vault', 'code', 'doc', 'meeting', 'email')"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of top seed nodes to retrieve")


class GraphStatsArgs(BaseModel):
    """Arguments for graph_rag_get_stats tool."""
    pass


class GraphReindexArgs(BaseModel):
    """Arguments for graph_rag_reindex_domain tool."""
    domain: Optional[str] = Field(
        default=None,
        description="Domain to reindex ('vault', 'code', 'doc', 'workspace', 'all')"
    )
    force_rebuild: bool = Field(
        default=False,
        description="Whether to clear existing nodes for domain and reindex from scratch"
    )
