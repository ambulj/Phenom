"""Autonomous Strategy Reflector for Phenom Autonomous Planning (Milestone 28 Phase 4).

Synthesizes reusable planning heuristics, updates confidence weights with observation counts,
and caches successful execution strategies with zero cloud telemetry egress (REFL-02.1, Rule 4).
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.planning.goal_decomposition_engine import Rule8ViolationError
from services.backend.planning.metacognitive_evaluator import (
    metacognitive_evaluator,
    MetacognitiveEvaluator,
    MetacognitiveReport,
)

logger = logging.getLogger("phenom.planning.strategy_reflector")


class StrategyHeuristic(BaseModel):
    heuristic_id: str = Field(default_factory=lambda: f"heur_{uuid.uuid4().hex[:8]}")
    domain: str
    rule_pattern: str
    confidence_weight: float = 0.85  # 0.0 - 1.0
    observation_count: int = 1
    last_updated: float = Field(default_factory=time.time)


class StrategyReflector:
    """Maintains a persistent, evolving repository of self-directed strategy heuristics."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self, evaluator: Optional[MetacognitiveEvaluator] = None) -> None:
        self._evaluator = evaluator or metacognitive_evaluator
        self._heuristics: Dict[str, StrategyHeuristic] = {}
        self._init_default_heuristics()

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Strategy reflector halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: strategy reflection involving payments is strictly prohibited. Found: {text}"
            )

    def _init_default_heuristics(self) -> None:
        """Seed initial verified planning heuristics."""
        self.record_heuristic(
            domain="DAG_DECOMPOSITION",
            rule_pattern="Always inject an initial inspection/prerequisite node before heavy state synthesis.",
            initial_confidence=0.95,
        )
        self.record_heuristic(
            domain="SANDBOX_ISOLATION",
            rule_pattern="When encountering permission denied on write ops, isolate step in restricted sandbox jail.",
            initial_confidence=0.92,
        )
        self.record_heuristic(
            domain="SLA_VERIFICATION",
            rule_pattern="Terminal leaf action in every subtask tier must assert Guardian SLA < 25.0ms halt latency.",
            initial_confidence=0.98,
        )

    def record_heuristic(
        self,
        domain: str,
        rule_pattern: str,
        initial_confidence: float = 0.85,
    ) -> StrategyHeuristic:
        """Records a new meta-heuristic or reinforces existing heuristic confidence upon observation."""
        self._check_guardian()
        self._validate_rule_8(domain)
        self._validate_rule_8(rule_pattern)

        # Check for existing rule pattern in same domain
        for h in self._heuristics.values():
            if h.domain.lower() == domain.lower() and h.rule_pattern.lower() == rule_pattern.lower():
                h.observation_count += 1
                # Bayesian confidence reinforcement
                h.confidence_weight = min(0.99, round(h.confidence_weight + 0.02, 3))
                h.last_updated = time.time()
                return h

        heuristic = StrategyHeuristic(
            domain=domain.upper(),
            rule_pattern=rule_pattern,
            confidence_weight=round(initial_confidence, 3),
            observation_count=1,
        )
        self._heuristics[heuristic.heuristic_id] = heuristic
        return heuristic

    def reflect_on_plan_efficiency(self, target_id: str) -> Dict[str, Any]:
        """Synthesizes high-level reflective strategic advice combining metacognitive report and matching heuristics."""
        self._check_guardian()
        self._validate_rule_8(target_id)

        report: MetacognitiveReport = self._evaluator.evaluate_plan(target_id)
        relevant_heuristics = list(self._heuristics.values())[:3]

        recommendations: List[str] = []
        if report.cognitive_drift_score > 0.15:
            recommendations.append("Apply tighter prerequisite gating to counter growing cognitive drift.")
        if report.reasoning_efficiency < 0.80:
            recommendations.append("Consider pruning speculative branches earlier or pre-allocating compensatory fallbacks.")
        if not recommendations:
            recommendations.append("Execution trajectory meets nominal convergence and efficiency criteria.")

        return {
            "target_id": target_id,
            "report_id": report.report_id,
            "reasoning_efficiency": report.reasoning_efficiency,
            "cognitive_drift_score": report.cognitive_drift_score,
            "hallucination_risk_score": report.hallucination_risk_score,
            "convergence_rate": report.convergence_rate,
            "strategic_recommendations": recommendations,
            "matched_heuristics": [h.model_dump() for h in relevant_heuristics],
        }

    def list_heuristics(self, domain: Optional[str] = None) -> List[StrategyHeuristic]:
        self._check_guardian()
        if domain:
            self._validate_rule_8(domain)
            return [h for h in self._heuristics.values() if h.domain == domain.upper()]
        return list(self._heuristics.values())


# Global singleton instance
strategy_reflector = StrategyReflector()
