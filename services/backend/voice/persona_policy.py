"""
Phenom Minimalist Voice Policy & Jarvis Cadence Engine
Gating spontaneous assistant speech strictly to 4 critical triggers:
1. Critical errors / build failures (ERROR_DETECTED)
2. Imminent calendar deadlines (< 10 minutes) (CALENDAR_URGENT)
3. Emergency Guardian / security alerts (SECURITY_ALERT)
4. Explicit direct summons / wake word (DIRECT_SUMMON)

Enforces complete spontaneous speech suppression during user typing or deep focus.
Formats speech into a witty, concise British Jarvis cadence.
"""

import re
import logging
from typing import Dict, Any, Optional
from services.backend.schemas.streaming_voice import SpontaneousSpeechDecision

logger = logging.getLogger("phenom.voice.persona")

ALLOWED_SPONTANEOUS_TRIGGERS = {
    "critical_error",
    "error_detected",
    "calendar_urgent",
    "guardian_security",
    "security_alert",
    "direct_summon",
    "wake_word",
}

SUPPRESSED_ACTIVITIES = {
    "deep_focus",
    "user_typing",
    "focus_mode",
    "gaming",
    "presentation",
}

CONVERSATIONAL_FILLERS = [
    r"^(?:hello|hi|hey)(?:\s+there)?\s*[,.]?\s*(?:how\s+are\s+you(?:\s+today)?\??|hope\s+you(?:'re|\s+are)\s+having\s+a\s+(?:great|wonderful|good)\s+day[.!?,]?)?\s*",
    r"^(?:sure|certainly|absolutely|of\s+course)[,!.]?\s*",
    r"^(?:i(?:'d|\s+would|\s+am)?\s+(?:be\s+)?(?:happy|delighted|pleased)\s+to\s+help(?:\s+you)?(?:\s+with\s+that)?)[,!.]?\s*",
    r"^(?:as\s+an\s+ai|as\s+your\s+assistant)[,!.]?\s*",
    r"^(?:allow\s+me\s+to\s+inform\s+you\s+that\s*)",
    r"^(?:i\s+am\s+pleased\s+to\s+inform\s+you\s+that\s*)",
]


