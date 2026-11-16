"""Contextual Swarm Voice Bridge for Phenom.

Phase 48-03: VOICE-03.
Translates user voice barge-in utterances into high-priority steering guidance
dynamically injected into the active swarm coordinator and task scheduler.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from services.backend.schemas.voice_duplex import BargeInType, SwarmGuidanceInjection
from services.backend.swarm.scheduler import SwarmScheduler
from services.backend.voice.barge_in_handler import BargeInSoftMuteHandler

logger = logging.getLogger("phenom.voice.swarm_voice_bridge")


class SwarmVoiceBridge:
    """Bridges real-time vocal barge-in speech with autonomous swarm execution."""

    CORRECTION_KEYWORDS = [r"\bno\b", r"\bdon'?t\b", r"\bstop\b", r"\bcancel\b", r"\bwrong\b", r"\brevert\b"]
    STEERING_KEYWORDS = [r"\bfocus\b", r"\bprioritize\b", r"\bfirst\b", r"\balso\b", r"\bmake sure\b", r"\buse\b"]

    def __init__(
        self,
        barge_in_handler: Optional[BargeInSoftMuteHandler] = None,
        default_scheduler: Optional[SwarmScheduler] = None,
    ) -> None:
        self.barge_in_handler = barge_in_handler or BargeInSoftMuteHandler()
        self.scheduler = default_scheduler
        self._injections: List[SwarmGuidanceInjection] = []

    def classify_intent(self, utterance: str) -> BargeInType:
        """Categorize user spoken interruption into a formal BargeInType."""
        cleaned = utterance.strip().lower()

        # 1. Emergency kill words
        if self.barge_in_handler.check_is_emergency_kill(cleaned):
            return BargeInType.EMERGENCY_HALT

        # 2. Corrections or scope fences
        if any(re.search(pat, cleaned) for pat in self.CORRECTION_KEYWORDS):
            return BargeInType.CORRECTION

        # 3. Steering guidance
        if any(re.search(pat, cleaned) for pat in self.STEERING_KEYWORDS):
            return BargeInType.STEERING_GUIDANCE

        return BargeInType.CONVERSATIONAL

    def inject_guidance(
        self,
        transcript: str,
        scheduler: Optional[SwarmScheduler] = None,
        target_task_id: Optional[str] = None,
    ) -> SwarmGuidanceInjection:
        """Convert transcript to guidance and inject into scheduler queue."""
        b_type = self.classify_intent(transcript)
        sched = scheduler or self.scheduler

        # If emergency kill-word, trigger halt
        if b_type == BargeInType.EMERGENCY_HALT:
            if sched:
                sched.halt()
            self.barge_in_handler.trigger_soft_mute(transcript)

        priority = 10 if b_type in (BargeInType.EMERGENCY_HALT, BargeInType.CORRECTION) else (8 if b_type == BargeInType.STEERING_GUIDANCE else 5)

        injection = SwarmGuidanceInjection(
            injection_id=f"guide_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}",
            target_task_id=target_task_id,
            priority=priority,
            guidance_text=transcript,
            barge_in_type=b_type,
            created_at=time.time(),
            applied=False,
        )

        # Apply to scheduled tasks if available
        if sched and sched.get_queue_status():
            for task in sched.get_queue_status():
                if target_task_id is None or task.task_id == target_task_id:
                    task.arguments["_operator_guidance"] = transcript
                    task.arguments["_guidance_priority"] = priority
                    injection.applied = True

        self._injections.append(injection)
        logger.info(
            "Injected guidance '%s' (type=%s, priority=%d, applied=%s)",
            transcript,
            b_type.value,
            priority,
            injection.applied,
        )
        return injection

    def get_active_guidance(self) -> List[SwarmGuidanceInjection]:
        """Return list of all recorded voice guidance injections."""
        return list(self._injections)

    def clear_guidance(self) -> int:
        """Clear all active guidance records."""
        count = len(self._injections)
        self._injections.clear()
        return count
