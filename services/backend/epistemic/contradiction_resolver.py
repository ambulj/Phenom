"""Contradiction Resolver for Phenom (Milestone 26 Phase 2).

Detects factual or preference contradictions against active epistemic beliefs
and calculates rational resolution strategies with confidence shifts (EPI-01.2, RES-03.1).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.epistemic.belief_network import (
    EpistemicBelief,
    EpistemicBeliefNetwork,
    epistemic_belief_network,
    Rule8ViolationError,
)

logger = logging.getLogger("phenom.epistemic.contradiction_resolver")


class ContradictionDetectionResult(BaseModel):
    conflict_detected: bool
    existing_belief: Optional[EpistemicBelief] = None
    conflicting_claim: Optional[str] = None
    resolution_strategy: str  # NO_CONFLICT, OVERWRITE_WITH_USER_CORRECTION, CONFIDENCE_DEGRADATION
    confidence_shift: float = 0.0
    explanation: str


class ContradictionResolver:
    """Detects and resolves epistemic contradictions between new statements and existing beliefs."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self, network: Optional[Any] = None) -> None:
        self._network = network or epistemic_belief_network

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Contradiction resolver halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: contradiction resolution involving payments is strictly prohibited. Found: {text}"
            )

    def analyze_claim(
        self,
        subject: str,
        predicate: str,
        claimed_value: str,
        is_user_direct: bool = True,
    ) -> ContradictionDetectionResult:
        """Analyze if a new claim contradicts an existing belief and determine resolution."""
        self._check_guardian()
        self._validate_rule_8(subject)
        self._validate_rule_8(predicate)
        self._validate_rule_8(claimed_value)

        key = f"{subject}::{predicate}".lower()
        beliefs = {f"{b.subject}::{b.predicate}".lower(): b for b in self._network.get_beliefs()}

        if key not in beliefs:
            return ContradictionDetectionResult(
                conflict_detected=False,
                resolution_strategy="NO_CONFLICT",
                explanation=f"No prior belief exists for '{subject} {predicate}'. New belief can be asserted safely.",
            )

        existing = beliefs[key]
        if existing.object_value.lower() == claimed_value.lower():
            return ContradictionDetectionResult(
                conflict_detected=False,
                existing_belief=existing,
                resolution_strategy="NO_CONFLICT",
                explanation=f"Claim matches existing belief '{existing.object_value}'. Confidence can be reinforced.",
            )

        # Contradiction detected!
        if is_user_direct:
            strategy = "OVERWRITE_WITH_USER_CORRECTION"
            shift = round(0.95 - existing.confidence, 3)
            expl = (
                f"Contradiction detected: Current belief is '{existing.object_value}' (conf: {existing.confidence}), "
                f"but direct user correction asserts '{claimed_value}'. User authority supersedes prior belief."
            )
        else:
            strategy = "CONFIDENCE_DEGRADATION"
            shift = -0.25
            expl = (
                f"Contradiction detected from indirect source. Existing belief '{existing.object_value}' "
                f"confidence degraded by 0.25 pending user clarification."
            )

        return ContradictionDetectionResult(
            conflict_detected=True,
            existing_belief=existing,
            conflicting_claim=claimed_value,
            resolution_strategy=strategy,
            confidence_shift=shift,
            explanation=expl,
        )

    def resolve_and_apply(
        self,
        subject: str,
        predicate: str,
        claimed_value: str,
        is_user_direct: bool = True,
    ) -> EpistemicBelief:
        """Analyze contradiction and apply resolution directly to the network."""
        self._check_guardian()
        analysis = self.analyze_claim(subject, predicate, claimed_value, is_user_direct=is_user_direct)

        if not analysis.conflict_detected:
            # Confirm or add
            return self._network.update_belief(
                subject=subject,
                predicate=predicate,
                object_value=claimed_value,
                source="USER_STATEMENT" if is_user_direct else "INFERRED",
                reason="Belief confirmation",
            )

        if analysis.resolution_strategy == "OVERWRITE_WITH_USER_CORRECTION":
            return self._network.update_belief(
                subject=subject,
                predicate=predicate,
                object_value=claimed_value,
                confidence_boost=0.95,
                source="USER_STATEMENT",
                reason=analysis.explanation,
            )
        else:
            # Degrade existing
            existing = analysis.existing_belief
            if existing:
                existing.confidence = max(0.20, existing.confidence + analysis.confidence_shift)
                return existing
            return self._network.update_belief(subject, predicate, claimed_value)


# Singleton instance
contradiction_resolver = ContradictionResolver()
