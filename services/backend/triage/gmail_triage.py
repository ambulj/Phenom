"""Real Gmail Unread Priority Thread Triage & Automated Drafter for Phenom.

Ingests unread messages via SSL IMAP (read-only EXAMINE), scores urgency,
and saves proposed reply drafts into [Gmail]/Drafts (EXE-01).
Phenom Rule 9: Email drafts only, never send. No SMTP is used or imported.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from services.backend.integrations.google_workspace import (
    GoogleWorkspaceClient,
    google_workspace,
    EmailSendingProhibitedError,
)
from services.backend.proactive.dispatcher import (
    ProactiveEventDispatcher,
    ProactiveCard,
    ProactivePriority,
    proactive_dispatcher,
)

logger = logging.getLogger(__name__)

URGENT_KEYWORDS = [
    "urgent",
    "asap",
    "deadline",
    "action required",
    "immediately",
    "critical",
    "priority",
    "important",
    "by today",
    "eod",
]

ACTION_PHRASES = [
    "can you",
    "could you",
    "please review",
    "please send",
    "please find",
    "let me know",
    "thoughts?",
    "feedback",
]


class EmailTriageItem(BaseModel):
    """Structured representation of a triaged email message."""

    id: str = Field(..., description="Message UID or ID")
    sender: str = Field(..., description="Sender email address or display name")
    subject: str = Field(default="", description="Subject line")
    date: str = Field(default="", description="Date string")
    snippet: str = Field(default="", description="First lines of message content")
    priority_score: int = Field(default=1, description="1: Low/Normal, 2: Priority, 3: Urgent")
    suggested_reply: Optional[str] = Field(default=None, description="Proposed draft text")
    draft_saved: bool = Field(default=False, description="True if saved into [Gmail]/Drafts")


class GmailTriageService:
    """Monitors Gmail inbox, triages unread messages, and creates drafts for review."""

    def __init__(
        self,
        workspace_client: Optional[GoogleWorkspaceClient] = None,
        dispatcher: Optional[ProactiveEventDispatcher] = None,
        poll_interval: float = 300.0,
    ) -> None:
        self.workspace_client = workspace_client or google_workspace
        self.dispatcher = dispatcher or proactive_dispatcher
        self.poll_interval = poll_interval

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._processed_msg_ids: Set[str] = set()

    def score_urgency(self, subject: str, snippet: str, sender: str) -> int:
        """Score message priority (1 = Low/Normal, 2 = Priority, 3 = Urgent)."""
        combined = f"{subject} {snippet}".lower()
        score = 1

        if any(kw in combined for kw in URGENT_KEYWORDS):
            score += 2

        if "?" in combined or any(phrase in combined for phrase in ACTION_PHRASES):
            score += 1

        return min(3, score)

    def compose_suggested_reply(self, subject: str, sender: str, snippet: str) -> str:
        """Compose a polite, professional Jarvis-style draft reply."""
        clean_subject = subject.replace("Re:", "").replace("RE:", "").strip()
        body = (
            f"Hi,\n\n"
            f"Thank you for your note regarding '{clean_subject}'.\n\n"
            f"I have received your message and am currently reviewing the details. "
            f"I will follow up with you shortly.\n\n"
            f"Best regards,\n"
            f"Phenom Executive Assistant"
        )
        return body

    async def triage_unread_emails(self, max_results: int = 10, auto_draft: bool = True) -> List[EmailTriageItem]:
        """Triage unread messages, score priority, and optionally create draft replies."""
        # Query unread emails via read-only IMAP (EXAMINE INBOX)
        raw_emails = await asyncio.to_thread(
            self.workspace_client.search_emails,
            query="is:unread",
            max_results=max_results,
        )

        items: List[EmailTriageItem] = []

        for msg in raw_emails:
            msg_id = str(msg.get("id") or msg.get("uid") or "")
            sender = msg.get("from") or msg.get("sender") or "Unknown Sender"
            subject = msg.get("subject") or "(No Subject)"
            snippet = msg.get("snippet") or msg.get("body", "")[:200]
            date_str = msg.get("date") or ""

            score = self.score_urgency(subject, snippet, sender)
            suggested_reply = self.compose_suggested_reply(subject, sender, snippet)
            draft_saved = False

            # Auto-create draft in Gmail Drafts for priority/urgent emails (Rule 9 compliant)
            if auto_draft and score >= 2 and msg_id not in self._processed_msg_ids:
                try:
                    await asyncio.to_thread(
                        self.workspace_client.save_draft,
                        to=sender,
                        subject=f"Re: {subject}",
                        body=suggested_reply,
                    )
                    draft_saved = True
                    logger.info("Created draft reply in [Gmail]/Drafts for message '%s'", subject)
                except Exception as exc:
                    logger.warning("Could not create IMAP draft for message '%s': %s", subject, exc)

            triage_item = EmailTriageItem(
                id=msg_id,
                sender=sender,
                subject=subject,
                date=date_str,
                snippet=snippet,
                priority_score=score,
                suggested_reply=suggested_reply,
                draft_saved=draft_saved,
            )
            items.append(triage_item)

            # If high urgency and not yet alerted, dispatch proactive card
            if score >= 2 and msg_id not in self._processed_msg_ids:
                self._processed_msg_ids.add(msg_id)
                priority_enum = ProactivePriority.URGENT if score == 3 else ProactivePriority.NORMAL
                card = ProactiveCard(
                    event_type="EMAIL_TRIAGE",
                    priority=priority_enum,
                    title=f"Priority Email: {subject[:40]}",
                    description=f"From {sender}: {snippet[:120]}...",
                    action_chip="Review in Gmail",
                    action_payload={"message_id": msg_id, "subject": subject, "draft_saved": draft_saved},
                )
                await self.dispatcher.dispatch(card)

        return items

    async def _run_loop(self) -> None:
        """Background inbox monitoring loop."""
        logger.info("GmailTriageService background loop started (interval=%.1fs)", self.poll_interval)
        while self._running:
            try:
                await self.triage_unread_emails(max_results=15, auto_draft=True)
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("GmailTriageService loop exception: %s", exc)
                await asyncio.sleep(self.poll_interval)

    def start(self) -> None:
        """Start background inbox monitoring."""
        if self._running:
            return
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._run_loop())
        except RuntimeError:
            logger.debug("No running event loop; Gmail triage will start when loop runs.")

    def stop(self) -> None:
        """Gracefully stop inbox monitoring."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

    def halt(self) -> None:
        """Synchronous Guardian halt callback (< 5ms SLA)."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None


gmail_triage = GmailTriageService()
