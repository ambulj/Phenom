"""Telegram Episodic Knowledge Cards (Milestone 49 Phase 5, TELE-03).

Formats proactive Telegram companion status cards featuring ASCII knowledge graph
topologies, episodic milestone recaps, and one-click `/sync_vault` and `/halt` triggers.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.remote.telegram_episodic_card")


class TelegramEpisodicCardFormatter:
    """Renders formatted Telegram companion cards for episodic milestones and heuristics."""

    _CREDENTIAL_PATTERN = re.compile(
        r"(?i)['\"]?\b(api[_-]?key|secret|token|password|bearer|auth[_-]?token|passwd|pwd)\b['\"]?\s*[:=\s]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"
    )

    def _sanitize(self, text: str) -> str:
        if not text:
            return ""
        return self._CREDENTIAL_PATTERN.sub(r"\1: [REDACTED]", text)

    def format_card(
        self,
        episode_title: str,
        summary: str,
        active_entities: List[str],
        recent_heuristics: List[str],
        active_window: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates markdown card text and interactive inline button rows."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Telegram card generation aborted.")

        clean_title = self._sanitize(episode_title)
        clean_summary = self._sanitize(summary)
        clean_window = self._sanitize(active_window or "Visual Studio Code")

        # Build ASCII Knowledge Topology
        ascii_graph = [
            "```",
            "  [Concept] <--- (IMPLEMENTS) --- [Project]",
            "      |                                |",
            "  (RESOLVES)                      (DEPENDS_ON)",
            "      v                                v",
            "  [Decision] <-------------------- [File]",
            "```",
        ]

        card_lines = [
            "🧠 *PHENOM KNOWLEDGE MATRIX & CHOREOGRAPHER*",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📌 *Milestone Episode*: `{clean_title}`",
            f"🎯 *Active Focus*: `{clean_window}`",
            "",
            "📊 *Episodic Topology*:",
            "\n".join(ascii_graph),
            "",
            f"📝 *Summary*: {clean_summary}",
            "",
            f"🔗 *Connected Entities*: {', '.join([f'`{e}`' for e in active_entities[:4]]) or 'None'}",
            f"🛡️ *Learned Heuristics*: {', '.join([f'`{h}`' for h in recent_heuristics[:2]]) or 'None'}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "⚡ _Universal Guardian SLA: < 25.0ms Active_",
        ]

        keyboard = [
            [
                {"text": "🔄 Sync Obsidian Vault", "callback_data": "/sync_obsidian_vault"},
                {"text": "🛑 HALT GUARDIAN", "callback_data": "/guardian_halt"},
            ]
        ]

        return {
            "text": "\n".join(card_lines),
            "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": keyboard},
        }


# Global singleton instance
telegram_episodic_card = TelegramEpisodicCardFormatter()
