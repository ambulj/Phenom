"""Goal Planning Tools for Phenom Autonomous Planning (Milestone 28 Phase 1).

Registers 3 planning tools in ToolRegistry:
1. decompose_hierarchical_goal (Tier 0)
2. expand_plan_tree_node (Tier 1)
3. get_active_goal_tree (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.planning.goal_decomposition_engine import (
    goal_decomposition_engine,
)


# ==========================================
# 1. Decompose Hierarchical Goal (Tier 0)
# ==========================================

class DecomposeHierarchicalGoalArgs(BaseModel):
    goal_description: str = Field(..., description="High-level natural language objective to decompose into a hierarchical plan tree.")
    max_depth: int = Field(default=4, ge=1, le=6, description="Maximum branching depth limit for the plan tree hierarchy.")


def preview_decompose_hierarchical_goal(args: Dict[str, Any]) -> str:
    goal = args.get("goal_description", "Unknown Goal")
    depth = args.get("max_depth", 4)
    return f"Deconstruct goal '{goal}' into recursive hierarchical plan tree (max depth: {depth})."


@registry.register(
    name="decompose_hierarchical_goal",
    tier=0,
    description="Deconstructs a high-level natural language objective into a multi-tier hierarchical plan tree with DAG prerequisites.",
    args_schema=DecomposeHierarchicalGoalArgs,
    preview_fn=preview_decompose_hierarchical_goal,
    can_remember_per_folder=False,
)
def handle_decompose_hierarchical_goal(
    goal_description: str,
    max_depth: int = 4,
) -> Dict[str, Any]:
    tree = goal_decomposition_engine.decompose_goal(goal_description, max_depth=max_depth)
    return tree.to_dict()


# ==========================================
# 2. Expand Plan Tree Node (Tier 1)
# ==========================================

class ExpandPlanTreeNodeArgs(BaseModel):
    tree_id: str = Field(..., description="Unique ID of the target plan tree.")
    parent_node_id: str = Field(..., description="Node ID within the tree to expand with child steps.")
    new_children: List[Dict[str, Any]] = Field(..., description="List of subtask or leaf action dictionaries to graft as child nodes.")


def preview_expand_plan_tree_node(args: Dict[str, Any]) -> str:
    tid = args.get("tree_id", "active_tree")
    pid = args.get("parent_node_id", "unknown_node")
    count = len(args.get("new_children", []))
    return f"Expand plan node '{pid}' in tree '{tid}' with {count} child action step(s)."


@registry.register(
    name="expand_plan_tree_node",
    tier=1,
    description="Expands a subtask node within a plan tree with finer-grained child action steps, enforcing tree depth bounds.",
    args_schema=ExpandPlanTreeNodeArgs,
    preview_fn=preview_expand_plan_tree_node,
    can_remember_per_folder=False,
)
def handle_expand_plan_tree_node(
    tree_id: str,
    parent_node_id: str,
    new_children: List[Dict[str, Any]],
) -> Dict[str, Any]:
    nodes = goal_decomposition_engine.expand_node(tree_id, parent_node_id, new_children)
    tree = goal_decomposition_engine.get_tree(tree_id)
    return {
        "tree_id": tree_id,
        "parent_node_id": parent_node_id,
        "expanded_children_count": len(nodes),
        "total_tree_nodes": len(tree.nodes) if tree else len(nodes),
        "nodes": [n.model_dump() for n in nodes],
    }


# ==========================================
# 3. Get Active Goal Tree (Tier 0)
# ==========================================

class GetActiveGoalTreeArgs(BaseModel):
    tree_id: Optional[str] = Field(default=None, description="Optional tree ID; defaults to currently active plan tree.")


def preview_get_active_goal_tree(args: Dict[str, Any]) -> str:
    tid = args.get("tree_id") or "active"
    return f"Retrieve hierarchical plan tree graph and completion progress for '{tid}'."


@registry.register(
    name="get_active_goal_tree",
    tier=0,
    description="Retrieves the current active hierarchical plan tree graph, nodes, and completion progress metrics.",
    args_schema=GetActiveGoalTreeArgs,
    preview_fn=preview_get_active_goal_tree,
    can_remember_per_folder=False,
)
def handle_get_active_goal_tree(
    tree_id: Optional[str] = None,
) -> Dict[str, Any]:
    tree = goal_decomposition_engine.get_tree(tree_id)
    if not tree:
        return {"error": "No active plan tree found.", "tree": None}
    return tree.to_dict()
