"""
Unit Tests for Phenom Specialist Swarm Orchestrator (SWM-01)
Validates debate lifecycle, escalation event broadcasting, user decision resolution,
and orchestrator query endpoints.
"""

import pytest
import asyncio
from typing import Dict, Any

from services.backend.schemas.swarm_debate import (
    SwarmProposal,
    ConsensusVerdict,
)
from services.backend.swarm.specialist_orchestrator import SpecialistSwarmOrchestrator


@pytest.mark.asyncio
async def test_dispatch_debate_autonomous_approval():
    """Verify clean proposal dispatches and returns autonomous approval without escalation."""
    orchestrator = SpecialistSwarmOrchestrator()
    proposal = SwarmProposal(
        title="Extract math helper",
        description="Add clean math helper with complete pytest test suite",
        diff="def test_add(): assert 1 + 1 == 2",
        risk_tier=1
    )

    report = await orchestrator.dispatch_debate(proposal, max_rounds=2)
    assert report.verdict == ConsensusVerdict.APPROVED_AUTONOMOUS
    assert report.final_score == 1.0

    # Debate is recorded in history
    status = orchestrator.get_debate_status(report.debate_id)
    assert status["found"] is True
    assert status["debate"]["debate_id"] == report.debate_id
    assert status["is_pending_escalation"] is False


@pytest.mark.asyncio
async def test_dispatch_debate_escalation_and_user_decision():
    """Verify low-consensus or blocked proposal creates escalation and resolves via user decision."""
    orchestrator = SpecialistSwarmOrchestrator()
    broadcast_events = []

    async def mock_broadcaster(msg: Dict[str, Any]):
        broadcast_events.append(msg)

    orchestrator.register_broadcaster(mock_broadcaster)

    # Proposal with blocked security rule
    bad_proposal = SwarmProposal(
        title="Format hard drive",
        description="Wipe directory using os.remove and rm -rf",
        risk_tier=2
    )

    # Dispatch debate (non-blocking resolution)
    report = await orchestrator.dispatch_debate(bad_proposal, max_rounds=1)
    assert report.verdict == ConsensusVerdict.GATED_PENDING_UNANIMOUS

    # Verify WebSocket broadcast was dispatched
    assert len(broadcast_events) == 1
    assert broadcast_events[0]["type"] == "swarm.debate.escalation"
    assert broadcast_events[0]["payload"]["debate_id"] == report.debate_id

    # Verify status reports pending escalation
    status = orchestrator.get_debate_status(report.debate_id)
    assert status["found"] is True
    assert status["is_pending_escalation"] is True

    # Submit user override decision
    updated_report = orchestrator.submit_user_decision(
        debate_id=report.debate_id,
        decision="approve",
        reason="Manual operator verified clean sandbox environment"
    )

    assert updated_report.verdict == ConsensusVerdict.APPROVED_BY_USER
    assert any("APPROVE" in r for r in updated_report.gating_reasons)

    # Verify escalation is no longer pending
    status_after = orchestrator.get_debate_status(report.debate_id)
    assert status_after["is_pending_escalation"] is False


@pytest.mark.asyncio
async def test_submit_user_decision_rejection():
    """Verify user rejection updates debate status to REJECTED_BY_USER."""
    orchestrator = SpecialistSwarmOrchestrator()
    proposal = SwarmProposal(
        title="Unverified API integration",
        description="Introduce integration [simulate_block]",
        risk_tier=1
    )

    report = await orchestrator.dispatch_debate(proposal, max_rounds=1)
    assert report.verdict in [ConsensusVerdict.ESCALATED_TO_USER, ConsensusVerdict.GATED_PENDING_UNANIMOUS]

    updated_report = orchestrator.submit_user_decision(
        debate_id=report.debate_id,
        decision="reject",
        reason="Risk unacceptable"
    )
    assert updated_report.verdict == ConsensusVerdict.REJECTED_BY_USER


@pytest.mark.asyncio
async def test_invalid_decision_validation():
    """Verify invalid decision strings raise ValueError."""
    orchestrator = SpecialistSwarmOrchestrator()
    proposal = SwarmProposal(
        title="Test proposal",
        description="Some changes [simulate_block]",
        risk_tier=1
    )
    report = await orchestrator.dispatch_debate(proposal, max_rounds=1)

    with pytest.raises(ValueError):
        orchestrator.submit_user_decision(report.debate_id, "maybe")


def test_get_debate_status_summary():
    """Verify get_debate_status without args returns summary list."""
    orchestrator = SpecialistSwarmOrchestrator()
    summary = orchestrator.get_debate_status()
    assert "total_debates" in summary
    assert "pending_escalations_count" in summary
    assert "recent_debates" in summary
