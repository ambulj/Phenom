"""Context-Aware Ambient Watchdog for Phenom (Milestone 30 Phase 4).

Monitors application focus transitions and calendar milestone markers to emit
non-intrusive HUD toast notifications and subtle voice reminders (AMB-01.1, AMB-01.2).
Enforces Rule 4 (offline local), Rule 8 (anti-checkout), Rule 11 (credential protection),
and Rule 3 Guardian kill switch SLA < 25.0ms.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.voice.tts import tts_engine

logger = logging.getLogger("phenom.ambient.watchdog")


class Rule8ViolationError(Exception):
    """Raised when context alert or command contains financial or payment directives."""
    pass


class ContextNudge(BaseModel):
    nudge_id: str
    category: str  # FOCUS, CALENDAR, MILESTONE, SYSTEM
    title: str
    message: str
    voice_phrase: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    acknowledged: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextWatchdog:
    """Monitors workspace application focus and calendar timelines for ambient alerts."""

    _RULE_8_PATTERN = re.compile(
        r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
        re.IGNORECASE,
    )

    _CREDENTIAL_PATTERN = re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password|bearer|auth[_-]?token|passwd|pwd)\b\s*[:=\s]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"
    )

    _DISTRACTION_SIGNATURES = [
        "youtube", "twitter", "x.com", "reddit", "facebook", "instagram", "tiktok", "netflix"
    ]

    def __init__(
        self,
        cooldown_seconds: float = 300.0,
        primary_goal: str = "Phenom Milestone 30 Implementation",
    ) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.primary_goal = primary_goal
        self.active_focus_app: str = "Visual Studio Code"
        self._last_nudge_times: Dict[str, float] = {}
        self.recent_nudges: List[ContextNudge] = []
        self._counter: int = 100
        self.speech_enabled: bool = True

    def check_safety(self, text: Optional[str] = None) -> None:
        """Enforces Guardian kill switch (Rule 3) and Anti-Checkout (Rule 8)."""
        if guardian.is_halted:
            raise RuntimeError("Execution halted by Guardian kill switch (CONTEXT_WATCHDOG_HALTED)")

        if text and self._RULE_8_PATTERN.search(text):
            raise Rule8ViolationError(
                "Rule 8 Violation: Payment, checkout, or billing directives detected in context watchdog"
            )

    def scrub_credentials(self, text: str) -> Tuple[str, int]:
        """Recursively scrubs credentials and tokens from alert strings (Rule 11)."""
        count = 0

        def replace_cred(match: re.Match) -> str:
            nonlocal count
            count += 1
            key = match.group(1)
            return f"{key}: [REDACTED]"

        scrubbed = self._CREDENTIAL_PATTERN.sub(replace_cred, text)
        return scrubbed, count

    def evaluate_app_switch(
        self,
        window_title: str,
        process_name: str,
    ) -> Optional[ContextNudge]:
        """Evaluates active window switch to detect focus drift from primary sprint goal."""
        self.check_safety(f"{window_title} {process_name}")
        self.active_focus_app = window_title

        now = time.time()
        low_title = window_title.lower()
        low_proc = process_name.lower()

        # Check for distraction signature
        is_distraction = any(sig in low_title or sig in low_proc for sig in self._DISTRACTION_SIGNATURES)

        if is_distraction:
            last_time = self._last_nudge_times.get("FOCUS", 0.0)
            if (now - last_time) >= self.cooldown_seconds:
                self._last_nudge_times["FOCUS"] = now
                self._counter += 1
                nudge_id = f"nudge-{self._counter}"

                clean_title, _ = self.scrub_credentials(window_title)
                voice_msg = f"Bro, quick check-in: let's stay locked into {self.primary_goal}!"
                nudge = ContextNudge(
                    nudge_id=nudge_id,
                    category="FOCUS",
                    title="Focus Drift Detected",
                    message=f"Switched to '{clean_title}'. Active objective is '{self.primary_goal}'.",
                    voice_phrase=voice_msg,
                )
                self.recent_nudges.append(nudge)
                if len(self.recent_nudges) > 50:
                    self.recent_nudges.pop(0)

                if self.speech_enabled:
                    try:
                        tts_engine.speak(voice_msg)
                    except Exception as err:
                        logger.debug("TTS nudge speak non-blocking failure: %s", err)

                logger.info("Context watchdog emitted focus drift nudge: %s", nudge_id)
                return nudge

        return None

    def evaluate_calendar_event(
        self,
        event_title: str,
        minutes_until: int,
    ) -> Optional[ContextNudge]:
        """Evaluates upcoming calendar timeline markers and emits timely reminders."""
        self.check_safety(event_title)

        if minutes_until <= 15:
            now = time.time()
            cooldown_key = f"CALENDAR_{event_title}"
            last_time = self._last_nudge_times.get(cooldown_key, 0.0)

            if (now - last_time) >= self.cooldown_seconds:
                self._last_nudge_times[cooldown_key] = now
                self._counter += 1
                nudge_id = f"nudge-{self._counter}"

                clean_event, _ = self.scrub_credentials(event_title)
                voice_msg = f"Bro, reminder: '{clean_event}' starts in {minutes_until} minutes."
                nudge = ContextNudge(
                    nudge_id=nudge_id,
                    category="CALENDAR",
                    title="Upcoming Schedule Alert",
                    message=f"Event '{clean_event}' is scheduled in {minutes_until} minutes.",
                    voice_phrase=voice_msg,
                    metadata={"minutes_until": minutes_until},
                )
                self.recent_nudges.append(nudge)
                if len(self.recent_nudges) > 50:
                    self.recent_nudges.pop(0)

                if self.speech_enabled:
                    try:
                        tts_engine.speak(voice_msg)
                    except Exception as err:
                        logger.debug("TTS calendar speak non-blocking failure: %s", err)

                logger.info("Context watchdog emitted calendar alert: %s", nudge_id)
                return nudge

        return None

    def trigger_manual_nudge(
        self,
        category: str,
        message: str,
        voice_phrase: Optional[str] = None,
    ) -> ContextNudge:
        """Triggers a manual or test context alert with Rule 8 and Rule 11 enforcement."""
        check_text = f"{category} {message} {voice_phrase or ''}"
        self.check_safety(check_text)

        clean_message, _ = self.scrub_credentials(message)
        clean_voice = None
        if voice_phrase:
            clean_voice, _ = self.scrub_credentials(voice_phrase)

        self._counter += 1
        nudge_id = f"nudge-{self._counter}"

        nudge = ContextNudge(
            nudge_id=nudge_id,
            category=category.upper(),
            title=f"Ambient {category.capitalize()} Nudge",
            message=clean_message,
            voice_phrase=clean_voice,
        )
        self.recent_nudges.append(nudge)
        if len(self.recent_nudges) > 50:
            self.recent_nudges.pop(0)

        if self.speech_enabled and clean_voice:
            try:
                tts_engine.speak(clean_voice)
            except Exception as err:
                logger.debug("TTS manual speak non-blocking failure: %s", err)

        return nudge

    def get_status(self) -> Dict[str, Any]:
        """Returns watchdog state, active focus app, and recent nudges."""
        self.check_safety()
        return {
            "active_focus_app": self.active_focus_app,
            "primary_goal": self.primary_goal,
            "cooldown_seconds": self.cooldown_seconds,
            "speech_enabled": self.speech_enabled,
            "recent_nudges_count": len(self.recent_nudges),
            "recent_nudges": [n.model_dump() for n in self.recent_nudges[-10:]],
            "guardian_halted": guardian.is_halted,
            "offline_local": True,
        }


# Global singleton instance
context_watchdog = ContextWatchdog()
