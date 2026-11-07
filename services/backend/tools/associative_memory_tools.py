"""
Phenom Associative Long-Term Memory Tools (SAF-01 & SAF-02).
Registers Milestone 19 Phase 4 tools in ToolRegistry:
1. store_associative_memory (Tier 1)
2. recall_associative_memory (Tier 0)
3. delete_associative_memory (Tier 1 - Rule 7 recycle bin)
4. get_associative_memory_stats (Tier 0)
All tools enforce strict Pydantic argument schemas, preview generators, and Guardian SLA guarantees.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.memory.associative_memory_engine import associative_memory_engine
from services.backend.memory.sqlite_vec_store import sqlite_vec_store


class StoreAssociativeMemoryArgs(BaseModel):
    content: str = Field(..., description="Fact, preference, or concept to remember permanently")
    tags: Optional[List[str]] = Field(default=None, description="Optional categories or tags")


class RecallAssociativeMemoryArgs(BaseModel):
    query: str = Field(..., description="Search query or contextual statement to retrieve memories for")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of relevant memories to return")
    min_score: float = Field(default=0.20, ge=0.0, le=1.0, description="Minimum cosine similarity threshold")


class DeleteAssociativeMemoryArgs(BaseModel):
    memory_id: str = Field(..., description="Unique memory ID to soft-delete to the recycle bin (Rule 7)")


class GetAssociativeMemoryStatsArgs(BaseModel):
    pass


@registry.register(
    name="store_associative_memory",
    tier=1,
    description="Stores an explicit fact or user preference permanently in encrypted associative memory.",
    args_schema=StoreAssociativeMemoryArgs,
    preview_fn=lambda a: f"Store permanent memory: '{(getattr(a, 'content', '') if not isinstance(a, dict) else a.get('content', ''))[:40]}...'"
)
async def store_associative_memory(
    content: str,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Stores explicit user memory."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    return associative_memory_engine.store_explicit_memory(content=content, tags=tags)


@registry.register(
    name="recall_associative_memory",
    tier=0,
    description="Executes sub-10ms semantic similarity recall over associative long-term memory. Read-only.",
    args_schema=RecallAssociativeMemoryArgs,
    preview_fn=lambda a: f"Recall memories for query '{(getattr(a, 'query', '') if not isinstance(a, dict) else a.get('query', ''))[:30]}'"
)
async def recall_associative_memory(
    query: str,
    top_k: int = 5,
    min_score: float = 0.20
) -> Dict[str, Any]:
    """Recalls memories matching semantic query."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    return associative_memory_engine.recall(query=query, top_k=top_k, min_score=min_score)


@registry.register(
    name="delete_associative_memory",
    tier=1,
    description="Soft-deletes a memory entry to the recycle bin (Rule 7). Never permanently purges without approval.",
    args_schema=DeleteAssociativeMemoryArgs,
    preview_fn=lambda a: f"Recycle memory entry '{(getattr(a, 'memory_id', '') if not isinstance(a, dict) else a.get('memory_id', ''))}'"
)
async def delete_associative_memory(memory_id: str) -> Dict[str, Any]:
    """Recycles memory entry."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    success = associative_memory_engine.delete_memory(memory_id)
    return {
        "status": "recycled" if success else "not_found",
        "memory_id": memory_id
    }


@registry.register(
    name="get_associative_memory_stats",
    tier=0,
    description="Returns vector database index statistics, active memory count, and encryption status. Read-only.",
    args_schema=GetAssociativeMemoryStatsArgs,
    preview_fn=lambda a: "Inspect associative memory vector store statistics (Read-only)"
)
async def get_associative_memory_stats() -> Dict[str, Any]:
    """Returns vector store stats."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    return sqlite_vec_store.get_stats()
