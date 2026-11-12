"""Attentional Pacer for Phenom (Milestone 26 Phase 4).

Paces ambient notifications and proactive interventions to prevent disrupting
the user during high cognitive load (COG-03.2, PAC-01.1).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.pacing.cognitive_load_tracker import (
    CognitiveLoadTracker,
    cognitive_load_tracker,
    Rule8ViolationError,
)

logger = logging.getLogger("phenom.pacing.attentional_pacer")


class PacedNotification(BaseModel):
    notification_id: str
    title: str
    body: str
    priority: str = "STANDARD_PROACTIVE"  # CRITICAL_SAFETY, STANDARD_PROACTIVE, LOW_AMBIENT
    created_at: float = Field(default_factory=time.time)


class PacingDecision(BaseModel):
    decision: str  # DISPATCH_IMMEDIATELY, DEFERRED_TO_QUEUE
    target_notification: PacedNotification
    user_attentional_state: str
    cognitive_load_score: float
    rationale: str


class AttentionalPacer:
    """Manages paced delivery of notifications against user cognitive bandwidth."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self, tracker: Optional[CognitiveLoadTracker] = None) -> None:
        self._tracker = tracker or cognitive_load_tracker
        self._deferred_queue: List[PacedNotification] = []

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Attentional pacer halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: notification pacing involving payments is strictly prohibited. Found: {text}"
            )

    def evaluate_and_pace(
        self,
        title: str,
        body: str,
        priority: str = "STANDARD_PROACTIVE",
    ) -> PacingDecision:
        """Determines whether a notification should be delivered now or queued."""
        self._check_guardian()
        self._validate_rule_8(title)
        self._validate_rule_8(body)
        self._validate_rule_8(priority)

        notif = PacedNotification(
            notification_id=f"notif_{int(time.time() * 1000) % 1000000}",
            title=title,
            body=body,
            priority=priority,
        )

        # Invariant: Critical safety notifications always punch through
        if priority.upper() == "CRITICAL_SAFETY":
            return PacingDecision(
                decision="DISPATCH_IMMEDIATELY",
                target_notification=notif,
                user_attentional_state="OVERRIDE",
                cognitive_load_score=1.0,
                rationale="Critical safety alerts bypass cognitive pacing (Rule 1 / Rule 3 invariant).",
            )

        cog_state = self._tracker.get_state()

        if cog_state.attentional_state == "DEEP_FLOW":
            self._deferred_queue.append(notif)
            return PacingDecision(
                decision="DEFERRED_TO_QUEUE",
                target_notification=notif,
                user_attentional_state=cog_state.attentional_state,
                cognitive_load_score=cog_state.cognitive_load_score,
                rationale=f"User in {cog_state.attentional_state} (load: {cog_state.cognitive_load_score}). Notification queued to avoid distraction.",
            )
        else:
            return PacingDecision(
                decision="DISPATCH_IMMEDIATELY",
                target_notification=notif,
                user_attentional_state=cog_state.attentional_state,
                cognitive_load_score=cog_state.cognitive_load_score,
                rationale=f"User in {cog_state.attentional_state} (load: {cog_state.cognitive_load_score}). Ambient dispatch approved.",
            )

    def get_deferred_queue(self) -> List[PacedNotification]:
        """Returns list of currently queued notifications."""
        self._check_guardian()
        return list(self._deferred_queue)

    def flush_deferred_queue(self) -> List[PacedNotification]:
        """Flushes and returns all deferred notifications for delivery."""
        self._check_guardian()
        flushed = list(self._deferred_queue)
        self._deferred_queue.clear()
        return flushed


# Global singleton instance
attentional_pacer = AttentionalPacer()
