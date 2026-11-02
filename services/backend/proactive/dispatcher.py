"""Proactive Event Dispatcher for Phenom.

Manages anti-fatigue cooldowns, priority tiers, DEEP_FOCUS / STUDY mode suppression,
and multimodal WebSocket notifications to Electron and Three.js Orb (DIS-01, DIS-02).
"""

from __future__ import annotations

import asyncio
from enum import IntEnum
import logging
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger(__name__)


class ProactivePriority(IntEnum):
    """Priority level for proactive events."""

    BACKGROUND = 1  # Idle housekeeping, background indexing
    NORMAL = 2      # Executive morning briefing, VIP email summaries
    URGENT = 3      # Pre-meeting alerts (< 15 min), critical security/system warnings


class ProactiveCard(BaseModel):
    """Actionable recommendation card presented to user."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = Field(..., description="Category: MEETING_PREP, MORNING_BRIEF, IDLE_CLEANUP, etc.")
    priority: ProactivePriority = Field(default=ProactivePriority.NORMAL)
    title: str = Field(..., description="Concise headline")
    description: str = Field(..., description="Actionable summary or recommendation")
    action_chip: Optional[str] = Field(default=None, description="1-click execution label (e.g. 'Review Draft')")
    action_payload: Optional[Dict[str, Any]] = Field(default=None, description="Payload executed on chip click")
    timestamp: float = Field(default_factory=time.time)
    dismissed: bool = Field(default=False)


WSBroadcastFn = Callable[[Dict[str, Any]], Awaitable[None]]


class ProactiveEventDispatcher:
    """Central event broker for proactive notifications and background triggers."""

    def __init__(
        self,
        ws_broadcast_fn: Optional[WSBroadcastFn] = None,
        default_cooldown_seconds: float = 900.0,  # 15 minutes anti-fatigue
    ) -> None:
        self.ws_broadcast_fn = ws_broadcast_fn
        self.default_cooldown_seconds = default_cooldown_seconds
        self._halted: bool = False

        self._current_mode: str = "CHILL"
        self._last_emitted_by_type: Dict[str, float] = {}
        self._cards: Dict[str, ProactiveCard] = {}
        self._cooldown_overrides: Dict[str, float] = {
            "MORNING_BRIEF": 3600.0 * 4,       # Max once every 4 hours
            "MEETING_PREP": 1800.0,            # Max once every 30 minutes
            "IDLE_CLEANUP": 3600.0 * 2,        # Max once every 2 hours
            "AMBIENT_SUGGESTION": 600.0,       # 10 minutes
        }

    @property
    def is_halted(self) -> bool:
        """Returns True if halted by Guardian or manually."""
        return self._halted or guardian.is_halted

    def reset(self) -> None:
        """Reset halted state."""
        self._halted = False

    @property
    def current_mode(self) -> str:
        """Current assistant presence mode."""
        return self._current_mode

    def set_mode(self, mode: str) -> None:
        """Update presence mode (WORK, STUDY, CHILL, DEEP_FOCUS)."""
        old_mode = self._current_mode
        self._current_mode = mode.upper()
        logger.info("ProactiveEventDispatcher mode updated: %s -> %s", old_mode, self._current_mode)

    def set_cooldown_override(self, event_type: str, seconds: float) -> None:
        """Set custom cooldown duration for a specific event type."""
        self._cooldown_overrides[event_type] = max(0.0, float(seconds))

    def get_cooldown_for_event(self, event_type: str) -> float:
        """Retrieve applicable cooldown duration in seconds."""
        return self._cooldown_overrides.get(event_type, self.default_cooldown_seconds)

    async def dispatch(self, card: ProactiveCard) -> bool:
        """Dispatch a proactive card, respecting mode quiet hours and cooldowns.

        Returns True if delivered/broadcast, False if suppressed by mode or cooldown.
        """
        if self.is_halted:
            logger.info("Proactive card '%s' suppressed: Guardian kill switch is active.", card.title)
            return False

        now = time.time()
        self._cards[card.id] = card

        # 1. Mode suppression check
        # In DEEP_FOCUS or STUDY, completely suppress non-urgent interruptions
        if self._current_mode in ("DEEP_FOCUS", "STUDY") and card.priority < ProactivePriority.URGENT:
            logger.info(
                "Proactive card '%s' (%s) queued silently due to active %s mode",
                card.title,
                card.event_type,
                self._current_mode,
            )
            return False

        # 2. Cooldown anti-fatigue check
        cooldown = self.get_cooldown_for_event(card.event_type)
        last_time = self._last_emitted_by_type.get(card.event_type, 0.0)

        # URGENT events bypass standard cooldowns
        if card.priority < ProactivePriority.URGENT and (now - last_time) < cooldown:
            logger.info(
                "Proactive card '%s' (%s) suppressed by cooldown (elapsed=%.1fs < %.1fs)",
                card.title,
                card.event_type,
                now - last_time,
                cooldown,
            )
            return False

        # Mark emission time
        self._last_emitted_by_type[card.event_type] = now

        # 3. Broadcast to Electron & Three.js Orb
        if self.ws_broadcast_fn:
            try:
                # Slide-in toast event
                await self.ws_broadcast_fn({
                    "type": "PROACTIVE_CARD",
                    "card": card.model_dump(),
                })

                # Particle orb pulse event
                pulse_color = "#CCFF00" if card.priority >= ProactivePriority.URGENT else "#0052FF"
                await self.ws_broadcast_fn({
                    "type": "PROACTIVE_ORB_PULSE",
                    "priority": int(card.priority),
                    "pulse_color": pulse_color,
                })
            except Exception as exc:
                logger.error("Failed to broadcast proactive event via WebSocket: %s", exc)

        logger.info("Dispatched proactive card '%s' [P%d]", card.title, card.priority)
        return True

    def dismiss_card(self, card_id: str) -> bool:
        """Mark a proactive card as dismissed by user."""
        if card_id in self._cards:
            self._cards[card_id].dismissed = True
            return True
        return False

    def list_active_cards(self, limit: int = 20) -> List[ProactiveCard]:
        """Return non-dismissed proactive cards ordered newest first."""
        active = [c for c in self._cards.values() if not c.dismissed]
        active.sort(key=lambda c: c.timestamp, reverse=True)
        return active[:limit]

    def halt(self) -> None:
        """Synchronous Guardian kill switch halt (< 5ms SLA)."""
        logger.info("Guardian triggered: ProactiveEventDispatcher halting")
        self._halted = True


proactive_dispatcher = ProactiveEventDispatcher()

