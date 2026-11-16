"""Two-Tier Quorum Consensus Engine for Phenom Multi-Agent Swarm.

Phase 48-02: CONS-02.
Mandates dual sign-off from both Coder and Security Auditor (with zero security alerts).
Enforces unilateral Security Auditor veto power and Architect deadlock arbitration.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Union

from services.backend.schemas.swarm_auction import AgentRole
from services.backend.schemas.swarm_consensus import (
    AgentReviewVote,
    FindingSeverity,
    QuorumEvaluationResult,
    QuorumState,
    ReviewVerdict,
)

logger = logging.getLogger("phenom.swarm.consensus_engine")


class TwoTierConsensusEngine:
    """Evaluates multi-agent peer review votes against the strict Two-Tier Quorum rule."""

    @classmethod
    def evaluate_quorum(
        cls,
        votes: Union[List[AgentReviewVote], Dict[AgentRole, AgentReviewVote]],
    ) -> QuorumEvaluationResult:
        """Evaluate consensus across collected agent review votes."""
        vote_dict: Dict[AgentRole, AgentReviewVote] = (
            {v.agent_role: v for v in votes} if isinstance(votes, list) else dict(votes)
        )

        blocking_reasons: List[str] = []
        coder_vote = vote_dict.get(AgentRole.CODER)
        security_vote = vote_dict.get(AgentRole.SECURITY_AUDITOR)
        architect_vote = vote_dict.get(AgentRole.ARCHITECT)

        # 1. Check Missing Essential Votes
        if not coder_vote or not security_vote:
            if not coder_vote:
                blocking_reasons.append("Missing mandatory vote from Coder agent.")
            if not security_vote:
                blocking_reasons.append("Missing mandatory vote from Security Auditor agent.")
            return QuorumEvaluationResult(
                state=QuorumState.INSUFFICIENT_VOTES,
                is_approved=False,
                coder_approved=False,
                security_approved=False,
                votes=vote_dict,
                blocking_reasons=blocking_reasons,
                timestamp=time.time(),
            )

        # 2. Check Security Auditor VETO (Rule 1, Rule 4, Rule 8, Rule 11)
        security_has_critical = any(
            f.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH)
            for f in security_vote.findings
        )
        if security_vote.verdict == ReviewVerdict.REJECT or security_has_critical:
            reason = (
                f"Security Auditor VETO: {len(security_vote.findings)} security violation(s) identified. "
                + "; ".join(f.message for f in security_vote.findings[:3])
            )
            blocking_reasons.append(reason)
            return QuorumEvaluationResult(
                state=QuorumState.VETOED,
                is_approved=False,
                coder_approved=(coder_vote.verdict == ReviewVerdict.APPROVE),
                security_approved=False,
                votes=vote_dict,
                blocking_reasons=blocking_reasons,
                timestamp=time.time(),
            )

        # 3. Check Coder Sign-Off (Functional & AST syntax correctness)
        coder_has_critical = any(
            f.severity == FindingSeverity.CRITICAL for f in coder_vote.findings
        )
        if coder_vote.verdict != ReviewVerdict.APPROVE or coder_has_critical:
            reason = (
                f"Coder Rejected/Requested Changes: {len(coder_vote.findings)} issue(s) identified. "
                + "; ".join(f.message for f in coder_vote.findings[:3])
            )
            blocking_reasons.append(reason)
            return QuorumEvaluationResult(
                state=QuorumState.INSUFFICIENT_VOTES,
                is_approved=False,
                coder_approved=False,
                security_approved=(security_vote.verdict == ReviewVerdict.APPROVE),
                votes=vote_dict,
                blocking_reasons=blocking_reasons,
                timestamp=time.time(),
            )

        # 4. Check for Deadlock (e.g. Auditor requested changes on non-critical items)
        if security_vote.verdict == ReviewVerdict.REQUEST_CHANGES:
            # Deadlock state: Coder passed, but Security Auditor has non-critical reservations
            blocking_reasons.append(
                "Deadlock: Coder approved but Security Auditor requested changes on non-critical findings. Requires Architect arbitration."
            )
            return QuorumEvaluationResult(
                state=QuorumState.DEADLOCKED,
                is_approved=False,
                coder_approved=True,
                security_approved=False,
                votes=vote_dict,
                blocking_reasons=blocking_reasons,
                timestamp=time.time(),
            )

        # 5. Full Two-Tier Quorum Attained
        return QuorumEvaluationResult(
            state=QuorumState.QUORUM_REACHED,
            is_approved=True,
            coder_approved=True,
            security_approved=True,
            architect_arbitrated=False,
            votes=vote_dict,
            blocking_reasons=[],
            timestamp=time.time(),
        )

    @classmethod
    def arbitrate_deadlock(
        cls,
        current_result: QuorumEvaluationResult,
        architect_override: bool,
        arbitration_notes: str,
    ) -> QuorumEvaluationResult:
        """Allow Architect agent to break non-critical deadlocks."""
        if current_result.state != QuorumState.DEADLOCKED:
            raise ValueError(
                f"Cannot arbitrate quorum in state '{current_result.state.value}'. Only DEADLOCKED states may be arbitrated."
            )

        if architect_override:
            logger.info("Architect resolved deadlock with APPROVAL: %s", arbitration_notes)
            return QuorumEvaluationResult(
                state=QuorumState.QUORUM_REACHED,
                is_approved=True,
                coder_approved=current_result.coder_approved,
                security_approved=current_result.security_approved,
                architect_arbitrated=True,
                votes=current_result.votes,
                blocking_reasons=[],
                timestamp=time.time(),
            )
        else:
            logger.info("Architect resolved deadlock with REJECTION: %s", arbitration_notes)
            return QuorumEvaluationResult(
                state=QuorumState.INSUFFICIENT_VOTES,
                is_approved=False,
                coder_approved=current_result.coder_approved,
                security_approved=current_result.security_approved,
                architect_arbitrated=True,
                votes=current_result.votes,
                blocking_reasons=[f"Architect upheld reservations: {arbitration_notes}"],
                timestamp=time.time(),
            )
