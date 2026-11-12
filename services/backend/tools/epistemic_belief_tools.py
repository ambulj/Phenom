"""Safety-Wrapped Epistemic Belief Tools.

Registers tools with ToolRegistry for updating epistemic beliefs,
detecting and resolving contradictions, and inspecting the active belief network (Phase 26-02 EPI-01 / RES-03).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.epistemic.belief_network import (
    epistemic_belief_network,
    EpistemicBelief,
    BeliefRevisionRecord,
)
from services.backend.epistemic.contradiction_resolver import contradiction_resolver


# ==========================================
# 1. Update Epistemic Belief (Tier 1)
# ==========================================

class UpdateEpistemicBeliefArgs(BaseModel):
    subject: str = Field(..., description="Subject of the proposition (e.g. 'User', 'Backend')")
    predicate: str = Field(..., description="Relationship or property predicate (e.g. 'prefers_theme')")
    object_value: str = Field(..., description="Value or object asserted (e.g. 'Dark Cyberpunk Glow')")
    confidence_boost: float = Field(0.15, description="Bayesian confidence boost or initial confidence weight (0.0 - 1.0)")
    source: str = Field("USER_STATEMENT", description="Source of the belief update ('USER_STATEMENT', 'INFERRED', 'OBSERVED')")


def update_epistemic_belief_preview(args: Dict[str, Any]) -> str:
    subj = args.get("subject", "Unknown")
    pred = args.get("predicate", "unknown_pred")
    val = args.get("object_value", "unknown_val")
    src = args.get("source", "USER_STATEMENT")
    return f"Update epistemic belief proposition: [{subj}] {pred} -> '{val}' (source: {src})."


@registry.register(
    name="update_epistemic_belief",
    tier=1,
    description="Updates or asserts an epistemic belief proposition with Bayesian confidence tracking and revision logging.",
    args_schema=UpdateEpistemicBeliefArgs,
    preview_fn=update_epistemic_belief_preview,
    can_remember_per_folder=False,
)
def handle_update_epistemic_belief(
    subject: str,
    predicate: str,
    object_value: str,
    confidence_boost: float = 0.15,
    source: str = "USER_STATEMENT",
) -> Dict[str, Any]:
    belief = epistemic_belief_network.update_belief(
        subject=subject,
        predicate=predicate,
        object_value=object_value,
        confidence_boost=confidence_boost,
        source=source,
        reason=f"Safety tool assertion via {source}",
    )
    return {
        "status": "UPDATED",
        "belief": belief.model_dump(),
    }


# ==========================================
# 2. Resolve Belief Contradiction (Tier 0)
# ==========================================

class ResolveBeliefContradictionArgs(BaseModel):
    subject: str = Field(..., description="Subject of the proposition to test")
    predicate: str = Field(..., description="Predicate to test")
    claimed_value: str = Field(..., description="The newly claimed value to evaluate against current beliefs")
    is_user_direct: bool = Field(True, description="Whether the claim is a direct authoritative statement from the user")


def resolve_belief_contradiction_preview(args: Dict[str, Any]) -> str:
    subj = args.get("subject", "Unknown")
    pred = args.get("predicate", "unknown_pred")
    claim = args.get("claimed_value", "unknown_val")
    return f"Evaluate potential contradiction for proposition [{subj}] {pred} against claimed value '{claim}'."


@registry.register(
    name="resolve_belief_contradiction",
    tier=0,
    description="Evaluates whether a new proposition contradicts current beliefs and calculates the rational resolution strategy.",
    args_schema=ResolveBeliefContradictionArgs,
    preview_fn=resolve_belief_contradiction_preview,
    can_remember_per_folder=False,
)
def handle_resolve_belief_contradiction(
    subject: str,
    predicate: str,
    claimed_value: str,
    is_user_direct: bool = True,
) -> Dict[str, Any]:
    result = contradiction_resolver.analyze_claim(
        subject=subject,
        predicate=predicate,
        claimed_value=claimed_value,
        is_user_direct=is_user_direct,
    )
    return {
        "conflict_detected": result.conflict_detected,
        "existing_belief": result.existing_belief.model_dump() if result.existing_belief else None,
        "conflicting_claim": result.conflicting_claim,
        "resolution_strategy": result.resolution_strategy,
        "confidence_shift": result.confidence_shift,
        "explanation": result.explanation,
    }


# ==========================================
# 3. Get Active Belief Network (Tier 0)
# ==========================================

class GetActiveBeliefNetworkArgs(BaseModel):
    active_only: bool = Field(True, description="Whether to include only currently active beliefs")


def get_active_belief_network_preview(args: Dict[str, Any]) -> str:
    return "Retrieve active epistemic belief network nodes and Bayesian revision history."


@registry.register(
    name="get_active_belief_network",
    tier=0,
    description="Retrieves the full epistemic belief network including propositions, confidence scores, and revision history.",
    args_schema=GetActiveBeliefNetworkArgs,
    preview_fn=get_active_belief_network_preview,
    can_remember_per_folder=False,
)
def handle_get_active_belief_network(active_only: bool = True) -> Dict[str, Any]:
    beliefs = epistemic_belief_network.get_beliefs(active_only=active_only)
    revisions = epistemic_belief_network.get_revisions()
    return {
        "belief_count": len(beliefs),
        "beliefs": [b.model_dump() for b in beliefs],
        "revision_count": len(revisions),
        "recent_revisions": [r.model_dump() for r in revisions[:10]],
    }
