"""Counterfactual Plan Evaluator for Phenom (Milestone 26 Phase 3).

Evaluates multi-step plan candidates before execution by projecting nominal
and counterfactual failure branches, forecasting side-effects, and computing safety scores (SIM-01.2, EVA-02.1).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.simulation.world_model_simulator import (
    SimulatedStepResult,
    WorldModelSimulator,
    world_model_simulator,
    Rule8ViolationError,
)

logger = logging.getLogger("phenom.simulation.counterfactual")


class PlanBranch(BaseModel):
    branch_name: str  # NOMINAL_SUCCESS, PERMISSION_FAIL_RETRY, TIMEOUT_BRANCH
    probability: float  # 0.0 - 1.0
    steps_simulated: List[SimulatedStepResult] = Field(default_factory=list)
    final_verdict: str  # PASS, RECOVERABLE_ERROR, FATAL_BLOCKED
    accumulated_risk: float = 0.0  # 0.0 - 1.0


class CounterfactualEvaluationReport(BaseModel):
    plan_title: str
    nominal_feasibility_score: float  # 0.0 - 1.0
    overall_safety_rating: str  # SAFE_TO_DISPATCH, REQUIRES_CONFIRMATION, BLOCKED
    branches: List[PlanBranch] = Field(default_factory=list)
    predicted_side_effects: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class CounterfactualEvaluator:
    """Evaluates plan candidates by projecting alternative counterfactual branches."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self, simulator: Optional[WorldModelSimulator] = None) -> None:
        self._sim = simulator or world_model_simulator

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Counterfactual evaluator halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: plan counterfactual involving payments is strictly prohibited. Found: {text}"
            )

    def evaluate_plan(
        self,
        plan_title: str,
        steps: List[Dict[str, Any]],
    ) -> CounterfactualEvaluationReport:
        """Simulate nominal execution and project counterfactual error branches."""
        self._check_guardian()
        self._validate_rule_8(plan_title)

        for step in steps:
            self._validate_rule_8(step.get("action", ""))
            self._validate_rule_8(step.get("target", ""))
            if "payload" in step and isinstance(step["payload"], dict):
                for v in step["payload"].values():
                    if isinstance(v, str):
                        self._validate_rule_8(v)

        # 1. Simulate Nominal Success Branch
        nominal_steps: List[SimulatedStepResult] = []
        all_side_effects: List[str] = []
        base_risk = 0.0

        for s in steps:
            action = s.get("action", "UNKNOWN")
            target = s.get("target", "system")
            payload = s.get("payload", {})
            res = self._sim.simulate_step(action, target, payload)
            nominal_steps.append(res)
            all_side_effects.extend(res.side_effects)

            # Weight step risks
            if action.upper() in ("FILE_DELETE", "DELETE_FILE", "PROCESS_KILL"):
                base_risk += 0.20
            elif action.upper() in ("EXEC_COMMAND", "RUN_COMMAND"):
                base_risk += 0.15
            else:
                base_risk += 0.05

        base_risk = min(0.95, base_risk)
        feasibility = round(max(0.10, 1.0 - base_risk), 2)

        nominal_branch = PlanBranch(
            branch_name="NOMINAL_SUCCESS",
            probability=round(feasibility * 0.85, 2),
            steps_simulated=nominal_steps,
            final_verdict="PASS",
            accumulated_risk=round(base_risk, 2),
        )

        # 2. Counterfactual Branch 1: Permission Denied Branch
        perm_steps = [
            SimulatedStepResult(
                step_id="step_perm_01",
                action_type="SIMULATED_PERMISSION_CHECK",
                target=steps[0].get("target", "system") if steps else "system",
                outcome="PERMISSION_ERROR",
                state_delta={"error": "AccessDenied"},
                side_effects=["Trigger Tier 1 approval fallback"],
            )
        ]
        perm_branch = PlanBranch(
            branch_name="COUNTERFACTUAL_PERMISSION_FALLBACK",
            probability=round(max(0.05, 1.0 - feasibility) * 0.6, 2),
            steps_simulated=perm_steps,
            final_verdict="RECOVERABLE_ERROR",
            accumulated_risk=0.10,
        )

        # 3. Counterfactual Branch 2: Timeout / Process Delay Branch
        timeout_steps = [
            SimulatedStepResult(
                step_id="step_timeout_01",
                action_type="STEP_TIMEOUT_GUARD",
                target="ExecutionTimer",
                outcome="BLOCKED",
                state_delta={"timeout_seconds": 2.0},
                side_effects=["LoopGuard abort invoked"],
            )
        ]
        timeout_branch = PlanBranch(
            branch_name="COUNTERFACTUAL_TIMEOUT_INTERRUPT",
            probability=0.08,
            steps_simulated=timeout_steps,
            final_verdict="RECOVERABLE_ERROR",
            accumulated_risk=0.05,
        )

        # Safety rating
        if feasibility >= 0.80:
            rating = "SAFE_TO_DISPATCH"
        elif feasibility >= 0.50:
            rating = "REQUIRES_CONFIRMATION"
        else:
            rating = "BLOCKED"

        recs = [
            f"Nominal success confidence projected at {(feasibility * 100):.0f}%.",
            f"Total forecasted collateral side-effects: {len(all_side_effects)}.",
        ]
        if base_risk > 0.30:
            recs.append("Verify Tier 1 confirmations for potentially mutating steps.")

        return CounterfactualEvaluationReport(
            plan_title=plan_title,
            nominal_feasibility_score=feasibility,
            overall_safety_rating=rating,
            branches=[nominal_branch, perm_branch, timeout_branch],
            predicted_side_effects=list(set(all_side_effects)),
            recommendations=recs,
        )

    def forecast_side_effects(self, steps: List[Dict[str, Any]]) -> List[str]:
        """Convenience method returning predicted side effects across all steps."""
        report = self.evaluate_plan(plan_title="Forecast Side Effects", steps=steps)
        return report.predicted_side_effects


# Global singleton instance
counterfactual_evaluator = CounterfactualEvaluator()
