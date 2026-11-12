"""Safety Matrix & Pragmatic Auto-Execution Tools for Phenom (Milestone 29 Phase 2).

Registers 3 safety matrix tools in ToolRegistry:
1. evaluate_tool_auto_execution_policy (Tier 0)
2. reclassify_safety_tier (Tier 1)
3. get_safety_tier_matrix (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.safety.tier_matrix import (
    safety_tier_matrix_manager,
)


# ==========================================
# 1. Evaluate Tool Auto Execution Policy (Tier 0)
# ==========================================

class EvaluateToolAutoExecutionPolicyArgs(BaseModel):
    tool_name: str = Field(..., description="Name of the registered tool to inspect.")


def preview_evaluate_tool_auto_execution_policy(args: Dict[str, Any]) -> str:
    tool_name = args.get("tool_name", "unknown")
    return f"Evaluate auto-execution policy and confirmation gate for tool '{tool_name}'."


@registry.register(
    name="evaluate_tool_auto_execution_policy",
    tier=0,
    description="Evaluates whether a tool auto-executes (Tier 0/1), requires explicit user confirmation (Tier 2), or is blocked (Tier 3).",
    args_schema=EvaluateToolAutoExecutionPolicyArgs,
    preview_fn=preview_evaluate_tool_auto_execution_policy,
    can_remember_per_folder=False,
)
def handle_evaluate_tool_auto_execution_policy(
    tool_name: str,
) -> Dict[str, Any]:
    policy = safety_tier_matrix_manager.evaluate_tool_policy(tool_name)
    return policy.model_dump()


# ==========================================
# 2. Reclassify Safety Tier (Tier 1)
# ==========================================

class ReclassifySafetyTierArgs(BaseModel):
    tool_name: str = Field(..., description="Name of the registered tool to reclassify.")
    new_tier: int = Field(..., ge=0, le=3, description="Target risk tier (0=Read-only auto, 1=Reversible auto, 2=Prompted, 3=Blocked).")
    reason: str = Field(default="", description="Operator justification for the safety tier adjustment.")


def preview_reclassify_safety_tier(args: Dict[str, Any]) -> str:
    tool_name = args.get("tool_name", "unknown")
    new_tier = args.get("new_tier", 0)
    reason = args.get("reason", "Operator adjustment")
    return f"Reclassify safety tier for '{tool_name}' to Tier {new_tier} (Reason: {reason})."


@registry.register(
    name="reclassify_safety_tier",
    tier=1,
    description="Adjusts a tool's safety tier (0, 1, 2, or 3) with immutable audit history and Guardian kill switch verification.",
    args_schema=ReclassifySafetyTierArgs,
    preview_fn=preview_reclassify_safety_tier,
    can_remember_per_folder=False,
)
def handle_reclassify_safety_tier(
    tool_name: str,
    new_tier: int,
    reason: str = "",
) -> Dict[str, Any]:
    record = safety_tier_matrix_manager.reclassify_tool(tool_name, new_tier, reason=reason)
    return record.model_dump()


# ==========================================
# 3. Get Safety Tier Matrix (Tier 0)
# ==========================================

class GetSafetyTierMatrixArgs(BaseModel):
    pass


def preview_get_safety_tier_matrix(args: Dict[str, Any]) -> str:
    return "Retrieve comprehensive safety tier matrix, auto-execution counts, and high-risk boundary breakdown."


@registry.register(
    name="get_safety_tier_matrix",
    tier=0,
    description="Generates a full audit report of all registered tools, their active risk tiers, and auto-execution status.",
    args_schema=GetSafetyTierMatrixArgs,
    preview_fn=preview_get_safety_tier_matrix,
    can_remember_per_folder=False,
)
def handle_get_safety_tier_matrix() -> Dict[str, Any]:
    report = safety_tier_matrix_manager.get_matrix_report()
    return report.model_dump()
