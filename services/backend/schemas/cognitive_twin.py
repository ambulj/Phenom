from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class EpisodicNodeType(str, Enum):
    ACTIVITY = "activity"
    TOPIC = "topic"
    TOOL_USAGE = "tool_usage"
    PROJECT = "project"
    HABIT = "habit"
    CONTEXT = "context"


class EpisodicNode(BaseModel):
    node_id: str
    node_type: EpisodicNodeType
    label: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    access_count: int = 1
    last_observed: float
    affinity_weight: float = Field(1.0, ge=0.0, le=100.0)


class EpisodicEdge(BaseModel):
    source_id: str
    target_id: str
    relationship: str
    weight: float = Field(1.0, ge=0.0, le=100.0)
    created_at: float


class ContextualAnticipation(BaseModel):
    anticipation_id: str
    suggested_action: str
    target_tool: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning_path: str
    timestamp: float


class CognitiveTwinState(BaseModel):
    total_nodes: int
    total_edges: int
    active_context_nodes: List[str] = []
    anticipations: List[ContextualAnticipation] = []
    is_locked: bool = False


class CognitiveTwinGetStatusArgs(BaseModel):
    include_anticipations: bool = True


class CognitiveTwinQueryGraphArgs(BaseModel):
    node_type: Optional[EpisodicNodeType] = None
    label_query: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)


class CognitiveTwinIngestEpisodeArgs(BaseModel):
    activity_label: str = Field(..., description="Description or label of the episodic activity")
    node_type: EpisodicNodeType = Field(EpisodicNodeType.ACTIVITY, description="Classification of the node")
    related_labels: List[str] = Field(default_factory=list, description="Labels of related entities to link")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Metadata key-values for the episode")


class CognitiveTwinPruneArgs(BaseModel):
    min_affinity_weight: float = Field(0.10, ge=0.0, le=1.0, description="Minimum affinity threshold below which nodes are pruned")
