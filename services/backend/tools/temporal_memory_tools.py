"""Temporal Memory Tools Registration for Phenom (Milestone 49 Phase 1, MEM-01, MEM-02, MEM-03).

Exposes:
1. `record_temporal_episode` (Tier 1) - Records bi-temporal episodic memory and entities.
2. `query_associative_memory` (Tier 0) - Hybrid BM25 + dense vector + graph traversal recall.
3. `sync_obsidian_memory` (Tier 1) - Synchronizes episodic knowledge graph to vault/Memory/.
"""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.schemas.temporal_graph import (
    AssociativeQuery,
    EntityType,
    RelationType,
    TemporalEntity,
    TemporalEpisode,
    TemporalRelation,
)
from services.backend.memory.temporal_graph_engine import TemporalGraphEngine
from services.backend.memory.associative_retriever import AssociativeRetriever
from services.backend.memory.obsidian_mirror import ObsidianMirror

# Shared singleton instances
temporal_engine = TemporalGraphEngine()
associative_retriever = AssociativeRetriever(engine=temporal_engine)
obsidian_mirror = ObsidianMirror(engine=temporal_engine)


# ============================================================================
# 1. record_temporal_episode (Tier 1)
# ============================================================================

class RecordTemporalEpisodeArgs(BaseModel):
    title: str = Field(..., description="Title of the episodic milestone or event")
    summary: str = Field(default="", description="Narrative summary of the episode")
    episode_type: str = Field(default="GENERAL", description="Taxonomy type of the episode")
    valid_time: Optional[float] = Field(default=None, description="Epoch timestamp when the event occurred (T_v)")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Entities to record: [{'name': '...', 'type': 'CONCEPT', 'content': '...'}]")
    tags: List[str] = Field(default_factory=list, description="Search tags")


def record_temporal_episode_preview(args: Dict[str, Any]) -> str:
    title = args.get("title", "Untitled Episode")
    ent_count = len(args.get("entities", []))
    return f"Record episodic event '{title}' with {ent_count} linked entities into bi-temporal knowledge graph."


@registry.register(
    name="record_temporal_episode",
    tier=1,
    description="Records a bi-temporal episodic memory event and associated entities into persistent storage.",
    args_schema=RecordTemporalEpisodeArgs,
    preview_fn=record_temporal_episode_preview,
    can_remember_per_folder=False,
)
def handle_record_temporal_episode(
    title: str,
    summary: str = "",
    episode_type: str = "GENERAL",
    valid_time: Optional[float] = None,
    entities: Optional[List[Dict[str, Any]]] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    now = time.time()
    t_v = valid_time if valid_time is not None else now
    tags = tags or []
    entities_list = entities or []

    created_entity_ids = []
    for ent_data in entities_list:
        ename = ent_data.get("name", "Unnamed")
        etype_str = ent_data.get("type", "CONCEPT")
        try:
            etype = EntityType(etype_str)
        except Exception:
            etype = EntityType.CONCEPT

        ent_id = ent_data.get("id") or f"ent_{int(now * 1000)}_{len(created_entity_ids)}"
        entity = TemporalEntity(
            id=ent_id,
            name=ename,
            entity_type=etype,
            content=ent_data.get("content", ""),
            valid_from=t_v,
            recorded_at=now,
            tags=ent_data.get("tags", tags),
            metadata=ent_data.get("metadata", {}),
        )
        temporal_engine.upsert_entity(entity)
        created_entity_ids.append(ent_id)

    ep_id = f"ep_{int(now * 1000)}"
    episode = TemporalEpisode(
        id=ep_id,
        title=title,
        summary=summary,
        episode_type=episode_type,
        event_timestamp=t_v,
        recorded_at=now,
        entity_ids=created_entity_ids,
        tags=tags,
    )
    temporal_engine.record_episode(episode)

    return {
        "status": "success",
        "episode_id": ep_id,
        "valid_time": t_v,
        "recorded_at": now,
        "entity_ids": created_entity_ids,
    }


# ============================================================================
# 2. query_associative_memory (Tier 0)
# ============================================================================

class QueryAssociativeMemoryArgs(BaseModel):
    query: str = Field(..., description="Natural language search or keyword query")
    as_of_valid_time: Optional[float] = Field(default=None, description="Query historical real-world perspective (T_v)")
    as_of_transaction_time: Optional[float] = Field(default=None, description="Query historical system belief perspective (T_t)")
    top_k: int = Field(default=5, ge=1, le=50, description="Max results")
    include_neighbors: bool = Field(default=True, description="Whether to include 1-hop connected graph context")


def query_associative_memory_preview(args: Dict[str, Any]) -> str:
    query = args.get("query", "")
    return f"Query associative episodic memory for '{query[:40]}'."


@registry.register(
    name="query_associative_memory",
    tier=0,
    description="Recalls facts and entities using hybrid BM25, dense vector search, temporal decay, and graph proximity.",
    args_schema=QueryAssociativeMemoryArgs,
    preview_fn=query_associative_memory_preview,
    can_remember_per_folder=False,
)
def handle_query_associative_memory(
    query: str,
    as_of_valid_time: Optional[float] = None,
    as_of_transaction_time: Optional[float] = None,
    top_k: int = 5,
    include_neighbors: bool = True,
) -> Dict[str, Any]:
    q = AssociativeQuery(
        query=query,
        as_of_valid_time=as_of_valid_time,
        as_of_transaction_time=as_of_transaction_time,
        top_k=top_k,
        include_neighbors=include_neighbors,
    )
    results = associative_retriever.search(q)
    return {
        "query": query,
        "count": len(results),
        "results": [
            {
                "id": r.entity.id,
                "name": r.entity.name,
                "type": r.entity.entity_type.value,
                "content": r.entity.content,
                "composite_score": r.composite_score,
                "lexical_score": r.lexical_score,
                "semantic_score": r.semantic_score,
                "temporal_decay": r.temporal_decay_factor,
                "graph_proximity": r.graph_proximity_score,
                "related": r.related_entities,
            }
            for r in results
        ],
    }


# ============================================================================
# 3. sync_obsidian_memory (Tier 1)
# ============================================================================

class SyncObsidianMemoryArgs(BaseModel):
    entity_id: Optional[str] = Field(default=None, description="Specific entity ID to mirror, or None for all active entities")


def sync_obsidian_memory_preview(args: Dict[str, Any]) -> str:
    eid = args.get("entity_id")
    if eid:
        return f"Synchronize episodic entity '{eid}' into Obsidian vault at vault/Memory/."
    return "Synchronize all active episodic entities and relationships into Obsidian vault at vault/Memory/."


@registry.register(
    name="sync_obsidian_memory",
    tier=1,
    description="Synchronizes bi-temporal episodic graph entities and relationships into Markdown notes in vault/Memory/.",
    args_schema=SyncObsidianMemoryArgs,
    preview_fn=sync_obsidian_memory_preview,
    can_remember_per_folder=False,
)
def handle_sync_obsidian_memory(entity_id: Optional[str] = None) -> Dict[str, Any]:
    if entity_id:
        ent = temporal_engine.get_entity(entity_id)
        if not ent:
            return {"status": "error", "error": f"Entity '{entity_id}' not found."}
        event = obsidian_mirror.sync_entity(ent)
        return {
            "status": "success",
            "synced_count": 1,
            "events": [event.model_dump()],
            "stats": obsidian_mirror.get_mirror_stats(),
        }

    events = obsidian_mirror.sync_all_active_entities()
    return {
        "status": "success",
        "synced_count": len(events),
        "events": [e.model_dump() for e in events],
        "stats": obsidian_mirror.get_mirror_stats(),
    }
