"""Pydantic schemas for Bi-Temporal Episodic Knowledge Matrix (Milestone 49 Phase 1).

Distinguishes:
- Valid Time (T_v): when the event/fact actually occurred or was true in reality.
- Transaction Time (T_t): when the event/fact was recorded or asserted into Phenom.
"""

from __future__ import annotations

from enum import Enum
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    CONCEPT = "CONCEPT"
    FILE = "FILE"
    PROJECT = "PROJECT"
    GOAL = "GOAL"
    DECISION = "DECISION"
    SESSION = "SESSION"
    EVENT = "EVENT"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    CODE_DIFF = "CODE_DIFF"


class RelationType(str, Enum):
    DEPENDS_ON = "DEPENDS_ON"
    IMPLEMENTS = "IMPLEMENTS"
    RESOLVES = "RESOLVES"
    MODIFIES = "MODIFIES"
    DERIVED_FROM = "DERIVED_FROM"
    RELATED_TO = "RELATED_TO"
    CAUSED_BY = "CAUSED_BY"
    SUPERSEDES = "SUPERSEDES"


class TemporalInterval(BaseModel):
    """Bi-temporal interval coordinates."""
    valid_from: float = Field(default_factory=time.time, description="Epoch seconds when fact became true in reality (T_v start)")
    valid_until: Optional[float] = Field(default=None, description="Epoch seconds when fact ceased to be true (T_v end)")
    recorded_at: float = Field(default_factory=time.time, description="Epoch seconds when recorded into system (T_t start)")
    superseded_at: Optional[float] = Field(default=None, description="Epoch seconds when assertion was replaced/invalidated (T_t end)")

    @property
    def is_active(self) -> bool:
        """True if the transaction assertion has not been superseded."""
        return self.superseded_at is None


class TemporalEntity(BaseModel):
    """A bi-temporal knowledge graph entity."""
    id: str = Field(description="Unique entity identifier (slug or uuid)")
    name: str = Field(description="Human-readable title or label")
    entity_type: EntityType = Field(default=EntityType.CONCEPT, description="Entity category")
    content: str = Field(default="", description="Detailed textual description or body")
    valid_from: float = Field(default_factory=time.time, description="Valid time (T_v start)")
    valid_until: Optional[float] = Field(default=None, description="Valid time (T_v end)")
    recorded_at: float = Field(default_factory=time.time, description="Transaction time (T_t start)")
    superseded_at: Optional[float] = Field(default=None, description="Transaction time (T_t end)")
    tags: List[str] = Field(default_factory=list, description="Categorical tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom contextual attributes")

    @property
    def is_active(self) -> bool:
        return self.superseded_at is None

    def is_valid_at(self, timestamp: float) -> bool:
        """Checks if entity was true in the real world at timestamp (T_v)."""
        if timestamp < self.valid_from:
            return False
        if self.valid_until is not None and timestamp > self.valid_until:
            return False
        return True

    def was_recorded_by(self, timestamp: float) -> bool:
        """Checks if Phenom knew about this entity as of transaction time timestamp (T_t)."""
        if timestamp < self.recorded_at:
            return False
        if self.superseded_at is not None and timestamp >= self.superseded_at:
            return False
        return True


class TemporalRelation(BaseModel):
    """A bi-temporal directed relationship between two entities."""
    id: str = Field(description="Unique relationship identifier")
    source_id: str = Field(description="Origin entity ID")
    target_id: str = Field(description="Destination entity ID")
    relation_type: RelationType = Field(default=RelationType.RELATED_TO, description="Semantic edge type")
    weight: float = Field(default=1.0, ge=0.0, description="Relationship strength/confidence")
    valid_from: float = Field(default_factory=time.time, description="Valid time (T_v start)")
    valid_until: Optional[float] = Field(default=None, description="Valid time (T_v end)")
    recorded_at: float = Field(default_factory=time.time, description="Transaction time (T_t start)")
    superseded_at: Optional[float] = Field(default=None, description="Transaction time (T_t end)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom relationship context")

    @property
    def is_active(self) -> bool:
        return self.superseded_at is None

    def is_valid_at(self, timestamp: float) -> bool:
        if timestamp < self.valid_from:
            return False
        if self.valid_until is not None and timestamp > self.valid_until:
            return False
        return True

    def was_recorded_by(self, timestamp: float) -> bool:
        if timestamp < self.recorded_at:
            return False
        if self.superseded_at is not None and timestamp >= self.superseded_at:
            return False
        return True


class TemporalEpisode(BaseModel):
    """A discrete episodic event grouping entities, actions, and decisions."""
    id: str = Field(description="Unique episode identifier")
    title: str = Field(description="Episode summary title")
    summary: str = Field(default="", description="Narrative recap of the episode")
    episode_type: str = Field(default="GENERAL", description="Episode taxonomy (e.g. MISSION, RESEARCH, CODING, CHOREOGRAPHY)")
    event_timestamp: float = Field(default_factory=time.time, description="When the event occurred (T_v)")
    recorded_at: float = Field(default_factory=time.time, description="When Phenom ingested the episode (T_t)")
    entity_ids: List[str] = Field(default_factory=list, description="IDs of entities involved in this episode")
    tags: List[str] = Field(default_factory=list, description="Categorical tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual telemetry")


class AssociativeQuery(BaseModel):
    """Query parameters for hybrid lexical, vector, and temporal-decay search."""
    query: str = Field(description="Search keywords or natural language prompt")
    as_of_valid_time: Optional[float] = Field(default=None, description="Historical query timestamp for T_v")
    as_of_transaction_time: Optional[float] = Field(default=None, description="Historical system perspective timestamp for T_t")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum number of ranked results")
    entity_types: Optional[List[EntityType]] = Field(default=None, description="Filter by entity types")
    include_neighbors: bool = Field(default=True, description="Whether to include 1-hop graph neighbors")
    max_hops: int = Field(default=2, ge=1, le=4, description="Maximum graph traversal depth")
    half_life_days: float = Field(default=14.0, gt=0.0, description="Temporal decay half-life in days")


class MemorySearchResult(BaseModel):
    """Ranked memory search match with explainable scoring breakdown."""
    entity: TemporalEntity = Field(description="Matched knowledge entity")
    composite_score: float = Field(description="Combined relevance score [0, 1]")
    lexical_score: float = Field(default=0.0, description="BM25 keyword match score")
    semantic_score: float = Field(default=0.0, description="Dense embedding cosine similarity")
    temporal_decay_factor: float = Field(default=1.0, description="Time-decay multiplier based on valid time")
    graph_proximity_score: float = Field(default=0.0, description="Network topology relevance score")
    related_entities: List[Dict[str, Any]] = Field(default_factory=list, description="1-hop and 2-hop connected graph context")


class ObsidianMirrorEvent(BaseModel):
    """Status record of a Markdown file synchronization event in vault/Memory/."""
    entity_id: str = Field(description="Synchronized entity ID")
    file_path: str = Field(description="Path to Markdown file in Obsidian vault")
    action: str = Field(description="SYNCED, CREATED, or SUPERSEDED")
    timestamp: float = Field(default_factory=time.time, description="Sync timestamp")
    checksum: str = Field(default="", description="Content SHA-256 checksum")
