"""Spoken Milestone & Handoff Briefings for Phenom Voice.

Phase 48-04: PERSONA-03.
Generates brief, well-timed spoken audio cues and notifications announcing
multi-agent swarm handoffs, consensus approvals, and mission completions.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from services.backend.schemas.dynamic_persona import SpokenMilestoneBriefing

logger = logging.getLogger("phenom.voice.proactive_cues")


class SpokenHandoffNotifier:
    """Creates concise voice briefings for autonomous swarm handoffs and milestones."""

    MAX_WORD_COUNT: int = 25  # Invariant: Must remain under 25 words to prevent fatigue

    @classmethod
    def _create_briefing(
        cls,
        event_type: str,
        text: str,
        urgency: int = 1,
        earcon: str = "chime_success.wav",
    ) -> SpokenMilestoneBriefing:
        """Internal helper validating word limit invariant."""
        words = text.strip().split()
        if len(words) > cls.MAX_WORD_COUNT:
            text = " ".join(words[: cls.MAX_WORD_COUNT]) + "..."

        briefing = SpokenMilestoneBriefing(
            briefing_id=f"brief_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}",
            event_type=event_type,
            text=text,
            urgency=urgency,
            audio_earcon=earcon,
            timestamp=time.time(),
        )
        logger.info("Generated spoken briefing [%s]: '%s'", event_type, text)
        return briefing

    @classmethod
    def create_handoff_briefing(
        cls,
        from_role: str,
        to_role: str,
        task_title: str = "",
    ) -> SpokenMilestoneBriefing:
        """Briefing announcing subagent handoff."""
        from_clean = from_role.replace("_", " ").title()
        to_clean = to_role.replace("_", " ").title()
        task_clean = f" on {task_title}" if task_title else ""
        text = f"{from_clean} handed off to {to_clean}{task_clean}. Execution proceeding."
        return cls._create_briefing(
            event_type="handoff",
            text=text,
            urgency=1,
            earcon="chime_handoff.wav",
        )

    @classmethod
    def create_quorum_briefing(
        cls,
        state: str,
        is_approved: bool,
    ) -> SpokenMilestoneBriefing:
        """Briefing announcing two-tier consensus quorum outcome."""
        if is_approved:
            text = "Two-tier quorum approved. Security Auditor and Coder signed off."
            urgency = 2
            earcon = "chime_quorum_pass.wav"
        else:
            text = f"Consensus check halted. Status is {state.replace('_', ' ')}."
            urgency = 4
            earcon = "alert_veto.wav"

        return cls._create_briefing(
            event_type="quorum",
            text=text,
            urgency=urgency,
            earcon=earcon,
        )

    @classmethod
    def create_mission_complete_briefing(
        cls,
        patch_id: str,
        file_count: int = 1,
    ) -> SpokenMilestoneBriefing:
        """Briefing announcing autonomous mission completion."""
        text = f"Mission complete, sir. Verified patch bundle ready across {file_count} files."
        return cls._create_briefing(
            event_type="complete",
            text=text,
            urgency=1,
            earcon="chime_complete.wav",
        )
