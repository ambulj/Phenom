"""Epistemic Belief Network for Phenom (Milestone 26 Phase 2).

Maintains a Bayesian-style epistemic belief network over user preferences, project facts,
and system conventions with revision histories and confidence tracking (EPI-01.1).
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.epistemic.belief_network")


class Rule8ViolationError(Exception):
    """Raised when an epistemic belief involves checkout, payment, or banking automation."""
    pass


class EpistemicBelief(BaseModel):
    belief_id: str = Field(default_factory=lambda: f"bel_{uuid.uuid4().hex[:8]}")
    subject: str
    predicate: str
    object_value: str
    confidence: float = 0.80  # 0.0 to 1.0
    prior_confidence: float = 0.50
    evidence_count: int = 1
    source: str = "INFERRED"  # USER_STATEMENT, INFERRED, DEFAULT_ASSUMPTION
    is_active: bool = True
    updated_at: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BeliefRevisionRecord(BaseModel):
    revision_id: str = Field(default_factory=lambda: f"rev_{uuid.uuid4().hex[:8]}")
    belief_id: str
    old_value: str
    new_value: str
    confidence_delta: float
    reason: str
    timestamp: float = Field(default_factory=time.time)


class EpistemicBeliefNetwork:
    """Manages active propositions, confidence updates, and belief revision records."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    INITIAL_PRESETS: List[Dict[str, Any]] = [
        {
            "subject": "User",
            "predicate": "prefers_theme",
            "object_value": "Dark Cyberpunk Glow",
            "confidence": 0.95,
            "source": "DEFAULT_ASSUMPTION",
        },
        {
            "subject": "Backend",
            "predicate": "uses_framework",
            "object_value": "FastAPI + WebSocket",
            "confidence": 0.99,
            "source": "DEFAULT_ASSUMPTION",
        },
        {
            "subject": "Safety",
            "predicate": "enforces_kill_switch_sla",
            "object_value": "< 25.0ms",
            "confidence": 1.0,
            "source": "DEFAULT_ASSUMPTION",
        },
    ]

    def __init__(self) -> None:
        self._beliefs: Dict[str, EpistemicBelief] = {}
        self._revisions: List[BeliefRevisionRecord] = []
        self._init_presets()

    def _init_presets(self) -> None:
        for p in self.INITIAL_PRESETS:
            key = f"{p['subject']}::{p['predicate']}".lower()
            self._beliefs[key] = EpistemicBelief(
                subject=p["subject"],
                predicate=p["predicate"],
                object_value=p["object_value"],
                confidence=p["confidence"],
                source=p["source"],
            )

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Epistemic belief network halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: belief proposition involving payments is strictly prohibited. Found: {text}"
            )

    def update_belief(
        self,
        subject: str,
        predicate: str,
        object_value: str,
        confidence_boost: float = 0.15,
        source: str = "USER_STATEMENT",
        reason: str = "Direct user interaction",
    ) -> EpistemicBelief:
        """Update an existing belief or assert a new proposition with Bayesian adjustment."""
        self._check_guardian()
        self._validate_rule_8(subject)
        self._validate_rule_8(predicate)
        self._validate_rule_8(object_value)

        key = f"{subject}::{predicate}".lower()
        now = time.time()

        if key in self._beliefs:
            existing = self._beliefs[key]
            old_val = existing.object_value
            old_conf = existing.confidence

            # If object value changes, record revision
            if old_val != object_value:
                # Value revision
                new_conf = min(0.99, max(0.60, confidence_boost if source == "USER_STATEMENT" else 0.70))
                delta = round(new_conf - old_conf, 3)
                existing.object_value = object_value
                existing.prior_confidence = old_conf
                existing.confidence = new_conf
                existing.source = source
                existing.evidence_count += 1
                existing.updated_at = now

                rev = BeliefRevisionRecord(
                    belief_id=existing.belief_id,
                    old_value=old_val,
                    new_value=object_value,
                    confidence_delta=delta,
                    reason=reason,
                    timestamp=now,
                )
                self._revisions.insert(0, rev)
                return existing
            else:
                # Value confirmed, reinforce confidence
                new_conf = min(0.99, existing.confidence + (1.0 - existing.confidence) * confidence_boost)
                existing.prior_confidence = existing.confidence
                existing.confidence = round(new_conf, 3)
                existing.evidence_count += 1
                existing.updated_at = now
                return existing
        else:
            # New belief
            conf = min(0.99, max(0.50, confidence_boost))
            belief = EpistemicBelief(
                subject=subject,
                predicate=predicate,
                object_value=object_value,
                confidence=round(conf, 3),
                source=source,
                updated_at=now,
            )
            self._beliefs[key] = belief
            return belief

    def get_beliefs(self, active_only: bool = True) -> List[EpistemicBelief]:
        """Query stored epistemic beliefs."""
        self._check_guardian()
        if active_only:
            return [b for b in self._beliefs.values() if b.is_active]
        return list(self._beliefs.values())

    def get_revisions(self) -> List[BeliefRevisionRecord]:
        """Query revision history log."""
        self._check_guardian()
        return list(self._revisions)


# Singleton instance
epistemic_belief_network = EpistemicBeliefNetwork()
