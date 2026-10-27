"""
Phenom Modes System (Phase 5)
Supports Work, Study, and Chill (Gaming) modes.
Controls enabled tools, assistant tone modifier, and notification rules.
Switchable by voice, hotkey, or UI; persisted in encrypted SQLCipher DB.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from services.backend.memory.db import encrypted_db

class AssistantMode(str, Enum):
    WORK = "work"
    STUDY = "study"
    CHILL = "chill"

MODE_PROFILES: Dict[AssistantMode, Dict[str, Any]] = {
    AssistantMode.WORK: {
        "name": "Work",
        "description": "High productivity: Gmail, Calendar, documents, fast task execution.",
        "tone_prompt": (
            "OPERATING MODE: WORK.\n"
            "Tone: Crisp, highly efficient, professional Jarvis executive assistant. "
            "Prioritize actionable output, task completion, and clarity."
        ),
        "notification_policy": "standard",  # Normal alerts
        "resource_profile": "normal",
        "prioritized_tool_categories": ["workspace", "documents", "files", "apps"],
    },
    AssistantMode.STUDY: {
        "name": "Study",
        "description": "Deep focus: Research papers, summaries, Obsidian vault, quiet notifications.",
        "tone_prompt": (
            "OPERATING MODE: STUDY.\n"
            "Tone: Scholarly, thoughtful, structured, insightful researcher and mentor. "
            "Provide deep analysis, citations, and clear explanations."
        ),
        "notification_policy": "quiet",  # Do not disturb; suppress non-critical alerts
        "resource_profile": "normal",
        "prioritized_tool_categories": ["research", "summaries", "vault", "memory"],
    },
    AssistantMode.CHILL: {
        "name": "Chill / Gaming",
        "description": "Relaxed companion: Playful banter, entertainment, low background resource usage.",
        "tone_prompt": (
            "OPERATING MODE: CHILL / GAMING.\n"
            "Tone: Witty, playful, sarcastic, relaxed gaming buddy. "
            "Use witty humor and banter while keeping explanations easygoing."
        ),
        "notification_policy": "minimal",  # Subtle notifications; never steal focus
        "resource_profile": "low",  # Throttled background heavy tasks
        "prioritized_tool_categories": ["entertainment", "news", "casual"],
    },
}

class ModeManager:
    def __init__(self, db_manager=None):
        self.db = db_manager or encrypted_db
        self._current_mode = self._load_persisted_mode()

    def _load_persisted_mode(self) -> AssistantMode:
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'current_mode';")
            row = cursor.fetchone()
            conn.close()
            if row and row[0] in [m.value for m in AssistantMode]:
                return AssistantMode(row[0])
        except Exception:
            pass
        return AssistantMode.WORK

    def get_current_mode(self) -> AssistantMode:
        return self._current_mode

    def get_mode_profile(self, mode: Optional[AssistantMode] = None) -> Dict[str, Any]:
        target = mode or self._current_mode
        return MODE_PROFILES[target]

    def set_mode(self, new_mode: str) -> Dict[str, Any]:
        normalized = new_mode.strip().lower()
        if "work" in normalized:
            mode = AssistantMode.WORK
        elif "study" in normalized or "focus" in normalized:
            mode = AssistantMode.STUDY
        elif "chill" in normalized or "game" in normalized or "gaming" in normalized:
            mode = AssistantMode.CHILL
        else:
            raise ValueError(f"Unknown mode '{new_mode}'. Allowed modes: work, study, chill.")

        self._current_mode = mode

        # Persist to DB
        try:
            conn = self.db.get_connection()
            with conn:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('current_mode', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                    (mode.value,)
                )
            conn.close()
        except Exception as e:
            print(f"[ModeManager] Failed to persist mode: {e}")

        return {
            "mode": mode.value,
            "name": MODE_PROFILES[mode]["name"],
            "description": MODE_PROFILES[mode]["description"],
            "notification_policy": MODE_PROFILES[mode]["notification_policy"],
            "resource_profile": MODE_PROFILES[mode]["resource_profile"]
        }

    def cycle_mode(self) -> Dict[str, Any]:
        """Cycles through Work -> Study -> Chill -> Work for hotkey toggle."""
        order = [AssistantMode.WORK, AssistantMode.STUDY, AssistantMode.CHILL]
        idx = order.index(self._current_mode)
        next_mode = order[(idx + 1) % len(order)]
        return self.set_mode(next_mode.value)

    def get_tone_prompt(self) -> str:
        return MODE_PROFILES[self._current_mode]["tone_prompt"]

    def is_notification_allowed(self, priority: str = "normal") -> bool:
        policy = MODE_PROFILES[self._current_mode]["notification_policy"]
        if policy == "standard":
            return True
        elif policy == "quiet":
            return priority in ["urgent", "critical", "kill_switch"]
        elif policy == "minimal":
            return priority in ["high", "urgent", "critical", "kill_switch"]
        return True

# Singleton instance
mode_manager = ModeManager()
