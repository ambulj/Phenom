"""
Tree-of-Thought (ToT) Metacognitive Goal Engine & Self-Healing DAG Schemas (PLN-01, SAF-01).
Pydantic v2 data models for DAG topology, nodes, branches, checkpoints,
metacognitive reflection logs, and tool governance arguments.
"""

from enum import Enum
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class NodeStatus(str, Enum):
    """Execution status lifecycle for individual DAG nodes."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PRUNED = "PRUNED"
    ROLLED_BACK = "ROLLED_BACK"
    SKIPPED = "SKIPPED"


class BranchType(str, Enum):
    """Categorization for branching pathways in Tree-of-Thought DAGs."""
    PRIMARY = "PRIMARY"
    CONTINGENCY = "CONTINGENCY"
    EXPLORATORY = "EXPLORATORY"


class DAGNode(BaseModel):
    """Single executable task node within a hierarchical Goal DAG."""
    model_config = ConfigDict(use_enum_values=True)

    node_id: str
    title: str
    description: str
    action_type: str
    tool_name: Optional[str] = None
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    branch_id: str
    tier: int = 1
    status: NodeStatus = NodeStatus.PENDING
    feasibility_score: float = 1.0
    estimated_duration_sec: float = 5.0
    is_checkpoint: bool = False
    retry_count: int = 0
    max_retries: int = 2
    result_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class DAGBranch(BaseModel):
    """Branch pathway comprising an ordered or semi-ordered collection of nodes."""
    model_config = ConfigDict(use_enum_values=True)

    branch_id: str
    name: str
    branch_type: BranchType = BranchType.PRIMARY
    node_ids: List[str] = Field(default_factory=list)
    feasibility_score: float = 1.0
    estimated_duration_sec: float = 30.0
    risk_tier: int = 1
    is_active: bool = False
    pruned: bool = False
    prune_reason: Optional[str] = None


class DAGCheckpoint(BaseModel):
    """Immutable state snapshot captured before speculative or high-impact node execution."""
    model_config = ConfigDict(use_enum_values=True)

    checkpoint_id: str
    dag_id: str
    step_index: int
    node_states: Dict[str, NodeStatus]
    context_snapshot: Dict[str, Any]
    timestamp: float = Field(default_factory=time.time)


class MetacognitiveReflection(BaseModel):
    """Record of metacognitive inspection detecting loops, oscillation, or recommending branch pruning."""
    model_config = ConfigDict(use_enum_values=True)

    reflection_id: str
    dag_id: str
    step_index: int
    detected_loop: bool = False
    loop_type: Optional[str] = None  # e.g. "stagnation", "oscillation_2cycle", "oscillation_3cycle"
    stagnation_detected: bool = False
    recommended_action: str = "CONTINUE"  # "CONTINUE", "RETRY_STEP", "PRUNE_BRANCH", "ABORT"
    target_branch_id: Optional[str] = None
    confidence_score: float = 1.0
    timestamp: float = Field(default_factory=time.time)


class GoalDAG(BaseModel):
    """Complete Hierarchical Tree-of-Thought Goal DAG model."""
    model_config = ConfigDict(use_enum_values=True)

    dag_id: str
    goal_description: str
    nodes: Dict[str, DAGNode] = Field(default_factory=dict)
    branches: Dict[str, DAGBranch] = Field(default_factory=dict)
    active_branch_id: str = ""
    status: str = "PENDING"  # "PENDING", "RUNNING", "COMPLETED", "FAILED", "ABORTED"
    checkpoints: List[DAGCheckpoint] = Field(default_factory=list)
    reflections: List[MetacognitiveReflection] = Field(default_factory=list)
    context_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    overall_progress_pct: float = 0.0


# Tool Argument Schemas for ToolRegistry (SAF-01)

class TotCreateGoalDagArgs(BaseModel):
    """Arguments for creating a hierarchical goal DAG."""
    goal_description: str = Field(..., description="High-level natural language user goal or objective.")
    max_contingency_branches: int = Field(default=2, ge=0, le=5, description="Maximum number of alternative contingency branches to generate.")
    exploration_depth: int = Field(default=3, ge=1, le=10, description="Exploration depth for thought tree expansion.")


class TotExecuteStepArgs(BaseModel):
    """Arguments for advancing execution of the active DAG by one step."""
    dag_id: str = Field(..., description="ID of the Goal DAG to execute.")
    node_id: Optional[str] = Field(None, description="Optional specific node to execute (must be in ready frontier). If omitted, next ready node is picked.")


class TotGetDagStatusArgs(BaseModel):
    """Arguments for querying full status and topology of a Goal DAG."""
    dag_id: str = Field(..., description="ID of the Goal DAG to query.")


class TotPruneBranchArgs(BaseModel):
    """Arguments for pruning an unviable branch in a Goal DAG."""
    dag_id: str = Field(..., description="ID of the Goal DAG.")
    branch_id: str = Field(..., description="ID of the branch to prune.")
    reason: Optional[str] = Field("Explicit manual pruning or metacognitive recommendation", description="Reason for branch pruning.")


class TotAbortGoalArgs(BaseModel):
    """Arguments for aborting an active Goal DAG."""
    dag_id: str = Field(..., description="ID of the Goal DAG to abort.")
    reason: Optional[str] = Field("User or Guardian abort", description="Reason for aborting the goal.")
