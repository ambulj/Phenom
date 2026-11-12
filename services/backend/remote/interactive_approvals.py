"""
Interactive Telegram Approvals Engine.
Manages remote Tier 1 & Tier 2 action approval tickets, formatting rich inline
keyboards, tracking expiration, and unblocking awaiting desktop tool futures.

Part of Phenom 21.0 Sovereign Omnimodal Intelligence (TEL-04.2 / REM-02.1).
"""

import time
import uuid
import asyncio
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian


class ApprovalTicket(BaseModel):
    ticket_id: str = Field(..., description="Unique ticket identifier")
    action_name: str = Field(..., description="Tool or action name requesting approval")
    tier: int = Field(..., description="Safety tier: 1 or 2")
    tool_args: Dict[str, Any] = Field(default_factory=dict, description="Sanitized action arguments")
    preview_text: str = Field(..., description="Human-readable preview of proposed changes")
    status: str = Field(default="pending", description="pending, approved, rejected, expired")
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")
    expires_at: float = Field(..., description="Expiration timestamp")
    resolution_time: Optional[float] = Field(default=None, description="When decision was rendered")
    resolved_by: Optional[str] = Field(default=None, description="Remote Telegram user ID or 'desktop'")


class InteractiveApprovalManager:
    """
    Coordinates remote authorization tickets for desktop actions via Telegram inline keyboards.
    """

    DEFAULT_TIMEOUT_SEC = 300.0  # 5 minutes

    def __init__(self):
        self._tickets: Dict[str, ApprovalTicket] = {}
        self._futures: Dict[str, asyncio.Future] = {}

    def create_ticket(
        self,
        action_name: str,
        tier: int,
        preview_text: str,
        tool_args: Optional[Dict[str, Any]] = None,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    ) -> ApprovalTicket:
        """Creates an approval ticket and registers an async waiting future."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Ticket creation blocked.")

        ticket_id = f"appr_{uuid.uuid4().hex[:8]}"
        now = time.time()
        ticket = ApprovalTicket(
            ticket_id=ticket_id,
            action_name=action_name,
            tier=tier,
            tool_args=tool_args or {},
            preview_text=preview_text,
            status="pending",
            created_at=now,
            expires_at=now + timeout_sec,
        )

        self._tickets[ticket_id] = ticket

        # Create future in current event loop if available
        try:
            loop = asyncio.get_running_loop()
            self._futures[ticket_id] = loop.create_future()
        except RuntimeError:
            pass

        return ticket

    def format_inline_keyboard(self, ticket: ApprovalTicket) -> Dict[str, Any]:
        """Generates Telegram inline keyboard markup for approval decision buttons."""
        return {
            "inline_keyboard": [
                [
                    {"text": "Approve ✅", "callback_data": f"approve:{ticket.ticket_id}"},
                    {"text": "Reject ❌", "callback_data": f"reject:{ticket.ticket_id}"}
                ],
                [
                    {"text": "Inspect Details 🔍", "callback_data": f"inspect:{ticket.ticket_id}"}
                ]
            ]
        }

    def resolve_ticket(
        self,
        ticket_id: str,
        decision: str,
        resolved_by: str = "telegram"
    ) -> bool:
        """
        Resolves a pending ticket ('approved' or 'rejected') and completes waiting future.
        """
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return False

        if ticket.status != "pending":
            return False

        # Expiration check
        if time.time() > ticket.expires_at:
            ticket.status = "expired"
            fut = self._futures.get(ticket_id)
            if fut and not fut.done():
                fut.set_result("expired")
            return False

        norm_decision = "approved" if decision.lower() in ("approve", "approved", "yes") else "rejected"
        ticket.status = norm_decision
        ticket.resolution_time = time.time()
        ticket.resolved_by = resolved_by

        fut = self._futures.get(ticket_id)
        if fut and not fut.done():
            fut.set_result(norm_decision)

        return True

    async def wait_for_decision(self, ticket_id: str, timeout_sec: Optional[float] = None) -> str:
        """
        Asynchronously waits for ticket approval, rejection, or timeout.
        """
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return "not_found"

        fut = self._futures.get(ticket_id)
        if not fut:
            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            self._futures[ticket_id] = fut

        eff_timeout = timeout_sec or max(1.0, ticket.expires_at - time.time())

        try:
            decision = await asyncio.wait_for(fut, timeout=eff_timeout)
            return decision
        except asyncio.TimeoutError:
            ticket.status = "expired"
            return "expired"

    def list_pending(self) -> List[ApprovalTicket]:
        """Returns all currently pending unexpired tickets."""
        now = time.time()
        pending = []
        for t in self._tickets.values():
            if t.status == "pending":
                if now > t.expires_at:
                    t.status = "expired"
                else:
                    pending.append(t)
        return pending

    def prune_expired(self) -> int:
        """Marks expired tickets and cleans up completed futures."""
        now = time.time()
        expired_count = 0
        for tid, t in list(self._tickets.items()):
            if t.status == "pending" and now > t.expires_at:
                t.status = "expired"
                expired_count += 1
                fut = self._futures.get(tid)
                if fut and not fut.done():
                    fut.set_result("expired")
        return expired_count


# Global singleton
interactive_approval_manager = InteractiveApprovalManager()
