"""Pydantic v2 schemas for Multi-Agent Task Auction Protocol & VRAM Governance.

Phase 48-01: SWARM-01, SWARM-02, SWARM-03.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Core specialized agent roles in the Phenom multi-agent swarm."""
    ARCHITECT = "architect"
    CODER = "coder"
    SECURITY_AUDITOR = "security_auditor"
    WEB_SCOUT = "web_scout"


class SwarmTaskStatus(str, Enum):
    """Lifecycle status of a swarm-scheduled task."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    HALTED = "halted"


class AgentProfile(BaseModel):
    """Specification of an agent role persona, capabilities, and affinities."""
    role: AgentRole
    display_name: str
    description: str
    system_prompt: str
    tool_affinities: Dict[str, float] = Field(
        default_factory=dict,
        description="Tool name to affinity weight mapping (0.0 to 1.0)",
    )
    capability_tags: List[str] = Field(default_factory=list)
    max_tokens: int = Field(default=4096)
    priority: int = Field(default=1, description="Higher priority resolves auction ties")


class TaskBid(BaseModel):
    """An agent's bid on a decomposed DAG node or mission task."""
    agent_role: AgentRole
    node_id: str
    fitness_score: float = Field(..., ge=0.0, le=1.0, description="Overall fitness match score")
    estimated_tokens: int = Field(default=500, ge=1)
    estimated_duration_sec: float = Field(default=2.0, ge=0.1)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    rationale: str = Field(default="")
    timestamp: float = Field(default_factory=time.time)


class AuctionResult(BaseModel):
    """The outcome of a task auction for a specific DAG node."""
    node_id: str
    winning_role: AgentRole
    winning_bid: TaskBid
    all_bids: List[TaskBid] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class VRAMMetrics(BaseModel):
    """Real-time GPU VRAM telemetry and governance metrics."""
    allocated_mb: float = Field(default=0.0, ge=0.0)
    reserved_mb: float = Field(default=0.0, ge=0.0)
    peak_mb: float = Field(default=0.0, ge=0.0)
    max_allowed_mb: float = Field(
        default=5632.0,
        description="Peak threshold for RTX 3050 8GB (default 5.5 GB = 5632 MB)",
    )
    is_safe: bool = Field(default=True)


class ScheduledTask(BaseModel):
    """A task managed by the time-sliced local swarm scheduler."""
    task_id: str
    node_id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    assigned_role: AgentRole
    status: SwarmTaskStatus = Field(default=SwarmTaskStatus.PENDING)
    result: Optional[Any] = None
    error: Optional[str] = None
    vram_usage_mb: float = Field(default=0.0)
    enqueued_at: float = Field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
