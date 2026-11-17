"""
Phenom Dual Handoff Briefing Generator (WKF-05.4)
Synthesizes completion handoff for autonomous desktop workflows:
1. Spoken witty Jarvis voice briefing (strictly enforced <= 25 words)
2. Telegram companion card with execution recap, progress ASCII, and metrics
"""

from __future__ import annotations

import os
import sys
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("phenom.workflows.dual_handoff")


class DualHandoffBriefing(BaseModel):
    """Structured dual handoff briefing containing spoken voice and Telegram card."""
    dag_id: str
    goal: str
    spoken_summary: str
    word_count: int
    telegram_card_markdown: str
    success: bool
    step_count: int
    duration_s: float
    screenshots_attached: int = 0
    timestamp: float = Field(default_factory=time.time)

    @field_validator("spoken_summary")
    @classmethod
    def validate_word_count(cls, v: str) -> str:
        words = v.split()
        if len(words) > 25:
            # Strictly enforce the <= 25 words limit
            trimmed = " ".join(words[:24]) + "..."
            return trimmed
        return v


class DualHandoffGenerator:
    """Produces witty Jarvis voice summaries and Telegram companion cards."""

    # Curated Jarvis witty templates strictly <= 25 words
    _SUCCESS_TEMPLATES = [
        "All tasks concluded with distinction, sir. Workspace synchronized, research encapsulated, and zero obstacles could stop us.",
        "Operation completed flawlessly, sir. Clean execution across every step with full safety enclaves intact. Ready when you are.",
        "Workflow executed to perfection, sir. Everything is filed, verified, and in proper order without a single complaint from Windows.",
    ]

    _PARTIAL_TEMPLATES = [
        "Workflow paused at an unexpected prompt, sir. Everything up to that point is safe and waiting for your review.",
        "A slight divergence required my pause, sir. Rather than guessing, I've secured the workspace for your final instruction.",
    ]

    def generate_briefing(
        self,
        dag_id: str,
        goal: str,
        step_count: int,
        success: bool,
        duration_s: float,
        screenshots_attached: int = 1
    ) -> DualHandoffBriefing:
        """Formulates spoken summary and Telegram companion card."""
        # 1. Select and format witty spoken summary
        if success:
            template = self._SUCCESS_TEMPLATES[hash(dag_id) % len(self._SUCCESS_TEMPLATES)]
        else:
            template = self._PARTIAL_TEMPLATES[hash(dag_id) % len(self._PARTIAL_TEMPLATES)]

        # Ensure strict <= 25 word constraint
        words = template.split()
        if len(words) > 25:
            spoken_text = " ".join(words[:24]) + "."
        else:
            spoken_text = template

        word_count = len(spoken_text.split())

        # 2. Format rich Telegram companion card
        status_emoji = "✅ COMPLETED" if success else "⚠️ DIVERGED / PAUSED"
        progress_bar = "▰▰▰▰▰▰▰▰▰▰ 100%" if success else "▰▰▰▰▰▱▱▱▱▱ 50%"

        telegram_card = (
            f"🤖 *Phenom Autonomous Workflow Debrief*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Goal:* `{goal}`\n"
            f"📊 *Status:* {status_emoji}\n"
            f"📈 *Progress:* `{progress_bar}`\n"
            f"⚡ *Duration:* `{duration_s:.1f}s` | *Steps:* `{step_count}`\n"
            f"🛡️ *Enclave:* `[UNTRUSTED_TAINT] Isolated`\n"
            f"📸 *Screenshots:* `{screenshots_attached} attached`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎙️ *Jarvis:* _\"{spoken_text}\"_\n"
            f"_(ID: {dag_id})_"
        )

        briefing = DualHandoffBriefing(
            dag_id=dag_id,
            goal=goal,
            spoken_summary=spoken_text,
            word_count=word_count,
            telegram_card_markdown=telegram_card,
            success=success,
            step_count=step_count,
            duration_s=duration_s,
            screenshots_attached=screenshots_attached,
        )

        # Broadcast briefing event to desktop UI
        self._broadcast_event("WORKFLOW_HANDOFF_BRIEFING", briefing.model_dump())
        return briefing

    def _broadcast_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        try:
            main_mod = sys.modules.get("services.backend.main")
            broadcaster = getattr(main_mod, "broadcast_message", None)
            if broadcaster:
                msg = {
                    "id": f"hnd-{os.urandom(2).hex()}",
                    "type": event_type,
                    "ts": str(time.time()),
                    "payload": payload
                }
                main_loop = getattr(main_mod, "main_loop", None)
                if main_loop and main_loop.is_running():
                    asyncio.run_coroutine_threadsafe(broadcaster(msg), main_loop)
        except Exception:
            pass


dual_handoff_generator = DualHandoffGenerator()
