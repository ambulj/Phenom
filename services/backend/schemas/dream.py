"""
Sovereign Neuro-Symbolic Sleep & Dream Engine Schemas (DRM-01, SAF-01, SAF-02).
Defines Pydantic v2 models for:
- Dream consolidation phase transitions and cycle reports
- Episodic task trace replays and generalized conceptual schemas
- Memory graph pruning metrics and safety tool argument schemas
"""

import time
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class DreamPhaseStatus(str, Enum):
    IDLE = "IDLE"
    INGESTING_EPISODES = "INGESTING_EPISODES"
    REPLAYING_TRACES = "REPLAYING_TRACES"
    COMPACTING_GRAPH = "COMPACTING_GRAPH"
    ABSTRACTING_SCHEMAS = "ABSTRACTING_SCHEMAS"
    COMPLETED = "COMPLETED"
    HALTED = "HALTED"


class EpisodicTrace(BaseModel):
    """Execution trace of a past user action, tool run, or goal planning step."""
    model_config = ConfigDict(use_enum_values=True)

    trace_id: str = Field(..., description="Unique trace identifier")
    source: str = Field(default="action_log", description="Origin: action_log, tot_goal, chat_session")
    timestamp: float = Field(default_factory=time.time, description="Trace creation epoch timestamp")
    action_type: str = Field(..., description="Action classification or tool category")
    tool_name: Optional[str] = Field(default=None, description="Tool invoked if applicable")
    status: str = Field(default="success", description="Outcome status: success, failed, pruned")
    summary: str = Field(..., description="Concise text description of what transpired")
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters or metrics")


class GeneralizedSchema(BaseModel):
    """High-level cognitive heuristic or domain schema abstracted from replayed episodes."""
    model_config = ConfigDict(use_enum_values=True)

    schema_id: str = Field(..., description="Unique schema rule identifier")
    domain: str = Field(..., description="Problem domain (e.g., coding, system, files, research)")
    heuristic_rule: str = Field(..., description="Abstracted pattern or rule of thumb")
    confidence: float = Field(default=1.0, description="Heuristic reliability score (0.0 to 1.0)")
    supporting_trace_ids: List[str] = Field(default_factory=list, description="IDs of traces supporting this rule")
    created_at: float = Field(default_factory=time.time, description="Creation epoch timestamp")


class ConsolidationReport(BaseModel):
    """Summary metrics of an executed dream memory consolidation cycle."""
    model_config = ConfigDict(use_enum_values=True)

    cycle_id: str = Field(..., description="Unique cycle identifier")
    episodes_replayed: int = Field(default=0, description="Total execution traces analyzed")
    schemas_formed: int = Field(default=0, description="New generalized cognitive schemas synthesized")
    edges_pruned: int = Field(default=0, description="Stale or dangling associative graph edges purged")
    duplicate_nodes_merged: int = Field(default=0, description="Redundant entity nodes consolidated")
    duration_ms: float = Field(default=0.0, description="Consolidation duration in milliseconds")
    completed_at: float = Field(default_factory=time.time, description="Cycle completion timestamp")


class DreamEngineStatus(BaseModel):
    """Real-time telemetry of the Dream Consolidation Engine."""
    model_config = ConfigDict(use_enum_values=True)

    is_running: bool = Field(default=False, description="True if a dream cycle is actively in progress")
    phase: DreamPhaseStatus = Field(default=DreamPhaseStatus.IDLE, description="Current dream cycle phase")
    last_cycle_at: Optional[float] = Field(default=None, description="Timestamp of the most recent dream cycle")
    total_cycles_completed: int = Field(default=0, description="Cumulative count of completed dream cycles")
    total_schemas_formed: int = Field(default=0, description="Total generalized schemas active in memory")
    is_halted: bool = Field(default=False, description="True if halted by Guardian kill switch")
    latest_report: Optional[ConsolidationReport] = Field(default=None, description="Report from most recent cycle")


# ==========================================
# Tool Argument Schemas (SAF-01)
# ==========================================

class DreamTriggerCycleArgs(BaseModel):
    force: bool = Field(default=False, description="Whether to trigger dream cycle immediately bypassing idle checks")
    max_episodes: int = Field(default=50, ge=1, le=200, description="Maximum number of historical traces to analyze")


class DreamGetStatusArgs(BaseModel):
    include_report: bool = Field(default=True, description="Whether to include full report of last consolidation cycle")


class DreamPruneStaleArgs(BaseModel):
    decay_days_threshold: int = Field(default=14, ge=1, description="Age in days beyond which unreferenced links decay")
    dry_run: bool = Field(default=False, description="If True, returns count without applying deletions")
