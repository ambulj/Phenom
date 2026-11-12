"""Cognitive Load Tracker for Phenom (Milestone 26 Phase 4).

Tracks real-time user interaction velocity, window dwell times, and attentional states
to quantify current cognitive load (COG-03.1).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.pacing.cognitive_load")


class Rule8ViolationError(Exception):
    """Raised when cognitive load monitoring encounters payment or checkout strings."""
    pass


class CognitiveStateReport(BaseModel):
    cognitive_load_score: float = Field(..., ge=0.0, le=1.0)
    attentional_state: str  # DEEP_FLOW, NORMAL_WORK, IDLE_EXPLORING, FATIGUE_OVERLOAD
    interaction_rate_per_min: float
    window_switches_per_min: float
    current_focus_dwell_seconds: float
    updated_at: float = Field(default_factory=time.time)


class CognitiveLoadTracker:
    """Calculates real-time user cognitive load and attentional focus states."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._interaction_timestamps: List[float] = []
        self._window_switch_timestamps: List[float] = []
        self._focus_start_time: float = time.time()
        self._current_window: str = "Phenom Cyber Desktop"

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Cognitive load tracker halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: cognitive load tracking involving payments is strictly prohibited. Found: {text}"
            )

    def record_interaction(self, event_type: str = "KEYSTROKE", window_title: Optional[str] = None) -> None:
        """Records a user physical interaction event (keystroke, click, scroll)."""
        self._check_guardian()
        self._validate_rule_8(event_type)
        if window_title:
            self._validate_rule_8(window_title)

        now = time.time()
        self._interaction_timestamps.append(now)

        # Window switch tracking
        if window_title and window_title != self._current_window:
            self._current_window = window_title
            self._window_switch_timestamps.append(now)
            self._focus_start_time = now

        self._prune_old_events(now)

    def _prune_old_events(self, now: float) -> None:
        cutoff = now - 60.0
        self._interaction_timestamps = [t for t in self._interaction_timestamps if t >= cutoff]
        self._window_switch_timestamps = [t for t in self._window_switch_timestamps if t >= cutoff]

    def get_state(self) -> CognitiveStateReport:
        """Computes current cognitive load score and classification."""
        self._check_guardian()
        now = time.time()
        self._prune_old_events(now)

        interaction_rate = len(self._interaction_timestamps)
        window_switches = len(self._window_switch_timestamps)
        dwell = max(0.0, round(now - self._focus_start_time, 1))

        # Velocity heuristic: 0 - 60+ interactions/min normalized
        raw_velocity_score = min(1.0, interaction_rate / 50.0)
        # Switching penalty (frequent switches increase turbulence)
        switch_penalty = min(0.3, window_switches * 0.05)

        load_score = min(1.0, round(raw_velocity_score * 0.75 + switch_penalty, 2))

        if load_score >= 0.75:
            state = "DEEP_FLOW"
        elif load_score >= 0.35:
            state = "NORMAL_WORK"
        else:
            state = "IDLE_EXPLORING"

        return CognitiveStateReport(
            cognitive_load_score=load_score,
            attentional_state=state,
            interaction_rate_per_min=float(interaction_rate),
            window_switches_per_min=float(window_switches),
            current_focus_dwell_seconds=dwell,
            updated_at=now,
        )


# Global singleton instance
cognitive_load_tracker = CognitiveLoadTracker()
