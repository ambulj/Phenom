"""Associative Temporal Knowledge Graph Tools for Phenom (Milestone 31 Phase 3).

Registers 4 specialized tools in ToolRegistry:
1. record_graph_entity (Tier 1)
2. record_graph_relation (Tier 1)
3. record_episodic_event (Tier 1)
4. query_associative_temporal_graph (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.memory.temporal_knowledge_graph import (
    temporal_knowledge_graph,
    EntityType,
    RelationType,
    EpisodeType,
)


# ==========================================
# 1. Record Graph Entity (Tier 1)
# ==========================================

class RecordGraphEntityArgs(BaseModel):
    id: str = Field(..., description="Unique entity ID (e.g. 'ent-auth-service').")
    name: str = Field(..., description="Entity name or label.")
    entity_type: str = Field(
        ...,
        description="Entity type: 'CONCEPT', 'FILE', 'PROJECT', 'GOAL', 'DECISION', 'SESSION'.",
    )
    properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Metadata dictionary for the entity."
    )


def preview_record_graph_entity(args: Dict[str, Any]) -> str:
    name = args.get("name", "entity")
    e_type = args.get("entity_type", "CONCEPT")
    return f"Insert or update knowledge graph entity [{name}] of type '{e_type}'"


@registry.register(
    name="record_graph_entity",
    tier=1,
    description="Inserts or updates a node in the encrypted associative knowledge graph (Tier 1 action).",
    args_schema=RecordGraphEntityArgs,
    preview_fn=preview_record_graph_entity,
    can_remember_per_folder=False,
)
def handle_record_graph_entity(
    id: str,
    name: str,
    entity_type: str,
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    e_type_enum = EntityType(entity_type.upper())
    entity = temporal_knowledge_graph.record_entity(
        id=id,
        name=name,
        entity_type=e_type_enum,
        properties=properties,
    )
    return entity.model_dump()


# ==========================================
# 2. Record Graph Relation (Tier 1)
# ==========================================

class RecordGraphRelationArgs(BaseModel):
    id: str = Field(..., description="Unique relation edge ID.")
    source_id: str = Field(..., description="Source entity ID.")
    target_id: str = Field(..., description="Target entity ID.")
    relation_type: str = Field(
        ...,
        description="Relation type: 'DEPENDS_ON', 'IMPLEMENTS', 'RESOLVES', 'MODIFIES', 'DERIVED_FROM', 'RELATED_TO'.",
    )
    weight: Optional[float] = Field(1.0, description="Edge weight / associative strength (0.0 to 1.0).")


def preview_record_graph_relation(args: Dict[str, Any]) -> str:
    src = args.get("source_id", "src")
    tgt = args.get("target_id", "tgt")
    rel = args.get("relation_type", "RELATED_TO")
    return f"Link knowledge graph entities: ({src}) --[{rel}]--> ({tgt})"


@registry.register(
    name="record_graph_relation",
    tier=1,
    description="Connects two entities with a directed weighted edge in the knowledge graph (Tier 1 action).",
    args_schema=RecordGraphRelationArgs,
    preview_fn=preview_record_graph_relation,
    can_remember_per_folder=False,
)
def handle_record_graph_relation(
    id: str,
    source_id: str,
    target_id: str,
    relation_type: str,
    weight: float = 1.0,
) -> Dict[str, Any]:
    rel_enum = RelationType(relation_type.upper())
    relation = temporal_knowledge_graph.record_relation(
        id=id,
        source_id=source_id,
        target_id=target_id,
        relation_type=rel_enum,
        weight=weight,
    )
    return relation.model_dump()


# ==========================================
# 3. Record Episodic Event (Tier 1)
# ==========================================

class RecordEpisodicEventArgs(BaseModel):
    id: str = Field(..., description="Unique episode event ID.")
    session_id: str = Field(..., description="Active session or sprint ID.")
    episode_type: str = Field(
        ...,
        description="Episode modality: 'TERMINAL_RUN', 'GIT_COMMIT', 'OBSIDIAN_NOTE', 'MILESTONE_DECISION'.",
    )
    summary: str = Field(..., description="Concise summary of the episodic milestone.")
    entity_ids: Optional[List[str]] = Field(
        default_factory=list, description="IDs of graph entities linked to this episode."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Execution or note metadata (e.g. exit_code, commit_hash, note_path)."
    )


def preview_record_episodic_event(args: Dict[str, Any]) -> str:
    ep_type = args.get("episode_type", "TERMINAL_RUN")
    summary = args.get("summary", "")
    preview_txt = (summary[:60] + "...") if len(summary) > 60 else summary
    return f"Record episodic event [{ep_type}]: \"{preview_txt}\""


@registry.register(
    name="record_episodic_event",
    tier=1,
    description="Indexes an episodic milestone (terminal run, Git commit, Obsidian daily note) in episodic memory (Tier 1 action).",
    args_schema=RecordEpisodicEventArgs,
    preview_fn=preview_record_episodic_event,
    can_remember_per_folder=False,
)
def handle_record_episodic_event(
    id: str,
    session_id: str,
    episode_type: str,
    summary: str,
    entity_ids: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ep_enum = EpisodeType(episode_type.upper())
    episode = temporal_knowledge_graph.record_episode(
        id=id,
        session_id=session_id,
        episode_type=ep_enum,
        summary=summary,
        entity_ids=entity_ids,
        metadata=metadata,
    )
    return episode.model_dump()


# ==========================================
# 4. Query Associative Temporal Graph (Tier 0)
# ==========================================

class QueryAssociativeTemporalGraphArgs(BaseModel):
    query: str = Field(..., description="Search query or keyword phrase.")
    max_hops: Optional[int] = Field(2, description="Maximum traversal depth (default 2 hops).")


def preview_query_associative_temporal_graph(args: Dict[str, Any]) -> str:
    q = args.get("query", "")
    hops = args.get("max_hops", 2)
    return f"Perform {hops}-hop associative temporal graph query for \"{q}\""


@registry.register(
    name="query_associative_temporal_graph",
    tier=0,
    description="Traverses associative graph from seed concepts up to k hops, applying exponential decay scoring (Tier 0 read-only).",
    args_schema=QueryAssociativeTemporalGraphArgs,
    preview_fn=preview_query_associative_temporal_graph,
    can_remember_per_folder=False,
)
def handle_query_associative_temporal_graph(
    query: str,
    max_hops: int = 2,
) -> Dict[str, Any]:
    result = temporal_knowledge_graph.query_associative_subgraph(
        query=query,
        max_hops=max_hops,
    )
    return result.model_dump()
