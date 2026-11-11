"""Adaptive Branch Pruner for Phenom Autonomous Planning (Milestone 28 Phase 2).

Evaluates candidate speculative branches, prunes non-viable or high-risk paths,
and maintains complete non-destructive pruning audit logs (PRUN-03.1, Rule 7).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.planning.goal_decomposition_engine import Rule8ViolationError
from services.backend.planning.speculative_planner import (
    speculative_planner,
    SpeculativePlanner,
    PlanBranch,
)

logger = logging.getLogger("phenom.planning.branch_pruner")


class PruningAuditRecord(BaseModel):
    audit_id: str
    target_id: str
    pruned_branch_ids: List[str]
    selected_branch_id: str
    selection_reason: str
    timestamp: float = Field(default_factory=time.time)


class BranchPruner:
    """Evaluates multi-path execution matrices and safely prunes sub-optimal or high-risk candidate branches."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self, planner: Optional[SpeculativePlanner] = None) -> None:
        self._planner = planner or speculative_planner
        self._audit_records: List[PruningAuditRecord] = []

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Branch pruner halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: branch pruning involving payments is strictly prohibited. Found: {text}"
            )

    def evaluate_risk_matrix(self, target_id: str) -> List[Dict[str, Any]]:
        """Calculates comparative risk, feasibility, and composite utility scores for candidate branches."""
        self._check_guardian()
        self._validate_rule_8(target_id)

        branches = self._planner.get_branches(target_id)
        matrix: List[Dict[str, Any]] = []

        for b in branches:
            # Composite utility: Feasibility weighted against risk and estimated latency
            # Higher is better: U = Feasibility * (1.0 - Risk)
            composite_utility = round(b.feasibility_score * (1.0 - b.risk_score), 3)
            matrix.append({
                "branch_id": b.branch_id,
                "name": b.name,
                "branch_type": b.branch_type.value,
                "feasibility_score": b.feasibility_score,
                "risk_score": b.risk_score,
                "composite_utility": composite_utility,
                "estimated_latency_ms": b.estimated_total_latency_ms,
                "is_selected": b.is_selected,
                "is_pruned": b.is_pruned,
            })

        return matrix

    def prune_branches(
        self,
        target_id: str,
        max_acceptable_risk: float = 0.30,
        min_acceptable_feasibility: float = 0.70,
    ) -> Dict[str, Any]:
        """Prunes branches exceeding risk tolerance or falling below feasibility thresholds."""
        self._check_guardian()
        self._validate_rule_8(target_id)

        branches = self._planner.get_branches(target_id)
        if not branches:
            raise ValueError(f"No branches found for target '{target_id}'.")

        pruned_ids: List[str] = []
        viable_branches: List[PlanBranch] = []

        for b in branches:
            if b.risk_score > max_acceptable_risk or b.feasibility_score < min_acceptable_feasibility:
                b.is_pruned = True
                b.is_selected = False
                pruned_ids.append(b.branch_id)
            else:
                b.is_pruned = False
                viable_branches.append(b)

        # Ensure at least one viable branch is selected
        if not viable_branches:
            # Fallback: keep the safest branch (lowest risk)
            safest = min(branches, key=lambda b: b.risk_score)
            safest.is_pruned = False
            safest.is_selected = True
            if safest.branch_id in pruned_ids:
                pruned_ids.remove(safest.branch_id)
            viable_branches.append(safest)
            selected_branch = safest
            reason = f"All branches exceeded risk threshold. Retained safest fallback branch '{safest.name}'."
        else:
            # Select the branch with highest composite utility
            best = max(viable_branches, key=lambda b: b.feasibility_score * (1.0 - b.risk_score))
            for vb in viable_branches:
                vb.is_selected = (vb.branch_id == best.branch_id)
            selected_branch = best
            reason = f"Selected optimal branch '{best.name}' with composite utility {round(best.feasibility_score * (1.0 - best.risk_score), 3)}."

        audit = PruningAuditRecord(
            audit_id=f"audit_{int(time.time() * 1000) % 1000000}",
            target_id=target_id,
            pruned_branch_ids=pruned_ids,
            selected_branch_id=selected_branch.branch_id,
            selection_reason=reason,
        )
        self._audit_records.append(audit)

        return {
            "target_id": target_id,
            "pruned_branch_count": len(pruned_ids),
            "viable_branch_count": len(viable_branches),
            "selected_branch_id": selected_branch.branch_id,
            "selected_branch_name": selected_branch.name,
            "selection_reason": reason,
            "audit_id": audit.audit_id,
        }

    def get_audit_history(self) -> List[Dict[str, Any]]:
        self._check_guardian()
        return [r.model_dump() for r in self._audit_records]


# Global singleton instance
branch_pruner = BranchPruner()
