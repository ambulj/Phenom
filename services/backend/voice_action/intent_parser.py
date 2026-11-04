import re
from typing import Tuple, Optional
from services.backend.schemas.voice_action import IntentType


class StreamingIntentParser:
    """Parses streaming speech transcripts into structured intents with strict Phenom safety invariants."""

    PAYMENT_TERMS = [
        "pay now", "buy now", "checkout", "place order",
        "complete purchase", "transfer money", "execute trade", "send money"
    ]

    CREDENTIAL_TERMS = [
        "password", "secret pin", "private key", "credit card", "cvv"
    ]

    PERMANENT_DELETE_TERMS = [
        "delete permanently", "purge file", "hard delete", "shred file"
    ]

    EMAIL_SEND_TERMS = [
        "send email", "dispatch email", "blast email"
    ]

    INTERRUPTION_TERMS = [
        "stop", "halt", "quiet", "cancel", "hold on", "wait", "shut up", "pause"
    ]

    def parse(self, transcript: str) -> Tuple[IntentType, Optional[str], float]:
        """
        Parses transcript into (IntentType, tool_name, confidence).
        Enforces Rule 7, Rule 8, Rule 9, and Rule 11.
        """
        if not transcript or not transcript.strip():
            return IntentType.UNKNOWN, None, 0.0

        lowered = transcript.strip().lower()

        # Rule 8: Payments impossible by construction
        for term in self.PAYMENT_TERMS:
            if term in lowered:
                raise PermissionError(
                    f"Rule 8 Violation: Voice-initiated financial transaction '{term}' is strictly blocked."
                )

        # Rule 8 & 11: Passwords / credentials blocked
        for term in self.CREDENTIAL_TERMS:
            if term in lowered:
                raise PermissionError(
                    f"Rule 8/11 Violation: Utterance contains sensitive credential term '{term}'."
                )

        # Rule 7: Permanent delete blocked
        for term in self.PERMANENT_DELETE_TERMS:
            if term in lowered:
                raise PermissionError(
                    f"Rule 7 Violation: Permanent file deletion '{term}' is prohibited. Phenom uses recycle bin only."
                )

        # Rule 9: Email drafts only
        for term in self.EMAIL_SEND_TERMS:
            if term in lowered:
                raise PermissionError(
                    f"Rule 9 Violation: Directly sending emails '{term}' is prohibited. Drafts only."
                )

        # Interruptions / Barge-in
        for term in self.INTERRUPTION_TERMS:
            if re.search(rf"\b{re.escape(term)}\b", lowered):
                return IntentType.INTERRUPTION, None, 0.98

        # System commands
        if any(term in lowered for term in ["mute", "unmute", "lock screen", "minimize", "maximize", "focus"]):
            return IntentType.SYSTEM_COMMAND, "system_control", 0.92

        # Tool calls
        if any(term in lowered for term in ["open", "find", "search", "read note", "draft", "check calendar"]):
            tool_name = "workspace_search"
            if "calendar" in lowered:
                tool_name = "calendar_query"
            elif "draft" in lowered:
                tool_name = "email_draft"
            elif "note" in lowered:
                tool_name = "notes_query"
            return IntentType.TOOL_CALL, tool_name, 0.90

        # General queries
        if any(lowered.startswith(w) for w in ["what", "who", "where", "how", "why", "explain", "tell me"]):
            return IntentType.QUERY, "knowledge_query", 0.85

        return IntentType.UNKNOWN, None, 0.40
