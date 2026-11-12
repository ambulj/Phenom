"""
Phenom Specialist Swarm Orchestrator (SWM-01, SAF-01, SAF-02)
Singleton manager coordinating multi-agent synthetic debate lifecycles, user escalation routing,
Cyber HUD event broadcasts, and sub-25ms synchronous Guardian kill switch termination.
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Any, Callable, Awaitable, Set

from services.backend.schemas.swarm_debate import (
    ConsensusReport,
    ConsensusVerdict,
    SwarmProposal,
    current_iso_time,
)
from services.backend.swarm.synthetic_debate import SyntheticDebateEngine

BroadcasterFn = Callable[[Dict[str, Any]], Awaitable[None]]


class SpecialistSwarmOrchestrator:
    """
    Manages active debates, user escalation state, and kill switch SLA.
    """

    def __init__(self, engine: Optional[SyntheticDebateEngine] = None):
        self._engine = engine or SyntheticDebateEngine()
        self._debates: Dict[str, ConsensusReport] = {}
        self._pending_escalations: Dict[str, asyncio.Future[Tuple[str, Optional[str]]]] = {}
        self._active_tasks: Set[asyncio.Task] = set()
        self._halted: bool = False
        self._broadcaster: Optional[BroadcasterFn] = None

    def register_broadcaster(self, broadcaster: BroadcasterFn) -> None:
        """Registers WebSocket broadcaster for Cyber HUD and client events."""
        self._broadcaster = broadcaster

    @property
    def is_halted(self) -> bool:
        return self._halted

    async def dispatch_debate(
        self,
        proposal: SwarmProposal,
        max_rounds: int = 3,
        await_user_decision: bool = False,
        timeout_seconds: Optional[float] = None
    ) -> ConsensusReport:
        """
        Dispatches multi-agent synthetic debate.
        If consensus is below 85% or gated pending unanimous sign-off, broadcasts
        escalation card to Cyber HUD and creates pending escalation record.
        """
        if self._halted:
            raise PermissionError("Phenom is currently HALTED by Guardian")

        current_task = asyncio.current_task()
        if current_task:
            self._active_tasks.add(current_task)

        try:
            report = await self._engine.run_debate(proposal, max_rounds=max_rounds)
            self._debates[report.debate_id] = report

            # Check if escalation is required
            if report.verdict in [ConsensusVerdict.ESCALATED_TO_USER, ConsensusVerdict.GATED_PENDING_UNANIMOUS]:
                loop = asyncio.get_running_loop()
                fut: asyncio.Future[Tuple[str, Optional[str]]] = loop.create_future()
                self._pending_escalations[report.debate_id] = fut

                # Broadcast escalation event to Cyber HUD
                if self._broadcaster:
                    try:
                        last_turn_critiques = (
                            {k: v.model_dump() for k, v in report.turns[-1].critiques.items()}
                            if report.turns else {}
                        )
                        payload = {
                            "debate_id": report.debate_id,
                            "proposal_title": report.proposal_title,
                            "proposal_description": report.proposal_description,
                            "proposal_diff": report.proposal_diff,
                            "risk_tier": report.risk_tier,
                            "final_score": report.final_score,
                            "verdict": report.verdict.value,
                            "gating_reasons": report.gating_reasons,
                            "specialist_breakdown": report.specialist_breakdown,
                            "turns_count": len(report.turns),
                            "last_turn_critiques": last_turn_critiques,
                            "timestamp": current_iso_time(),
                        }
                        await self._broadcaster({
                            "id": f"swarm-esc-{report.debate_id}",
                            "type": "swarm.debate.escalation",
                            "ts": current_iso_time(),
                            "payload": payload,
                        })
                    except Exception:
                        pass

                if await_user_decision:
                    if timeout_seconds:
                        try:
                            decision, reason = await asyncio.wait_for(fut, timeout=timeout_seconds)
                        except asyncio.TimeoutError:
                            decision, reason = "reject", "Escalation timed out waiting for user input"
                            self.submit_user_decision(report.debate_id, decision, reason)
                    else:
                        decision, reason = await fut
                    return self._debates[report.debate_id]

            return report

        finally:
            if current_task and current_task in self._active_tasks:
                self._active_tasks.remove(current_task)

    def submit_user_decision(
        self,
        debate_id: str,
        decision: str,
        reason: Optional[str] = None
    ) -> ConsensusReport:
        """
        Resolves pending user escalation for a debate.
        Valid decisions: 'approve' or 'reject'.
        """
        if self._halted:
            raise PermissionError("Phenom is currently HALTED by Guardian")

        report = self._debates.get(debate_id)
        if not report:
            raise KeyError(f"Debate '{debate_id}' not found in active records.")

        norm_decision = decision.strip().lower()
        if norm_decision == "approve":
            report.verdict = ConsensusVerdict.APPROVED_BY_USER
        elif norm_decision == "reject":
            report.verdict = ConsensusVerdict.REJECTED_BY_USER
        else:
            raise ValueError(f"Invalid decision '{decision}'. Must be 'approve' or 'reject'.")

        resolution_note = f"User Decision: {norm_decision.upper()}"
        if reason:
            resolution_note += f" - {reason}"
        report.gating_reasons.append(resolution_note)

        # Resolve pending escalation future if present
        if debate_id in self._pending_escalations:
            fut = self._pending_escalations.pop(debate_id)
            if not fut.done():
                fut.set_result((norm_decision, reason))

        # Broadcast decision event if broadcaster is present
        if self._broadcaster:
            try:
                loop = asyncio.get_running_loop()
                if loop and loop.is_running():
                    loop.create_task(self._broadcaster({
                        "id": f"swarm-dec-{debate_id}",
                        "type": "swarm.debate.decision_resolved",
                        "ts": current_iso_time(),
                        "payload": {
                            "debate_id": debate_id,
                            "decision": norm_decision,
                            "verdict": report.verdict.value,
                            "reason": reason,
                        }
                    }))
            except Exception:
                pass

        return report

    def get_debate_status(self, debate_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves status of a specific debate or general summary of all debates.
        """
        if debate_id:
            report = self._debates.get(debate_id)
            if not report:
                return {
                    "found": False,
                    "error": f"Debate ID '{debate_id}' not found."
                }
            return {
                "found": True,
                "debate": report.model_dump(),
                "is_pending_escalation": debate_id in self._pending_escalations,
            }

        return {
            "total_debates": len(self._debates),
            "pending_escalations_count": len(self._pending_escalations),
            "pending_escalation_ids": list(self._pending_escalations.keys()),
            "is_halted": self._halted,
            "recent_debates": [
                {
                    "debate_id": rep.debate_id,
                    "title": rep.proposal_title,
                    "verdict": rep.verdict.value,
                    "score": rep.final_score,
                    "risk_tier": rep.risk_tier,
                    "turns_count": len(rep.turns),
                    "started_at": rep.started_at,
                    "completed_at": rep.completed_at,
                }
                for rep in list(self._debates.values())[-10:]
            ],
        }

    def halt(self) -> None:
        """
        Synchronous kill switch termination.
        Cancels all running debate tasks and rejects pending escalations in < 1.0ms (< 25ms SLA).
        """
        self._halted = True

        # Cancel all active asyncio tasks
        for task in list(self._active_tasks):
            try:
                if not task.done():
                    task.cancel()
            except Exception:
                pass
        self._active_tasks.clear()

        # Reject all pending escalations
        for fut in list(self._pending_escalations.values()):
            try:
                if not fut.done():
                    fut.set_exception(PermissionError("Phenom is currently HALTED by Guardian"))
            except Exception:
                pass
        self._pending_escalations.clear()

        # Mark all pending reports as HALTED
        for report in self._debates.values():
            if report.verdict in [ConsensusVerdict.ESCALATED_TO_USER, ConsensusVerdict.GATED_PENDING_UNANIMOUS]:
                report.verdict = ConsensusVerdict.HALTED
                report.gating_reasons.append("Halted synchronously by Guardian kill switch.")

    def reset(self) -> None:
        """Resets halted state back to idle."""
        self._halted = False
        self._active_tasks.clear()
        self._pending_escalations.clear()


# Global singleton instance
specialist_swarm_orchestrator = SpecialistSwarmOrchestrator()
