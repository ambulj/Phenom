"""Spatial Intent Resolver for Phenom (Milestone 24 Phase 3).

Correlates spoken deictic commands ('refactor this', 'explain here') with spatial cursor
coordinates and active UI/AST symbols in < 35ms (VOX-07.2, GES-01.1).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.spatial.cursor_telemetry_tracker import (
    cursor_telemetry_tracker,
    CursorSpatialContext,
)

logger = logging.getLogger("phenom.spatial.intent_resolver")


class Rule8ViolationError(Exception):
    """Raised when an intent involves payment, checkout, or automated financial transactions."""
    pass


class SpatialResolvedIntent(BaseModel):
    spoken_command: str
    action_verb: str  # refactor, explain, test, benchmark, fix, inspect
    resolved_target: str
    target_type: str  # AST_FUNCTION, AST_CLASS, UI_ELEMENT, EDITOR_BLOCK
    cursor_coords: Dict[str, int]
    bounding_box: Dict[str, int]
    resolution_latency_ms: float
    confidence: float
    is_deictic: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SpatialIntentResolver:
    """Low-latency cross-modal spatial-voice fusion and deictic intent resolver."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing|stripe|paypal)\b",
        re.IGNORECASE,
    )

    DEICTIC_TOKENS = {"this", "here", "that", "selected", "active", "current", "cursor"}

    ACTION_VERBS = {
        "refactor": "refactor",
        "rewrite": "refactor",
        "clean up": "refactor",
        "explain": "explain",
        "what is": "explain",
        "describe": "explain",
        "test": "test",
        "run tests": "test",
        "benchmark": "benchmark",
        "profile": "benchmark",
        "fix": "fix",
        "heal": "fix",
        "repair": "fix",
        "inspect": "inspect",
        "highlight": "inspect",
    }

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Spatial intent resolution halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: spatial commands involving payments or checkout are strictly prohibited. Found: {text}"
            )

    def resolve_spatial_intent(
        self,
        spoken_command: str,
        cursor_context: Optional[CursorSpatialContext] = None,
    ) -> SpatialResolvedIntent:
        """Resolve spoken deictic command to a concrete UI or AST target."""
        self._check_guardian()
        self._validate_rule_8(spoken_command)

        t0 = time.perf_counter()
        cmd_lower = spoken_command.lower()

        # 1. Detect action verb
        action_verb = "inspect"
        for phrase, verb in self.ACTION_VERBS.items():
            if phrase in cmd_lower:
                action_verb = verb
                break

        # 2. Check for deictic spatial pronouns
        words = set(re.findall(r"\b\w+\b", cmd_lower))
        is_deictic = bool(words & self.DEICTIC_TOKENS)

        # 3. Retrieve spatial context
        ctx = cursor_context or cursor_telemetry_tracker.get_cursor_context()
        if ctx.target_symbol:
            self._validate_rule_8(ctx.target_symbol)

        # 4. Bind target symbol or element
        resolved_target = ctx.target_symbol or ctx.target_element
        target_type = "AST_FUNCTION" if ctx.target_symbol else "UI_ELEMENT"
        confidence = 0.96 if is_deictic else 0.82

        # Synthesize target bounding box around cursor
        box_w = 420
        box_h = 160
        box_left = max(0, ctx.x - box_w // 2)
        box_top = max(0, ctx.y - box_h // 2)
        bounding_box = {"left": box_left, "top": box_top, "width": box_w, "height": box_h}

        duration_ms = (time.perf_counter() - t0) * 1000.0

        return SpatialResolvedIntent(
            spoken_command=spoken_command,
            action_verb=action_verb,
            resolved_target=resolved_target,
            target_type=target_type,
            cursor_coords={"x": ctx.x, "y": ctx.y},
            bounding_box=bounding_box,
            resolution_latency_ms=round(duration_ms, 3),
            confidence=confidence,
            is_deictic=is_deictic,
            metadata={"window": ctx.window_title},
        )

    def highlight_target(self, target_name: str) -> Dict[str, Any]:
        """Broadcast UI highlight beacon for a resolved target (GES-01.1)."""
        self._check_guardian()
        self._validate_rule_8(target_name)

        ctx = cursor_telemetry_tracker.get_cursor_context()
        return {
            "target_name": target_name,
            "status": "highlighted",
            "beacon_coords": {"x": ctx.x, "y": ctx.y},
            "timestamp": time.time(),
        }


# Singleton instance
spatial_intent_resolver = SpatialIntentResolver()
