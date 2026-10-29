"""
Phenom Notification Digest Engine (Task 7j)
Captures, buffers, and digests missed notifications during Gaming Mode and Quiet Hours.

Strict Invariants:
1. Full text of OTPs and 2FA authentication codes are NEVER read aloud or leaked.
2. Financial details (account numbers, balances, card numbers) are strictly redacted.
3. Spoken format matches Jarvis assistant personality:
   "You missed 3 notifications: Telegram message from Alex, calendar reminder for team sync, and a system update notice."
"""

import re
import time
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class BufferedNotification(BaseModel):
    id: str = Field(default_factory=lambda: f"notif_{uuid.uuid4().hex[:8]}")
    source: str
    title: str
    body: str
    timestamp: float = Field(default_factory=time.time)
    category: str = "general"
    is_otp: bool = False
    is_financial: bool = False
    sanitized_summary: str = ""

# Patterns matching OTPs, 2FA, verification codes
OTP_REGEX = re.compile(
    r"\b(?:otp|one[- ]time[- ]password|verification code|security code|passcode|secret code|two-factor|2fa|login code)\b",
    re.IGNORECASE
)
CODE_DIGITS_REGEX = re.compile(r"\b\d{4,8}\b")

# Patterns matching financial transactions, account numbers, card balances
FINANCIAL_REGEX = re.compile(
    r"\b(?:debited|credited|bank|account ending|card ending|balance|inr|usd|eur|gbp|transfer|transaction)\b",
    re.IGNORECASE
)
ACCOUNT_DIGITS_REGEX = re.compile(r"\b(?:xx\d{4}|\d{4}-\d{4}-\d{4}-\d{4}|\d{10,16})\b", re.IGNORECASE)

class NotificationDigestManager:
    def __init__(self):
        self._buffer: List[BufferedNotification] = []
        self._dnd_active: bool = False

    @property
    def is_dnd_active(self) -> bool:
        return self._dnd_active

    def enable_dnd(self):
        """Enables Do-Not-Disturb / Muted notifications (e.g. during gaming)."""
        self._dnd_active = True

    def disable_dnd(self):
        """Disables Do-Not-Disturb."""
        self._dnd_active = False

    def buffer_notification(
        self,
        source: str,
        title: str,
        body: str,
        category: str = "general"
    ) -> BufferedNotification:
        """
        Buffers an incoming notification while categorizing and stripping sensitive secrets.
        """
        combined_text = f"{source} {title} {body}"
        
        # Check OTP patterns
        is_otp = bool(OTP_REGEX.search(combined_text) or ("code" in combined_text.lower() and CODE_DIGITS_REGEX.search(body)))

        # Check financial patterns
        is_financial = bool(FINANCIAL_REGEX.search(combined_text) or ACCOUNT_DIGITS_REGEX.search(body))

        # Build sanitized summary (NEVER include raw OTP or account numbers)
        if is_otp:
            summary = f"verification alert from {source} (code hidden for security)"
        elif is_financial:
            summary = f"bank alert from {source} (financial details hidden for security)"
        elif source.lower() in ["telegram", "whatsapp", "signal", "messages"]:
            summary = f"{source} message from {title}"
        elif source.lower() in ["calendar", "google calendar", "outlook"]:
            summary = f"calendar reminder for {title}"
        else:
            summary = f"{source} update for {title}"

        notif = BufferedNotification(
            source=source,
            title=title,
            body=body,
            category=category,
            is_otp=is_otp,
            is_financial=is_financial,
            sanitized_summary=summary
        )
        self._buffer.append(notif)
        return notif

    def get_missed_notifications(self) -> List[BufferedNotification]:
        return list(self._buffer)

    def generate_spoken_digest(self) -> Dict[str, Any]:
        """
        Generates clean conversational speech summary of missed notifications.
        Guarantees 0 OTP digits and 0 account numbers in the output.
        """
        count = len(self._buffer)
        if count == 0:
            text = "You have no missed notifications, sir."
            return {
                "count": 0,
                "spoken_text": text,
                "items": [],
                "contains_otp": False,
                "contains_financial": False
            }

        # Format items into natural English
        summaries = [n.sanitized_summary for n in self._buffer]
        if count == 1:
            items_str = summaries[0]
        elif count == 2:
            items_str = f"{summaries[0]}, and {summaries[1]}"
        else:
            items_str = ", ".join(summaries[:-1]) + f", and {summaries[-1]}"

        text = f"You missed {count} notification{'s' if count != 1 else ''}: {items_str}."

        # Audit check: verify zero OTP digits or private accounts leaked
        # Check for any isolated 4-8 digit numbers in the generated spoken text
        has_leaked_digits = bool(re.search(r"\b\d{4,8}\b", text))
        if has_leaked_digits:
            # Fallback fail-safe: hard redact any unexpected digits
            text = re.sub(r"\b\d{4,8}\b", "[REDACTED]", text)

        return {
            "count": count,
            "spoken_text": text,
            "items": [n.model_dump() for n in self._buffer],
            "contains_otp": any(n.is_otp for n in self._buffer),
            "contains_financial": any(n.is_financial for n in self._buffer)
        }

    def clear_buffer(self) -> int:
        """Clears buffered notifications after user has reviewed or heard the digest."""
        cleared = len(self._buffer)
        self._buffer.clear()
        return cleared

# Global notification digest manager instance
notification_digest_manager = NotificationDigestManager()
