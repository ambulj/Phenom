"""Conversational Intent Parser for Phenom (Milestone 29 Phase 3).

Parses spoken and natural language user responses to confirmation prompts,
identifying affirmative, negative, or ambiguous intent with confidence scoring (VOICE-01.2).
"""

from __future__ import annotations

from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.safety.intent_parser")


class Rule8ViolationError(Exception):
    """Raised when intent parsing involves payment or checkout operations."""
    pass


class ConfirmationDecision(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    AMBIGUOUS = "AMBIGUOUS"


class ParsedIntentResult(BaseModel):
    decision: ConfirmationDecision
    confidence: float
    matched_phrase: Optional[str] = None
    raw_input: str


class ConversationalIntentParser:
    """Parses natural spoken or typed user feedback during confirmation requests."""

    _RULE_8_PATTERN = re.compile(
        r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
        re.IGNORECASE,
    )

    _AFFIRMATIVE_PATTERNS = [
        re.compile(r"\b(yes|yeah|yep|yup|sure|definitely|absolutely|certainly)\b", re.IGNORECASE),
        re.compile(r"\b(go ahead|do it|proceed|confirm|approve|approved|make it happen)\b", re.IGNORECASE),
        re.compile(r"\b(all good|sounds good|looks good|okay|ok|fine)\b", re.IGNORECASE),
        re.compile(r"\b(haan|haanji|kar do|kar de|theek hai)\b", re.IGNORECASE),
    ]

    _NEGATIVE_PATTERNS = [
        re.compile(r"\b(no|nah|nope|never|negative|deny|denied)\b", re.IGNORECASE),
        re.compile(r"\b(cancel|stop|abort|halt|drop it|leave it)\b", re.IGNORECASE),
        re.compile(r"\b(don't|do not|wait|hold on|not now)\b", re.IGNORECASE),
        re.compile(r"\b(mat kar|nahi|nahin|ruko)\b", re.IGNORECASE),
    ]

    def check_safety(self, text: str) -> None:
        """Enforces Guardian kill switch and Rule 8 payment defenses."""
        if guardian.is_halted:
            raise RuntimeError("Execution halted by Guardian kill switch (INTENT_PARSER_HALTED)")

        if self._RULE_8_PATTERN.search(text):
            raise Rule8ViolationError(
                "Rule 8 Violation: Payment, checkout, or billing directives detected in user voice input"
            )

    def parse_intent(self, text: str) -> ParsedIntentResult:
        """Evaluates spoken response string and resolves confirmation decision."""
        self.check_safety(text)
        cleaned = text.strip()

        if not cleaned:
            return ParsedIntentResult(
                decision=ConfirmationDecision.AMBIGUOUS,
                confidence=0.0,
                matched_phrase=None,
                raw_input=text,
            )

        # Check negative patterns first (Safety invariant: default to deny on conflict)
        for pattern in self._NEGATIVE_PATTERNS:
            match = pattern.search(cleaned)
            if match:
                return ParsedIntentResult(
                    decision=ConfirmationDecision.DENIED,
                    confidence=0.95,
                    matched_phrase=match.group(0),
                    raw_input=cleaned,
                )

        # Check affirmative patterns
        for pattern in self._AFFIRMATIVE_PATTERNS:
            match = pattern.search(cleaned)
            if match:
                return ParsedIntentResult(
                    decision=ConfirmationDecision.APPROVED,
                    confidence=0.95,
                    matched_phrase=match.group(0),
                    raw_input=cleaned,
                )

        return ParsedIntentResult(
            decision=ConfirmationDecision.AMBIGUOUS,
            confidence=0.3,
            matched_phrase=None,
            raw_input=cleaned,
        )


# Global singleton instance
conversational_intent_parser = ConversationalIntentParser()
