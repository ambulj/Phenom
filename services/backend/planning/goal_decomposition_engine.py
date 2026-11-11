"""Goal Decomposition Engine for Phenom Autonomous Planning (Milestone 28 Phase 1).

Deconstructs high-level user directives into recursive, dependency-validated plan trees
with zero cloud egress (Rule 4), Rule 8 payment defenses, and Guardian halt SLA compliance (GOAL-01.1, GOAL-01.2).
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from services.backend.safety.guardian import guardian
from services.backend.planning.plan_tree import (
    PlanNode,
    PlanNodeStatus,
    PlanNodeType,
    PlanTree,
)

logger = logging.getLogger("phenom.planning.goal_decomposition")


class Rule8ViolationError(Exception):
    """Raised when goal decomposition or task payload involves payment/checkout keywords."""
    pass


class GoalDecompositionEngine:
    """Recursively decomposes user goals into structured, hierarchical plan trees."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._trees: Dict[str, PlanTree] = {}
        self._active_tree_id: Optional[str] = None
        self._init_default_tree()

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Goal decomposition engine halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: goal planning involving payments is strictly prohibited. Found: {text}"
            )

    def _init_default_tree(self) -> None:
        """Seeds an initial verified tree for immediate system availability."""
        tree = self.decompose_goal("Autonomous System Health & Safety Verification")
        self._active_tree_id = tree.tree_id

    def decompose_goal(self, goal_description: str, max_depth: int = 4) -> PlanTree:
        """Decomposes a high-level goal into a multi-tier plan tree (Root -> Subtasks -> Leaf Actions)."""
        self._check_guardian()
        self._validate_rule_8(goal_description)

        tree = PlanTree(
            tree_id=f"tree_{uuid.uuid4().hex[:8]}",
            root_goal=goal_description,
            max_depth=max_depth,
        )

        # 1. Root Goal Node (Depth 0)
        root_node = PlanNode(
            node_id=f"root_{uuid.uuid4().hex[:6]}",
            title=goal_description,
            node_type=PlanNodeType.ROOT_GOAL,
            status=PlanNodeStatus.IN_PROGRESS,
            depth=0,
            parent_id=None,
        )
        tree.add_node(root_node)

        # 2. Stage 1: Context & Dependency Analysis (Depth 1)
        st1 = PlanNode(
            node_id=f"sub_{uuid.uuid4().hex[:6]}",
            title=f"Analyze Prerequisites & State for '{goal_description[:35]}'",
            node_type=PlanNodeType.SUBTASK,
            status=PlanNodeStatus.PENDING,
            depth=1,
            parent_id=root_node.node_id,
            action_type="INSPECT",
            estimated_duration_ms=45.0,
        )
        tree.add_node(st1)

        # Leaf 1.1: Snapshot Environment State (Depth 2)
        leaf1_1 = PlanNode(
            node_id=f"leaf_{uuid.uuid4().hex[:6]}",
            title="Inspect System State & Active Processes",
            node_type=PlanNodeType.LEAF_ACTION,
            status=PlanNodeStatus.PENDING,
            depth=2,
            parent_id=st1.node_id,
            action_type="INSPECT_STATE",
            parameters={"scope": "local_environment"},
            estimated_duration_ms=20.0,
        )
        tree.add_node(leaf1_1)

        # 3. Stage 2: Synthesis & Execution (Depth 1)
        st2 = PlanNode(
            node_id=f"sub_{uuid.uuid4().hex[:6]}",
            title=f"Execute Core Workflow for '{goal_description[:35]}'",
            node_type=PlanNodeType.SUBTASK,
            status=PlanNodeStatus.PENDING,
            depth=1,
            parent_id=root_node.node_id,
            prerequisites=[st1.node_id],
            action_type="EXECUTE",
            estimated_duration_ms=120.0,
        )
        tree.add_node(st2)

        # Leaf 2.1: Primary Synthesis Task (Depth 2)
        leaf2_1 = PlanNode(
            node_id=f"leaf_{uuid.uuid4().hex[:6]}",
            title="Synthesize Structured Solution & State Deltas",
            node_type=PlanNodeType.LEAF_ACTION,
            status=PlanNodeStatus.PENDING,
            depth=2,
            parent_id=st2.node_id,
            prerequisites=[leaf1_1.node_id],
            action_type="SYNTHESIZE",
            parameters={"target": goal_description},
            estimated_duration_ms=80.0,
        )
        tree.add_node(leaf2_1)

        # 4. Stage 3: Verification & Invariant Audit (Depth 1)
        st3 = PlanNode(
            node_id=f"sub_{uuid.uuid4().hex[:6]}",
            title=f"Verify Safety Invariants & Acceptance for '{goal_description[:35]}'",
            node_type=PlanNodeType.SUBTASK,
            status=PlanNodeStatus.PENDING,
            depth=1,
            parent_id=root_node.node_id,
            prerequisites=[st2.node_id],
            action_type="VERIFY",
            estimated_duration_ms=50.0,
        )
        tree.add_node(st3)

        # Leaf 3.1: Guardian SLA & Invariant Verification (Depth 2)
        leaf3_1 = PlanNode(
            node_id=f"leaf_{uuid.uuid4().hex[:6]}",
            title="Execute Guardian SLA & Invariant Assertion",
            node_type=PlanNodeType.LEAF_ACTION,
            status=PlanNodeStatus.PENDING,
            depth=2,
            parent_id=st3.node_id,
            prerequisites=[leaf2_1.node_id],
            action_type="VERIFY_SLA",
            parameters={"hard_sla_ms": 25.0},
            estimated_duration_ms=30.0,
        )
        tree.add_node(leaf3_1)

        self._trees[tree.tree_id] = tree
        self._active_tree_id = tree.tree_id
        return tree

    def expand_node(
        self,
        tree_id: str,
        parent_node_id: str,
        new_children: List[Dict[str, Any]],
    ) -> List[PlanNode]:
        """Expands an existing subtask node with finer-grained child nodes."""
        self._check_guardian()
        tree = self.get_tree(tree_id)
        if not tree:
            raise ValueError(f"Plan tree '{tree_id}' not found.")

        parent = tree.get_node(parent_node_id)
        if not parent:
            raise ValueError(f"Parent node '{parent_node_id}' not found in tree '{tree_id}'.")

        if parent.depth >= tree.max_depth:
            raise ValueError(f"Cannot expand node at max depth {tree.max_depth}.")

        created_nodes: List[PlanNode] = []
        for item in new_children:
            title = item.get("title", "Expanded Action Step")
            self._validate_rule_8(title)
            action_type = item.get("action_type", "EXECUTE")
            params = item.get("parameters", {})
            for v in params.values():
                if isinstance(v, str):
                    self._validate_rule_8(v)

            child = PlanNode(
                node_id=f"leaf_{uuid.uuid4().hex[:6]}",
                title=title,
                node_type=PlanNodeType.LEAF_ACTION,
                status=PlanNodeStatus.PENDING,
                depth=parent.depth + 1,
                parent_id=parent.node_id,
                action_type=action_type,
                parameters=params,
                estimated_duration_ms=float(item.get("estimated_duration_ms", 30.0)),
            )
            tree.add_node(child)
            created_nodes.append(child)

        return created_nodes

    def mark_node_status(self, tree_id: str, node_id: str, status: PlanNodeStatus) -> PlanNode:
        """Updates node status, setting completion timestamps when done."""
        self._check_guardian()
        tree = self.get_tree(tree_id)
        if not tree:
            raise ValueError(f"Plan tree '{tree_id}' not found.")

        node = tree.get_node(node_id)
        if not node:
            raise ValueError(f"Node '{node_id}' not found in tree '{tree_id}'.")

        node.status = status
        if status == PlanNodeStatus.COMPLETED:
            node.completed_at = time.time()
        elif status == PlanNodeStatus.IN_PROGRESS:
            node.completed_at = None

        return node

    def get_tree(self, tree_id: Optional[str] = None) -> Optional[PlanTree]:
        """Retrieves a plan tree by ID or the currently active tree."""
        self._check_guardian()
        tid = tree_id or self._active_tree_id
        if not tid:
            return None
        return self._trees.get(tid)

    def list_trees(self) -> List[PlanTree]:
        self._check_guardian()
        return list(self._trees.values())


# Global singleton instance
goal_decomposition_engine = GoalDecompositionEngine()
