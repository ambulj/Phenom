"""Task Anticipation Engine for Phenom (Milestone 23 Phase 4).

Implements statistical Markov transition chains over user habit sequences to anticipate
the next workflow action, compute conditional transition probabilities, and surface
proactive one-click action cards.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.proactive.task_anticipation")


class Rule8ViolationError(Exception):
    """Raised when an action involves payment, checkout, or automated financial transactions."""
    pass


class AnticipatedAction(BaseModel):
    action_id: str
    target_action: str
    source_action: Optional[str] = None
    probability: float
    confidence_level: str  # HIGH, MEDIUM, LOW
    reason: str
    prewarmed: bool = False
    dismissed: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskAnticipationEngine:
    """Statistical Markov transition chain engine for user workflow anticipation."""

    # Rule 8 payment regex pattern
    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing|stripe|paypal)\b",
        re.IGNORECASE,
    )

    # Rule 11 credential scrubbing patterns
    _CREDENTIAL_PATTERNS = [
        (re.compile(r"(ghp_[a-zA-Z0-9]{20,})"), "[SCRUBBED_GITHUB_TOKEN]"),
        (re.compile(r"(sk-[a-zA-Z0-9]{20,})"), "[SCRUBBED_API_KEY]"),
        (re.compile(r"(Bearer\s+[a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE), "Bearer [SCRUBBED_TOKEN]"),
        (re.compile(r"(password\s*[:=]\s*['\"][^'\"]+['\"])", re.IGNORECASE), 'password: "[SCRUBBED_PASSWORD]"'),
    ]

    def __init__(self, persistence_dir: Optional[str] = None) -> None:
        self.persistence_dir = Path(persistence_dir) if persistence_dir else Path(".phenom/habits")
        self.persistence_path = self.persistence_dir / "habit_transitions.json"
        # transitions[source_action][target_action] = count
        self.transitions: Dict[str, Dict[str, int]] = {}
        # action totals
        self.action_counts: Dict[str, int] = {}
        self.dismissed_actions: set[str] = set()
        self._load_habits()

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Anticipation operations halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: checkout, payments, and financial execution are strictly prohibited. Found in: {text}"
            )

    def _scrub_credentials(self, text: str) -> str:
        scrubbed = text
        for pattern, replacement in self._CREDENTIAL_PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed

    def record_transition(
        self,
        source_action: str,
        target_action: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a sequential transition between two workflow actions."""
        self._check_guardian()
        self._validate_rule_8(source_action)
        self._validate_rule_8(target_action)

        scrubbed_source = self._scrub_credentials(source_action.strip())
        scrubbed_target = self._scrub_credentials(target_action.strip())

        if scrubbed_source not in self.transitions:
            self.transitions[scrubbed_source] = {}
        self.transitions[scrubbed_source][scrubbed_target] = (
            self.transitions[scrubbed_source].get(scrubbed_target, 0) + 1
        )

        self.action_counts[scrubbed_source] = self.action_counts.get(scrubbed_source, 0) + 1
        self.action_counts[scrubbed_target] = self.action_counts.get(scrubbed_target, 0) + 1

        self._save_habits()

        total_from_source = sum(self.transitions[scrubbed_source].values())
        prob = self.transitions[scrubbed_source][scrubbed_target] / total_from_source

        return {
            "source_action": scrubbed_source,
            "target_action": scrubbed_target,
            "transition_count": self.transitions[scrubbed_source][scrubbed_target],
            "total_source_occurrences": total_from_source,
            "conditional_probability": round(prob, 4),
        }

    def predict_next_actions(
        self,
        current_action: Optional[str] = None,
        threshold: float = 0.40,
        limit: int = 5,
    ) -> List[AnticipatedAction]:
        """Predict the next anticipated actions given current workflow action."""
        self._check_guardian()
        if current_action:
            self._validate_rule_8(current_action)
            current_action = self._scrub_credentials(current_action.strip())

        predictions: List[AnticipatedAction] = []

        if current_action and current_action in self.transitions:
            source_targets = self.transitions[current_action]
            total_transitions = sum(source_targets.values())

            for target, count in source_targets.items():
                action_id = f"ant_{current_action}_{target}"
                if target in self.dismissed_actions or action_id in self.dismissed_actions:
                    continue
                prob = count / total_transitions
                if prob >= threshold:
                    confidence = "HIGH" if prob >= 0.70 else ("MEDIUM" if prob >= 0.50 else "LOW")
                    predictions.append(
                        AnticipatedAction(
                            action_id=action_id,
                            target_action=target,
                            source_action=current_action,
                            probability=round(prob, 4),
                            confidence_level=confidence,
                            reason=f"P({target} | {current_action}) = {prob*100:.1f}% based on {count}/{total_transitions} sequential transitions.",
                        )
                    )
        elif not current_action and self.action_counts:
            # Fallback to marginal frequency priors across all actions
            total_actions = sum(self.action_counts.values())
            for target, count in self.action_counts.items():
                action_id = f"ant_prior_{target}"
                if target in self.dismissed_actions or action_id in self.dismissed_actions:
                    continue
                prob = count / total_actions
                if prob >= threshold:
                    confidence = "HIGH" if prob >= 0.70 else ("MEDIUM" if prob >= 0.50 else "LOW")
                    predictions.append(
                        AnticipatedAction(
                            action_id=f"ant_prior_{target}",
                            target_action=target,
                            source_action=None,
                            probability=round(prob, 4),
                            confidence_level=confidence,
                            reason=f"Marginal prior P({target}) = {prob*100:.1f}% across all historical actions.",
                        )
                    )

        # Sort by probability descending
        predictions.sort(key=lambda p: p.probability, reverse=True)
        return predictions[:limit]

    def dismiss_action_card(self, action_id: str) -> Dict[str, Any]:
        """Soft-dismiss an anticipated action card without destroying historical transitions (Rule 7)."""
        self._check_guardian()
        self.dismissed_actions.add(action_id)
        # Also parse target action if it fits standard format
        parts = action_id.split("_")
        if len(parts) >= 3:
            target = parts[-1]
            self.dismissed_actions.add(target)

        self._save_habits()
        return {
            "action_id": action_id,
            "status": "dismissed",
            "message": f"Action card '{action_id}' soft-dismissed. Transition weights preserved.",
        }

    def _save_habits(self) -> None:
        """Persist transition weights non-destructively (Rule 7)."""
        try:
            self.persistence_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "transitions": self.transitions,
                "action_counts": self.action_counts,
                "dismissed_actions": list(self.dismissed_actions),
            }
            with open(self.persistence_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not persist habit transitions: {e}")

    def _load_habits(self) -> None:
        """Load habit transitions if file exists."""
        if self.persistence_path.exists():
            try:
                with open(self.persistence_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.transitions = data.get("transitions", {})
                self.action_counts = data.get("action_counts", {})
                self.dismissed_actions = set(data.get("dismissed_actions", []))
            except Exception as e:
                logger.warning(f"Could not load habit transitions from {self.persistence_path}: {e}")


# Singleton instance
task_anticipation_engine = TaskAnticipationEngine()
