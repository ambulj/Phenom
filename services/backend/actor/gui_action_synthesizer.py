"""Declarative GUI Action Synthesizer for Phenom (Milestone 25 Phase 2).

Deconstructs natural language desktop instructions into validated multi-step GUI interaction
plans with grounded coordinates and safety tier classifications (ACT-02.1, EXEC-03.1).
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.grounding.semantic_grounding_engine import (
    semantic_grounding_engine,
    SemanticGroundingEngine,
)

logger = logging.getLogger("phenom.actor.gui_action_synthesizer")


class Rule8ViolationError(Exception):
    """Raised when an action plan targets payment, checkout, or automated billing."""
    pass


class GuiActionStep(BaseModel):
    step_id: int
    action_type: str  # CLICK, DOUBLE_CLICK, RIGHT_CLICK, TYPE_TEXT, KEY_SHORTCUT, SCROLL, HOVER
    target_query: Optional[str] = None
    target_coordinates: Optional[Tuple[int, int]] = None  # (x, y)
    text_payload: Optional[str] = None
    key_combination: Optional[str] = None
    description: str
    is_destructive: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GuiActionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    user_goal: str
    steps: List[GuiActionStep]
    estimated_duration_ms: float
    safety_tier: int = 1
    requires_confirmation: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GuiActionSynthesizer:
    """Translates user goals into sequential declarative GUI action step plans."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing|stripe|paypal)\b",
        re.IGNORECASE,
    )

    def __init__(self, grounding_engine: Optional[Any] = None) -> None:
        self._grounding_engine = grounding_engine or semantic_grounding_engine

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. GUI action synthesis halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: action plan targeting payments or checkout is strictly prohibited. Found: {text}"
            )

    def synthesize_plan(self, user_goal: str) -> GuiActionPlan:
        """Synthesizes a multi-step GUI action plan from user intent."""
        self._check_guardian()
        self._validate_rule_8(user_goal)

        goal_lower = user_goal.lower()
        steps: List[GuiActionStep] = []

        # 1. Search file and open
        if "search" in goal_lower and ("open" in goal_lower or "file" in goal_lower):
            m_search = self._grounding_engine.ground_query("search bar")
            steps.append(
                GuiActionStep(
                    step_id=1,
                    action_type="CLICK",
                    target_query="search bar",
                    target_coordinates=m_search.target_coordinates,
                    description=f"Click search bar at {m_search.target_coordinates}",
                )
            )
            # Extract possible query token
            tokens = [t for t in re.findall(r"\w+\.\w+|\w+", user_goal) if t.lower() not in ["search", "for", "in", "the", "editor", "and", "open", "it"]]
            search_query = tokens[0] if tokens else "main.py"
            self._validate_rule_8(search_query)

            steps.append(
                GuiActionStep(
                    step_id=2,
                    action_type="TYPE_TEXT",
                    text_payload=search_query,
                    description=f"Type search text '{search_query}'",
                )
            )
            steps.append(
                GuiActionStep(
                    step_id=3,
                    action_type="KEY_SHORTCUT",
                    key_combination="Enter",
                    description="Press Enter to open matched search result",
                )
            )

        # 2. Save file and run tests
        elif "save" in goal_lower and "test" in goal_lower:
            m_save = self._grounding_engine.ground_query("save changes button")
            steps.append(
                GuiActionStep(
                    step_id=1,
                    action_type="CLICK",
                    target_query="save changes button",
                    target_coordinates=m_save.target_coordinates,
                    description=f"Click save changes button at {m_save.target_coordinates}",
                )
            )
            m_run = self._grounding_engine.ground_query("run tests button")
            steps.append(
                GuiActionStep(
                    step_id=2,
                    action_type="CLICK",
                    target_query="run tests button",
                    target_coordinates=m_run.target_coordinates,
                    description=f"Click run tests button at {m_run.target_coordinates}",
                )
            )

        # 3. Open settings and toggle
        elif "settings" in goal_lower:
            m_gear = self._grounding_engine.ground_query("settings gear icon")
            steps.append(
                GuiActionStep(
                    step_id=1,
                    action_type="CLICK",
                    target_query="settings gear icon",
                    target_coordinates=m_gear.target_coordinates,
                    description=f"Click settings gear at {m_gear.target_coordinates}",
                )
            )
            steps.append(
                GuiActionStep(
                    step_id=2,
                    action_type="KEY_SHORTCUT",
                    key_combination="Ctrl+,",
                    description="Open Preferences shortcut",
                )
            )

        # 4. Generic single-click or action fallback
        else:
            m_generic = self._grounding_engine.ground_query(user_goal)
            steps.append(
                GuiActionStep(
                    step_id=1,
                    action_type="CLICK",
                    target_query=user_goal,
                    target_coordinates=m_generic.target_coordinates,
                    description=f"Click grounded element '{m_generic.matched_element.label}' at {m_generic.target_coordinates}",
                )
            )

        estimated_duration = len(steps) * 350.0  # 350ms per step

        return GuiActionPlan(
            user_goal=user_goal,
            steps=steps,
            estimated_duration_ms=estimated_duration,
            safety_tier=1,
            requires_confirmation=True,
            metadata={"step_count": len(steps)},
        )


# Singleton instance
gui_action_synthesizer = GuiActionSynthesizer()
