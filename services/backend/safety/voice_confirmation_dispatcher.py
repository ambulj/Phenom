"""Conversational Voice Confirmation Dispatcher for Phenom (Milestone 29 Phase 3).

Dispatches friendly, spoken confirmation prompts and manages real-time voice
intent resolution for Tier 2 operations (VOICE-01.1, CONFIRM-03.1).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.safety.conversational_intent_parser import (
    conversational_intent_parser,
    ConfirmationDecision,
    ParsedIntentResult,
    Rule8ViolationError,
)

logger = logging.getLogger("phenom.safety.voice_dispatcher")


class ConversationalVoicePrompt(BaseModel):
    prompt_id: str
    tool_name: str
    spoken_question: str
    display_summary: str
    tier: int = 2
    created_at: float = Field(default_factory=time.time)
    timeout_seconds: int = 60


class PendingVoiceConfirmation(BaseModel):
    prompt: ConversationalVoicePrompt
    status: str = "PENDING"  # "PENDING", "APPROVED", "DENIED", "TIMED_OUT", "CANCELLED"
    resolved_at: Optional[float] = None
    decision: Optional[ConfirmationDecision] = None
    raw_user_input: Optional[str] = None
    reason: Optional[str] = None


class VoiceConfirmationDispatcher:
    """Dispatches conversational voice confirmation prompts and tracks resolution state."""

    _RULE_8_PATTERN = re.compile(
        r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._pending: Dict[str, PendingVoiceConfirmation] = {}
        self._futures: Dict[str, asyncio.Future] = {}

    def check_safety(self, text: str) -> None:
        """Enforces Guardian kill switch and Rule 8 payment defenses."""
        if guardian.is_halted:
            raise RuntimeError("Execution halted by Guardian kill switch (VOICE_DISPATCHER_HALTED)")

        if self._RULE_8_PATTERN.search(text):
            raise Rule8ViolationError(
                "Rule 8 Violation: Payment, checkout, or billing directives detected in confirmation payload"
            )

    def synthesize_spoken_prompt(
        self,
        tool_name: str,
        args: Dict[str, Any],
        tier: int = 2,
        prompt_id: Optional[str] = None,
    ) -> ConversationalVoicePrompt:
        """Translates technical tool action and arguments into friendly spoken English."""
        self.check_safety(f"{tool_name} {args}")

        pid = prompt_id or f"voice-conf-{int(time.time() * 1000) % 100000}-{os.urandom(2).hex()}"

        target = (
            args.get("path")
            or args.get("dest")
            or args.get("target")
            or args.get("recipient")
            or args.get("app_name")
            or "target resource"
        )
        if isinstance(target, str) and ("\\" in target or "/" in target):
            target_display = os.path.basename(target) or target
        else:
            target_display = str(target)

        if tool_name in ["recycle_delete", "delete_file"]:
            spoken = f"Bro, should I recycle {target_display} for you?"
            summary = f"Move {target_display} safely to Windows Recycle Bin"
        elif tool_name in ["send_email", "send_email_draft"]:
            recipient = args.get("recipient", "the recipient")
            spoken = f"Bro, do you want me to send this email to {recipient}?"
            summary = f"Send outbound email to {recipient}"
        elif tool_name in ["telegram_broadcast", "telegram_send_remote"]:
            spoken = "Bro, should I broadcast this message to your Telegram channel?"
            summary = "Broadcast remote notification to Telegram"
        elif tool_name in ["modify_registry_key"]:
            spoken = f"Bro, should I update the Windows registry key for {target_display}?"
            summary = f"Modify Windows registry setting: {target_display}"
        else:
            spoken = f"Bro, should I go ahead and run {tool_name} on {target_display}?"
            summary = f"Execute high-risk action: {tool_name} on {target_display}"

        return ConversationalVoicePrompt(
            prompt_id=pid,
            tool_name=tool_name,
            spoken_question=spoken,
            display_summary=summary,
            tier=tier,
            created_at=time.time(),
            timeout_seconds=60,
        )

    def dispatch_confirmation(
        self,
        tool_name: str,
        args: Dict[str, Any],
        tier: int = 2,
    ) -> ConversationalVoicePrompt:
        """Dispatches a new conversational confirmation and records it in pending queue."""
        prompt = self.synthesize_spoken_prompt(tool_name, args, tier=tier)
        pending = PendingVoiceConfirmation(prompt=prompt, status="PENDING")
        self._pending[prompt.prompt_id] = pending
        logger.info(
            "Dispatched voice confirmation [%s]: '%s'",
            prompt.prompt_id,
            prompt.spoken_question,
        )
        return prompt

    def resolve_confirmation(
        self,
        prompt_id: str,
        user_response: str,
    ) -> Dict[str, Any]:
        """Resolves a pending voice confirmation using intent parsing."""
        self.check_safety(f"{prompt_id} {user_response}")

        pending = self._pending.get(prompt_id)
        if not pending:
            raise KeyError(f"No active pending voice confirmation found with ID '{prompt_id}'.")

        # Check if already resolved or timed out
        now = time.time()
        if now - pending.prompt.created_at > pending.prompt.timeout_seconds:
            pending.status = "TIMED_OUT"
            pending.resolved_at = now
            pending.reason = "Confirmation timed out after 60 seconds"
            return {
                "prompt_id": prompt_id,
                "status": "TIMED_OUT",
                "decision": "DENIED",
                "parsed_intent": "TIMED_OUT",
                "spoken_feedback": "Voice confirmation timed out, bro. Operation cancelled.",
            }

        # Parse user intent
        parsed: ParsedIntentResult = conversational_intent_parser.parse_intent(user_response)
        pending.resolved_at = now
        pending.raw_user_input = user_response
        pending.decision = parsed.decision

        if parsed.decision == ConfirmationDecision.APPROVED:
            pending.status = "APPROVED"
            pending.reason = f"Approved via voice/text: '{parsed.matched_phrase}'"
            feedback = "Awesome, bro! Proceeding now."
        elif parsed.decision == ConfirmationDecision.DENIED:
            pending.status = "DENIED"
            pending.reason = f"Denied via voice/text: '{parsed.matched_phrase}'"
            feedback = "No problem, bro! Cancelled."
        else:
            pending.status = "PENDING"
            pending.reason = "Ambiguous response, awaiting clear yes or no"
            feedback = "Sorry bro, didn't catch that. Say 'yes' to proceed or 'no' to cancel."

        return {
            "prompt_id": prompt_id,
            "status": pending.status,
            "decision": parsed.decision.value,
            "parsed_intent": parsed.model_dump(),
            "spoken_feedback": feedback,
        }

    def cancel_confirmation(self, prompt_id: str, reason: str = "Cancelled by user") -> bool:
        """Cancels an active confirmation request."""
        pending = self._pending.get(prompt_id)
        if pending and pending.status == "PENDING":
            pending.status = "CANCELLED"
            pending.resolved_at = time.time()
            pending.reason = reason
            return True
        return False

    def get_active_confirmations(self) -> List[Dict[str, Any]]:
        """Returns all currently pending voice confirmations."""
        self.check_safety("get_active")
        now = time.time()
        active: List[Dict[str, Any]] = []
        for pid, conf in self._pending.items():
            if conf.status == "PENDING":
                if now - conf.prompt.created_at > conf.prompt.timeout_seconds:
                    conf.status = "TIMED_OUT"
                    conf.resolved_at = now
                else:
                    active.append({
                        "prompt_id": pid,
                        "tool_name": conf.prompt.tool_name,
                        "spoken_question": conf.prompt.spoken_question,
                        "display_summary": conf.prompt.display_summary,
                        "tier": conf.prompt.tier,
                        "created_at": conf.prompt.created_at,
                        "time_remaining_seconds": max(0, int(conf.prompt.timeout_seconds - (now - conf.prompt.created_at))),
                    })
        return active


# Global singleton instance
voice_confirmation_dispatcher = VoiceConfirmationDispatcher()
