"""Adaptive Throttler for Phenom (Milestone 24 Phase 4).

Dynamically balances heterogeneous subagent worker concurrency, background indexing tasks,
and LLM context window allocations based on real-time resource telemetry (GOV-03.2, RES-02.1).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.governor.resource_governor import resource_governor

logger = logging.getLogger("phenom.governor.adaptive_throttler")


class Rule8ViolationError(Exception):
    """Raised when an operation involves payment, checkout, or automated financial transactions."""
    pass


class ThrottleConfiguration(BaseModel):
    state: str  # NORMAL, CONSERVE, EMERGENCY_THROTTLE
    max_concurrency: int
    background_indexing_paused: bool
    context_window_cap: int
    vram_headroom_mb: float
    manual_override: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AdaptiveThrottler:
    """Dynamic concurrency allocator and system workload throttler."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing|stripe|paypal)\b",
        re.IGNORECASE,
    )

    STATE_POLICIES: Dict[str, Dict[str, Any]] = {
        "NORMAL": {
            "max_concurrency": 4,
            "background_indexing_paused": False,
            "context_window_cap": 8192,
            "vram_headroom_mb": 1024.0,
        },
        "CONSERVE": {
            "max_concurrency": 2,
            "background_indexing_paused": False,
            "context_window_cap": 4096,
            "vram_headroom_mb": 1536.0,
        },
        "EMERGENCY_THROTTLE": {
            "max_concurrency": 1,
            "background_indexing_paused": True,
            "context_window_cap": 2048,
            "vram_headroom_mb": 2048.0,
        },
    }

    def __init__(self, governor: Optional[Any] = None) -> None:
        self._governor = governor or resource_governor
        self._current_config = ThrottleConfiguration(
            state="NORMAL",
            max_concurrency=4,
            background_indexing_paused=False,
            context_window_cap=8192,
            vram_headroom_mb=1024.0,
            manual_override=False,
        )

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Adaptive throttler operations halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: throttle parameters involving payments or checkout are strictly prohibited. Found: {text}"
            )

    def sync_throttle_state(
        self,
        force_state: Optional[str] = None,
        manual: bool = False,
    ) -> ThrottleConfiguration:
        """Synchronize throttling state against telemetry or manual override."""
        self._check_guardian()

        if force_state:
            self._validate_rule_8(force_state)
            target_state = force_state.upper()
        elif self._current_config.manual_override and not manual:
            target_state = self._current_config.state
        else:
            telem = self._governor.sample_telemetry()
            target_state = telem.throttle_state

        if target_state not in self.STATE_POLICIES:
            target_state = "NORMAL"

        policy = self.STATE_POLICIES[target_state]
        self._current_config = ThrottleConfiguration(
            state=target_state,
            max_concurrency=policy["max_concurrency"],
            background_indexing_paused=policy["background_indexing_paused"],
            context_window_cap=policy["context_window_cap"],
            vram_headroom_mb=policy["vram_headroom_mb"],
            manual_override=manual,
        )
        return self._current_config

    def override_headroom(self, vram_headroom_mb: float) -> ThrottleConfiguration:
        """Apply custom VRAM safety headroom bound."""
        self._check_guardian()
        self._current_config.vram_headroom_mb = max(256.0, float(vram_headroom_mb))
        self._current_config.manual_override = True
        return self._current_config

    def reset_override(self) -> ThrottleConfiguration:
        """Reset manual overrides and resume automatic telemetry-driven throttling."""
        self._check_guardian()
        return self.sync_throttle_state(manual=False)

    def get_active_config(self) -> ThrottleConfiguration:
        """Retrieve active throttling parameters."""
        self._check_guardian()
        return self._current_config


# Singleton instance
adaptive_throttler = AdaptiveThrottler()
