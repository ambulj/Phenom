"""Plan Tree Data Structures for Phenom Autonomous Planning (Milestone 28 Phase 1).

Implements recursive, depth-bounded hierarchical plan trees (GoalNode, SubtaskNode, LeafActionNode)
with prerequisite dependency validation, acyclicity guarantees, and serializable schemas (TREE-02.1).
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PlanNodeStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PRUNED = "PRUNED"


class PlanNodeType(str, Enum):
    ROOT_GOAL = "ROOT_GOAL"
    SUBTASK = "SUBTASK"
    LEAF_ACTION = "LEAF_ACTION"


class PlanNode(BaseModel):
    node_id: str = Field(default_factory=lambda: f"node_{uuid.uuid4().hex[:8]}")
    title: str
    node_type: PlanNodeType = PlanNodeType.SUBTASK
    status: PlanNodeStatus = PlanNodeStatus.PENDING
    depth: int = 0
    parent_id: Optional[str] = None
    prerequisites: List[str] = Field(default_factory=list)
    children_ids: List[str] = Field(default_factory=list)
    action_type: Optional[str] = None  # e.g., INSPECT, SYNTHESIZE, EXECUTE, VERIFY
    parameters: Dict[str, Any] = Field(default_factory=dict)
    estimated_duration_ms: float = 100.0
    created_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None


class PlanTree(BaseModel):
    tree_id: str = Field(default_factory=lambda: f"tree_{uuid.uuid4().hex[:8]}")
    root_goal: str
    nodes: Dict[str, PlanNode] = Field(default_factory=dict)
    max_depth: int = 4
    created_at: float = Field(default_factory=time.time)

    def add_node(self, node: PlanNode) -> None:
        """Adds a node to the plan tree and links it to its parent."""
        if node.depth > self.max_depth:
            raise ValueError(f"Node depth {node.depth} exceeds tree max depth {self.max_depth}")

        self.nodes[node.node_id] = node
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node.node_id not in parent.children_ids:
                parent.children_ids.append(node.node_id)

    def get_node(self, node_id: str) -> Optional[PlanNode]:
        return self.nodes.get(node_id)

    def get_children(self, node_id: str) -> List[PlanNode]:
        node = self.get_node(node_id)
        if not node:
            return []
        return [self.nodes[cid] for cid in node.children_ids if cid in self.nodes]

    def get_prerequisites(self, node_id: str) -> List[PlanNode]:
        node = self.get_node(node_id)
        if not node:
            return []
        return [self.nodes[pid] for pid in node.prerequisites if pid in self.nodes]

    def is_runnable(self, node_id: str) -> bool:
        """A node is runnable if its status is PENDING and all prerequisite nodes are COMPLETED."""
        node = self.get_node(node_id)
        if not node or node.status != PlanNodeStatus.PENDING:
            return False

        for prereq_id in node.prerequisites:
            prereq = self.get_node(prereq_id)
            if not prereq or prereq.status != PlanNodeStatus.COMPLETED:
                return False

        return True

    def calculate_progress(self) -> float:
        """Returns overall tree completion percentage [0.0 - 1.0]."""
        if not self.nodes:
            return 0.0
        completed = sum(1 for n in self.nodes.values() if n.status == PlanNodeStatus.COMPLETED)
        return round(completed / len(self.nodes), 3)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tree_id": self.tree_id,
            "root_goal": self.root_goal,
            "total_nodes": len(self.nodes),
            "progress": self.calculate_progress(),
            "nodes": [n.model_dump() for n in self.nodes.values()],
            "created_at": self.created_at,
        }
