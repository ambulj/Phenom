"""
Mission DAG Schemas for Autonomous Task Planning & Execution (Phase 47-01).
Enforces:
1. DAGNode models representing atomic tool invocations with explicit dependencies and risk tiers.
2. MissionDAG models with goal, nodes, risk level calculation, and upfront approval tracking.
3. PreconditionCheckResult models capturing safety allowlist and file existence audits.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class DAGNodeStatus(str, Enum):
    pending = "pending"
    ready = "ready"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"
    halted = "halted"

    # Uppercase aliases for compatibility
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    HALTED = "halted"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

    # Uppercase aliases for compatibility
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DAGNode(BaseModel):
    """Represents a single atomic execution step within a Directed Acyclic Graph."""
    node_id: str = Field(..., description="Unique identifier for the node within the DAG (e.g. 'node-1')")
    title: str = Field(..., description="Human-readable title describing what this step does")
    tool_name: str = Field(..., description="Target tool registered in ToolRegistry")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to the tool")
    tier: int = Field(default=1, ge=0, le=3, description="Safety tier of the tool operation (0=Read-only, 1=Reversible, 2=Confirmation, 3=Physical)")
    depends_on: List[str] = Field(default_factory=list, description="List of node_ids that must complete successfully before this node executes")
    timeout_seconds: int = Field(default=60, ge=1, le=900, description="Maximum execution timeout in seconds")
    status: DAGNodeStatus = Field(default=DAGNodeStatus.pending, description="Current execution state of the node")
    result: Optional[Any] = Field(default=None, description="Output payload produced upon successful tool execution")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")


class PreconditionCheckResult(BaseModel):
    """Carries pre-flight verification results for a DAG node or full mission."""
    passed: bool = Field(..., description="True if all safety preconditions were satisfied")
    checked_paths: List[str] = Field(default_factory=list, description="File/directory paths validated against allowlists")
    checked_tools: List[str] = Field(default_factory=list, description="Tool names verified in ToolRegistry")
    violations: List[str] = Field(default_factory=list, description="List of detected precondition violations or security rejections")


class MissionDAG(BaseModel):
    """Represents a complete autonomous execution plan formulated as a Directed Acyclic Graph."""
    mission_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique mission identifier")
    goal: str = Field(..., description="High-level natural language prompt requested by operator")
    nodes: List[DAGNode] = Field(default_factory=list, description="Ordered or unordered nodes comprising the execution graph")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Timestamp of plan formulation")
    risk_level: RiskLevel = Field(default=RiskLevel.low, description="Aggregated risk assessment for the mission")
    requires_confirmation: bool = Field(default=False, description="True if mission crosses Tier 2/3 boundaries or touches high-risk actions")
    is_approved: bool = Field(default=False, description="True once operator explicitly approves plan via upfront modal")

    def get_node(self, node_id: str) -> Optional[DAGNode]:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def recalculate_risk(self) -> None:
        """Computes aggregate risk level and confirmation requirement based on constituent nodes."""
        max_tier = max((n.tier for n in self.nodes), default=0)
        if max_tier >= 3:
            self.risk_level = RiskLevel.critical
            self.requires_confirmation = True
        elif max_tier == 2:
            self.risk_level = RiskLevel.high
            self.requires_confirmation = True
        elif max_tier == 1:
            self.risk_level = RiskLevel.medium
            # In untainted mode, Tier 1 is auto_execute, but upfront approval is still recorded
            self.requires_confirmation = False
        else:
            self.risk_level = RiskLevel.low
            self.requires_confirmation = False
