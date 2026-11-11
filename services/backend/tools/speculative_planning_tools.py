"""Speculative Planning & Branch Pruning Tools for Phenom Autonomous Planning (Milestone 28 Phase 2).

Registers 3 planning tools in ToolRegistry:
1. generate_speculative_plan_branches (Tier 0)
2. prune_nonviable_branches (Tier 1)
3. evaluate_branch_risk_matrix (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.planning.speculative_planner import speculative_planner
from services.backend.planning.branch_pruner import branch_pruner


# ==========================================
# 1. Generate Speculative Plan Branches (Tier 0)
# ==========================================

class GenerateSpeculativePlanBranchesArgs(BaseModel):
    target_goal_or_tree_id: str = Field(..., description="Goal objective or plan tree ID to synthesize speculative branches for.")


def preview_generate_speculative_plan_branches(args: Dict[str, Any]) -> str:
    target = args.get("target_goal_or_tree_id", "Unknown Goal")
    return f"Synthesize speculative multi-path execution branches (Nominal, Contingency, Defensive) for '{target}'."


@registry.register(
    name="generate_speculative_plan_branches",
    tier=0,
    description="Synthesizes concurrent speculative execution branches (Nominal, Contingency, Defensive) with risk-reward feasibility scores.",
    args_schema=GenerateSpeculativePlanBranchesArgs,
    preview_fn=preview_generate_speculative_plan_branches,
    can_remember_per_folder=False,
)
def handle_generate_speculative_plan_branches(
    target_goal_or_tree_id: str,
) -> Dict[str, Any]:
    branches = speculative_planner.generate_speculative_branches(target_goal_or_tree_id)
    return {
        "target_id": target_goal_or_tree_id,
        "branch_count": len(branches),
        "branches": [b.model_dump() for b in branches],
    }


# ==========================================
# 2. Prune Non-Viable Branches (Tier 1)
# ==========================================

class PruneNonviableBranchesArgs(BaseModel):
    target_id: str = Field(..., description="Target goal or plan tree ID whose branches will be pruned.")
    max_acceptable_risk: float = Field(default=0.30, ge=0.0, le=1.0, description="Maximum risk tolerance threshold [0.0 - 1.0].")
    min_acceptable_feasibility: float = Field(default=0.70, ge=0.0, le=1.0, description="Minimum feasibility threshold [0.0 - 1.0].")


def preview_prune_nonviable_branches(args: Dict[str, Any]) -> str:
    tid = args.get("target_id", "active_target")
    risk = args.get("max_acceptable_risk", 0.30)
    feas = args.get("min_acceptable_feasibility", 0.70)
    return f"Prune non-viable execution branches for '{tid}' (risk threshold: {risk}, min feasibility: {feas})."


@registry.register(
    name="prune_nonviable_branches",
    tier=1,
    description="Evaluates candidate branches, prunes paths exceeding risk tolerance or underperforming feasibility, and logs audit record.",
    args_schema=PruneNonviableBranchesArgs,
    preview_fn=preview_prune_nonviable_branches,
    can_remember_per_folder=False,
)
def handle_prune_nonviable_branches(
    target_id: str,
    max_acceptable_risk: float = 0.30,
    min_acceptable_feasibility: float = 0.70,
) -> Dict[str, Any]:
    result = branch_pruner.prune_branches(
        target_id=target_id,
        max_acceptable_risk=max_acceptable_risk,
        min_acceptable_feasibility=min_acceptable_feasibility,
    )
    return result


# ==========================================
# 3. Evaluate Branch Risk Matrix (Tier 0)
# ==========================================

class EvaluateBranchRiskMatrixArgs(BaseModel):
    target_id: str = Field(..., description="Target goal or plan tree ID to evaluate.")


def preview_evaluate_branch_risk_matrix(args: Dict[str, Any]) -> str:
    tid = args.get("target_id", "active_target")
    return f"Evaluate comparative risk-reward and utility matrix for speculative branches under '{tid}'."


@registry.register(
    name="evaluate_branch_risk_matrix",
    tier=0,
    description="Calculates comparative risk, feasibility, and composite utility scores across all speculative branches.",
    args_schema=EvaluateBranchRiskMatrixArgs,
    preview_fn=preview_evaluate_branch_risk_matrix,
    can_remember_per_folder=False,
)
def handle_evaluate_branch_risk_matrix(
    target_id: str,
) -> Dict[str, Any]:
    matrix = branch_pruner.evaluate_risk_matrix(target_id)
    return {
        "target_id": target_id,
        "branch_evaluations": matrix,
    }