class MinimalistVoicePolicy:
    """
    Smart voice policy manager.
    Controls spontaneous speech emission and enforces witty British Jarvis cadence.
    """

    def __init__(self, mode: str = "minimalist", cadence: str = "british_jarvis"):
        self.mode = mode.lower()
        self.cadence = cadence.lower()

    def set_mode(self, mode: str):
        valid_modes = {"minimalist", "conversational"}
        if mode.lower() in valid_modes:
            self.mode = mode.lower()
        else:
            raise ValueError(f"Invalid mode '{mode}'. Choose from {valid_modes}")

    def get_mode(self) -> str:
        return self.mode

    def set_cadence(self, cadence: str):
        self.cadence = cadence.lower()

    def get_cadence(self) -> str:
        return self.cadence

    def evaluate_spontaneous_speech(
        self,
        event_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> SpontaneousSpeechDecision:
        """
        Evaluates whether Phenom is permitted to speak spontaneously.

        Rules:
        - In 'conversational' mode: speaks on standard events unless user is typing or deep focus.
        - In 'minimalist' mode: strictly gated to 4 triggers:
            1. critical_error / error_detected
            2. calendar_urgent (< 10 minutes until event)
            3. guardian_security / security_alert
            4. direct_summon / wake_word
        - Complete suppression during user typing or deep focus.
        """
        ctx = context or {}
        evt = event_type.lower().strip()

        # 1. Check activity / focus suppression (Highest priority)
        user_typing = ctx.get("user_typing", False) or ctx.get("is_typing", False)
        activity = str(ctx.get("activity", "")).lower().strip()
        focus_state = str(ctx.get("focus_state", "")).lower().strip()

        if user_typing or activity in SUPPRESSED_ACTIVITIES or focus_state in SUPPRESSED_ACTIVITIES:
            # Direct summon can still speak if user explicitly summoned, otherwise complete suppression
            if evt not in ("direct_summon", "wake_word"):
                reason = "Suppressed: user typing detected" if user_typing else f"Suppressed: active focus mode ({activity or focus_state})"
                return SpontaneousSpeechDecision(
                    should_speak=False,
                    reason=reason,
                    urgency_level="none",
                    suggested_tone="suppressed",
                )

        # 2. In conversational mode, allow broader spontaneous triggers
        if self.mode == "conversational":
            if evt in ("desktop_observation", "routine_update", "idle_presence"):
                return SpontaneousSpeechDecision(
                    should_speak=True,
                    reason="Conversational mode permits proactive ambient updates",
                    urgency_level="low",
                    suggested_tone="conversational",
                )

        # 3. In minimalist mode: Check allowed triggers
        if evt in ("critical_error", "error_detected"):
            return SpontaneousSpeechDecision(
                should_speak=True,
                reason="Critical error detected requiring immediate user awareness",
                urgency_level="critical",
                suggested_tone="urgent_witty",
            )

        if evt in ("calendar_urgent",):
            mins = ctx.get("minutes_until", 15)
            if mins is not None and mins <= 10:
                return SpontaneousSpeechDecision(
                    should_speak=True,
                    reason=f"Imminent calendar event starting in {mins} minutes (< 10m threshold)",
                    urgency_level="urgent",
                    suggested_tone="polished_concise",
                )
            else:
                return SpontaneousSpeechDecision(
                    should_speak=False,
                    reason=f"Calendar event starting in {mins}m is outside < 10m urgency threshold",
                    urgency_level="low",
                    suggested_tone="none",
                )

        if evt in ("guardian_security", "security_alert"):
            return SpontaneousSpeechDecision(
                should_speak=True,
                reason="Guardian security or permission alert requires immediate notification",
                urgency_level="security",
                suggested_tone="firm_direct",
            )

        if evt in ("direct_summon", "wake_word"):
            return SpontaneousSpeechDecision(
                should_speak=True,
                reason="User explicitly summoned the assistant",
                urgency_level="direct",
                suggested_tone="witty_concise",
            )

        # All other spontaneous events suppressed in minimalist mode
        return SpontaneousSpeechDecision(
            should_speak=False,
            reason=f"Minimalist policy suppressed non-urgent event '{event_type}'",
            urgency_level="none",
            suggested_tone="none",
        )

    def format_jarvis_cadence(self, text: str, context_type: str = "general") -> str:
        """
        Formats utterance into a witty, concise British Jarvis cadence.
        - Strips pleasantries, introductory fluff, and wordy AI disclaimers.
        - Enforces brevity and punchiness.
        - Adds context-appropriate refined British opening if not already present.
        """
        if not text:
            return ""

        clean = text.strip()

        # Strip conversational fillers repeatedly until stabilized
        changed = True
        while changed:
            changed = False
            for pattern in CONVERSATIONAL_FILLERS:
                new_clean = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip()
                if new_clean != clean:
                    clean = new_clean
                    changed = True

        # Capitalize first letter of remaining text
        if clean:
            clean = clean[0].upper() + clean[1:]

        # If cadence is not british_jarvis, return sanitized text
        if self.cadence != "british_jarvis":
            return clean

        ctx = context_type.lower().strip()

        # Add witty British prefix where fitting if clean text doesn't already have one
        lower_clean = clean.lower()
        if ctx == "critical_error" and not any(lower_clean.startswith(p) for p in ("heads up", "pardon", "right then", "seems like", "it appears")):
            clean = f"Pardon the intrusion, sir. {clean}"
        elif ctx == "calendar_urgent" and not any(lower_clean.startswith(p) for p in ("heads up", "reminder", "right then", "quick heads-up")):
            clean = f"Quick heads-up, sir: {clean}"
        elif ctx == "direct_summon" and not any(lower_clean.startswith(p) for p in ("at your service", "right then", "ready", "yes", "sir")):
            clean = f"Right then. {clean}"

        return clean


# Global singleton instance
minimalist_voice_policy = MinimalistVoicePolicy()
