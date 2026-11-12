"""Semantic Grounding Engine for Phenom (Milestone 25 Phase 1).

Matches natural language directives and visual queries to concrete screen bounding boxes
and target click coordinates with role-based and spatial semantic disambiguation (ACT-01.2, VIS-04.1).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.grounding.visual_segmenter import (
    SegmentedUIElement,
    visual_segmenter,
    Rule8ViolationError,
)

logger = logging.getLogger("phenom.grounding.semantic_grounding_engine")


class SemanticGroundingMatch(BaseModel):
    query: str
    matched_element: SegmentedUIElement
    target_coordinates: Tuple[int, int]  # (center_x, center_y)
    match_score: float  # 0.0 to 1.0
    match_reason: str
    latency_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticGroundingEngine:
    """Grounds user intent into concrete GUI element targets and spatial click anchors."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing|stripe|paypal)\b",
        re.IGNORECASE,
    )

    ROLE_KEYWORDS: Dict[str, List[str]] = {
        "BUTTON": ["button", "btn", "click", "press", "submit", "save", "run", "close"],
        "INPUT": ["input", "textbox", "field", "search", "query", "type", "enter", "prompt"],
        "MENU_ITEM": ["menu", "item", "dropdown", "select", "file", "edit", "view"],
        "ICON": ["icon", "gear", "settings", "close", "minimize", "maximize"],
        "TEXT_BLOCK": ["text", "label", "heading", "status", "message"],
    }

    def __init__(self, segmenter: Optional[Any] = None) -> None:
        self._segmenter = segmenter or visual_segmenter

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Semantic grounding halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: grounding queries targeting payments or checkouts are strictly prohibited. Found: {text}"
            )

    def ground_query(
        self,
        query: str,
        screen_metadata: Optional[Dict[str, Any]] = None,
        candidate_elements: Optional[List[SegmentedUIElement]] = None,
    ) -> SemanticGroundingMatch:
        """Ground a natural language query to the best-matching on-screen UI element."""
        t0 = time.perf_counter()
        self._check_guardian()
        self._validate_rule_8(query)

        elements = candidate_elements or self._segmenter.segment_screen(screen_metadata)
        if not elements:
            raise ValueError("No UI elements detected on active screen.")

        q_lower = query.lower()
        q_tokens = set(re.findall(r"\w+", q_lower))

        # Check expected role affinities from query
        favored_roles: List[str] = []
        for role, keywords in self.ROLE_KEYWORDS.items():
            if any(kw in q_tokens for kw in keywords):
                favored_roles.append(role)

        # Detect spatial directional cues in query
        prefer_top = "top" in q_tokens or "upper" in q_tokens
        prefer_bottom = "bottom" in q_tokens or "lower" in q_tokens
        prefer_left = "left" in q_tokens
        prefer_right = "right" in q_tokens

        best_element: Optional[SegmentedUIElement] = None
        best_score = -1.0
        best_reason = ""

        screen_w = 1920
        screen_h = 1080

        for elem in elements:
            score = 0.0
            reasons = []

            # 1. Label token match
            elem_tokens = set(re.findall(r"\w+", elem.label.lower()))
            overlap = q_tokens.intersection(elem_tokens)
            if overlap:
                overlap_ratio = len(overlap) / max(1, len(elem_tokens))
                score += overlap_ratio * 0.60
                reasons.append(f"matched label tokens ({', '.join(overlap)})")

            # Exact substring match bonus
            if elem.label.lower() in q_lower or any(token in elem.label.lower() for token in q_tokens if len(token) > 3):
                score += 0.25
                reasons.append("substring match")

            # 2. Role alignment
            if elem.role in favored_roles:
                score += 0.20
                reasons.append(f"role '{elem.role}' matches intent")

            # 3. Spatial alignment
            cx = elem.bounding_box.center_x
            cy = elem.bounding_box.center_y

            if prefer_top:
                if cy < screen_h * 0.4:
                    score += 0.25
                    reasons.append("spatial: top region match")
                elif cy > screen_h * 0.6:
                    score -= 0.35
                    reasons.append("spatial: penalty not top")

            if prefer_bottom:
                if cy > screen_h * 0.6:
                    score += 0.25
                    reasons.append("spatial: bottom region match")
                elif cy < screen_h * 0.4:
                    score -= 0.35
                    reasons.append("spatial: penalty not bottom")

            if prefer_left:
                if cx < screen_w * 0.4:
                    score += 0.25
                    reasons.append("spatial: left region match")
                elif cx > screen_w * 0.6:
                    score -= 0.35
                    reasons.append("spatial: penalty not left")

            if prefer_right:
                if cx > screen_w * 0.6:
                    score += 0.25
                    reasons.append("spatial: right region match")
                elif cx < screen_w * 0.4:
                    score -= 0.35
                    reasons.append("spatial: penalty not right")

            # 4. Interactive bonus for action verbs
            if elem.is_interactive and any(v in q_tokens for v in ["click", "press", "type", "open", "find"]):
                score += 0.10

            if score > best_score:
                best_score = score
                best_element = elem
                best_reason = "; ".join(reasons) if reasons else "default fallback target"

        if best_element is None:
            best_element = elements[0]
            best_score = 0.50
            best_reason = "fallback to primary root element"

        latency_ms = (time.perf_counter() - t0) * 1000.0

        # Normalized confidence capped at 0.99
        normalized_score = min(0.99, max(0.40, best_score))

        return SemanticGroundingMatch(
            query=query,
            matched_element=best_element,
            target_coordinates=(
                best_element.bounding_box.center_x,
                best_element.bounding_box.center_y,
            ),
            match_score=round(normalized_score, 2),
            match_reason=best_reason,
            latency_ms=round(latency_ms, 3),
            metadata={
                "candidate_count": len(elements),
                "is_interactive": best_element.is_interactive,
            },
        )


# Singleton instance
semantic_grounding_engine = SemanticGroundingEngine()
