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
    DEEP_FOCUS = "deep_focus"
    CYBER = "cyber"
    SECURITY = "security"

SPECIALIST_MODEL_NAME = "hf.co/tinyopsec/Qwen3.5-4B-Uncensored-Aggressive-GGUF:Q4_K_M"

MODE_PROFILES: Dict[AssistantMode, Dict[str, Any]] = {
    AssistantMode.SECURITY: {
        "name": "Security & Kali Mode",
        "description": "Tactical Infosec & Penetration Testing: Reconnaissance, scanning, exploit simulation, vulnerability auditing.",
        "specialist_model": SPECIALIST_MODEL_NAME,
        "tone_prompt": (
            "OPERATING MODE: SECURITY & KALI SPECIALIST OPERATOR.\n"
            "Tone: Tactical, precision-driven infosec engineer and offensive security partner. "
            "Execute recon, scanning, and security audits with elite technical precision. "
            "Address user as Bro or Chief Operator. Zero conversational fluff."
        ),
        "notification_policy": "standard",
        "resource_profile": "high",
        "audio_volume_scale": 0.9,
        "prioritized_tool_categories": ["security", "terminal", "diagnostics", "code", "network"],
    },
    AssistantMode.CYBER: {
        "name": "Cyber Warfare & SOC",
        "description": "Tactical Infosec Operator: Network security, reverse engineering, exploit analysis, threat auditing.",
        "specialist_model": SPECIALIST_MODEL_NAME,
        "tone_prompt": (
            "OPERATING MODE: CYBER WARFARE & SOC LAB PARTNER.\n"
            "Tone: Tactical, elite infosec engineer and cyber partner to Abhi. "
            "Use sharp cybersecurity terminology (recon, zero-days, memory safety, MITRE ATT&CK, pcap, reverse engineering, hardening). "
            "Address Abhi as Bro or Chief Operator. High technical precision."
        ),
        "notification_policy": "standard",
        "resource_profile": "high",
        "audio_volume_scale": 0.85,
        "prioritized_tool_categories": ["security", "terminal", "diagnostics", "code", "network"],
    },
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
        "audio_volume_scale": 1.0,
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
        "audio_volume_scale": 0.35,
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
        "audio_volume_scale": 0.65,
        "prioritized_tool_categories": ["entertainment", "news", "casual"],
    },
    AssistantMode.DEEP_FOCUS: {
        "name": "Deep Focus",
        "description": "Absolute concentration: Total silence, all non-critical notifications blocked, max compute.",
        "tone_prompt": (
            "OPERATING MODE: DEEP FOCUS.\n"
            "Tone: Ultra-terse, precise, zero conversational filler. "
            "Deliver exact solutions immediately."
        ),
        "notification_policy": "silent",  # Strictly zero toasts except Guardian halt
        "resource_profile": "high",
        "audio_volume_scale": 0.0,
        "prioritized_tool_categories": ["code", "terminal", "vault", "system"],
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

    @property
    def current_mode(self) -> AssistantMode:
        return self._current_mode

    @property
    def is_security_mode_active(self) -> bool:
        return self._current_mode in (AssistantMode.SECURITY, AssistantMode.CYBER)

    @property
    def active_specialist_model(self) -> Optional[str]:
        if self.is_security_mode_active:
            return SPECIALIST_MODEL_NAME
        return None

    def get_current_mode(self) -> AssistantMode:
        return self._current_mode

    def get_mode_profile(self, mode: Optional[AssistantMode] = None) -> Dict[str, Any]:
        target = mode or self._current_mode
        return MODE_PROFILES[target]

    def set_mode(self, new_mode: str) -> Dict[str, Any]:
        normalized = new_mode.strip().lower()
        if "security" in normalized or "kali" in normalized:
            mode = AssistantMode.SECURITY
        elif "cyber" in normalized or "red_team" in normalized or "redteam" in normalized:
            mode = AssistantMode.CYBER
        elif "deep" in normalized or "silent" in normalized:
            mode = AssistantMode.DEEP_FOCUS
        elif "work" in normalized or "normal" in normalized or "default" in normalized:
            mode = AssistantMode.WORK
        elif "study" in normalized or "research" in normalized or "focus" in normalized:
            mode = AssistantMode.STUDY
        elif "chill" in normalized or "game" in normalized or "gaming" in normalized:
            mode = AssistantMode.CHILL
        else:
            raise ValueError(f"Unknown mode '{new_mode}'. Allowed modes: work, study, chill, deep_focus, security, cyber.")

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

        # Broadcast mode change to UI
        try:
            import sys, asyncio
            main_mod = sys.modules.get("services.backend.main")
            if main_mod and hasattr(main_mod, "broadcast_message"):
                msg = {
                    "type": "mode.changed",
                    "payload": {
                        "mode": mode.value,
                        "name": MODE_PROFILES[mode]["name"],
                        "is_security_mode": self.is_security_mode_active,
                        "specialist_model": self.active_specialist_model,
                        "indicator": "SECURITY / KALI SPECIALIST ACTIVE" if self.is_security_mode_active else None
                    }
                }
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(main_mod.broadcast_message(msg))
                except RuntimeError:
                    pass
        except Exception:
            pass

        return {
            "mode": mode.value,
            "name": MODE_PROFILES[mode]["name"],
            "description": MODE_PROFILES[mode]["description"],
            "notification_policy": MODE_PROFILES[mode]["notification_policy"],
            "resource_profile": MODE_PROFILES[mode]["resource_profile"],
            "is_security_mode": self.is_security_mode_active,
            "specialist_model": self.active_specialist_model
        }

    def cycle_mode(self) -> Dict[str, Any]:
        """Cycles through Work -> Study -> Chill -> Work for hotkey toggle."""
        order = [AssistantMode.WORK, AssistantMode.STUDY, AssistantMode.CHILL, AssistantMode.DEEP_FOCUS]
        idx = order.index(self._current_mode)
        next_mode = order[(idx + 1) % len(order)]
        return self.set_mode(next_mode.value)

    def get_tone_prompt(self) -> str:
        return MODE_PROFILES[self._current_mode]["tone_prompt"]

    def is_notification_allowed(self, priority: str = "normal") -> bool:
        policy = MODE_PROFILES[self._current_mode]["notification_policy"]
        if policy == "silent":
            return priority in ["critical", "kill_switch"]
        elif policy == "quiet":
            return priority in ["urgent", "critical", "kill_switch"]
        elif policy == "minimal":
            return priority in ["high", "urgent", "critical", "kill_switch"]
        return True

    def get_volume_scale(self, mode: Optional[AssistantMode] = None) -> float:
        target = mode or self._current_mode
        return float(MODE_PROFILES.get(target, {}).get("audio_volume_scale", 1.0))

# Singleton instance
mode_manager = ModeManager()
