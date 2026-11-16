"""
Dynamic Editable Telegram Mission Card Generator (Phase 47-05, ROUTER-04).
Formats real-time progress status cards with ASCII progress bars, inline actions,
and milestone updates for the authorized Telegram companion.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class TelegramMissionCard:
    """Generates dynamic markdown status messages for Telegram bot delivery."""

    @staticmethod
    def generate_progress_bar(completed: int, total: int, width: int = 10) -> str:
        """Constructs an ASCII progress bar (e.g. [████░░░░░░] 40%)."""
        if total <= 0:
            return "[░░░░░░░░░░] 0%"
        pct = min(1.0, max(0.0, completed / total))
        fill_count = int(round(pct * width))
        empty_count = width - fill_count
        bar = "█" * fill_count + "░" * empty_count
        return f"[{bar}] {int(pct * 100)}%"

    @staticmethod
    def format_mission_card(
        mission_id: str,
        goal: str,
        status: str,
        current_step_title: str,
        completed_steps: int,
        total_steps: int,
        elapsed_seconds: float,
        error: Optional[str] = None
    ) -> str:
        """Formats the Markdown payload for Telegram message updates."""
        progress_bar = TelegramMissionCard.generate_progress_bar(completed_steps, total_steps)
        mins = int(elapsed_seconds // 60)
        secs = int(elapsed_seconds % 60)
        timer_str = f"{mins:02d}:{secs:02d}"

        status_emoji = {
            "running": "⚡ RUNNING",
            "completed": "✅ COMPLETED",
            "failed": "❌ FAILED",
            "halted": "🛑 HALTED",
            "pending": "⏳ WAITING APPROVAL"
        }.get(status.lower(), f"ℹ️ {status.upper()}")

        lines = [
            "🤖 *PHENOM AUTONOMOUS MISSION*",
            f"🎯 *Goal:* _{goal}_",
            f"📊 *Status:* `{status_emoji}`",
            f"📈 *Progress:* `{progress_bar}` ({completed_steps}/{total_steps} steps)",
            f"📍 *Active Step:* `{current_step_title}`",
            f"⏱️ *Elapsed Time:* `{timer_str}`"
        ]

        if error:
            lines.append(f"⚠️ *Alert:* `{error}`")

        lines.append(f"\n_ID: {mission_id[:12]}_")

        return "\n".join(lines)

    @staticmethod
    def get_inline_keyboard(mission_id: str, status: str) -> List[List[Dict[str, str]]]:
        """Builds inline action buttons for Telegram status card."""
        if status.lower() == "pending":
            return [
                [
                    {"text": "✅ Authorize Mission", "callback_data": f"mission:approve:{mission_id}"},
                    {"text": "❌ Cancel", "callback_data": f"mission:cancel:{mission_id}"}
                ]
            ]
        elif status.lower() == "running":
            return [
                [
                    {"text": "⏸️ Pause", "callback_data": f"mission:pause:{mission_id}"},
                    {"text": "🛑 HALT KILL SWITCH", "callback_data": f"mission:halt:{mission_id}"}
                ]
            ]
        return []


# Global singleton instance
telegram_mission_card = TelegramMissionCard()
