"""
Unit Tests for Phenom Specialist Swarm Schemas & Personas (SWM-01)
Validates Pydantic schema constraints, enum values, and persona evaluation outputs.
"""

import pytest
from pydantic import ValidationError

from services.backend.schemas.swarm_debate import (
    SpecialistRole,
    CritiqueVerdict,
    ConsensusVerdict,
    SpecialistCritique,
    DebateTurn,
    ConsensusReport,
    SwarmProposal,
    SwarmDispatchSpecialistsArgs,
    SwarmGetDebateStatusArgs,
    SwarmSubmitUserDecisionArgs,
)
from services.backend.swarm.specialist_personas import evaluate_proposal, SPECIALIST_PROMPTS


def test_specialist_enums():
    """Verify enum members exist and match expected string values."""
    assert SpecialistRole.LEAD_ARCHITECT.value == "lead_architect"
    assert SpecialistRole.CODE_REVIEWER.value == "code_reviewer"
    assert SpecialistRole.SECURITY_AUDITOR.value == "security_auditor"
    assert SpecialistRole.QA_ENGINEER.value == "qa_engineer"

    assert CritiqueVerdict.APPROVE.value == "APPROVE"
    assert CritiqueVerdict.REQUEST_CHANGES.value == "REQUEST_CHANGES"
    assert CritiqueVerdict.BLOCK.value == "BLOCK"

    assert ConsensusVerdict.APPROVED_AUTONOMOUS.value == "APPROVED_AUTONOMOUS"
    assert ConsensusVerdict.GATED_PENDING_UNANIMOUS.value == "GATED_PENDING_UNANIMOUS"
    assert ConsensusVerdict.ESCALATED_TO_USER.value == "ESCALATED_TO_USER"
    assert ConsensusVerdict.HALTED.value == "HALTED"


def test_specialist_critique_schema_validation():
    """Verify SpecialistCritique model validates confidence bounds and fields."""
    critique = SpecialistCritique(
        role=SpecialistRole.LEAD_ARCHITECT,
        verdict=CritiqueVerdict.APPROVE,
        confidence=0.95,
        strengths=["Solid modular boundaries"],
        concerns=[],
        recommendations=["Continue with current layout"]
    )
    assert critique.role == SpecialistRole.LEAD_ARCHITECT
    assert critique.confidence == 0.95
    assert len(critique.strengths) == 1

    # Confidence must be between 0.0 and 1.0
    with pytest.raises(ValidationError):
        SpecialistCritique(
            role=SpecialistRole.CODE_REVIEWER,
            verdict=CritiqueVerdict.APPROVE,
            confidence=1.5  # Invalid > 1.0
        )

    with pytest.raises(ValidationError):
        SpecialistCritique(
            role=SpecialistRole.CODE_REVIEWER,
            verdict=CritiqueVerdict.APPROVE,
            confidence=-0.1  # Invalid < 0.0
        )


def test_debate_turn_and_consensus_report_schema():
    """Verify DebateTurn and ConsensusReport serialization and validation."""
    critiques = {
        "lead_architect": SpecialistCritique(
            role=SpecialistRole.LEAD_ARCHITECT,
            verdict=CritiqueVerdict.APPROVE,
            confidence=0.9
        ),
        "security_auditor": SpecialistCritique(
            role=SpecialistRole.SECURITY_AUDITOR,
            verdict=CritiqueVerdict.APPROVE,
            confidence=0.95
        )
    }

    turn = DebateTurn(
        round_number=1,
        critiques=critiques,
        cross_rebuttals=["Security accepts architecture"],
        turn_summary="Round 1 completed with consensus"
    )
    assert turn.round_number == 1
    assert "lead_architect" in turn.critiques

    # Round number must be between 1 and 3
    with pytest.raises(ValidationError):
        DebateTurn(round_number=4, critiques={})

    report = ConsensusReport(
        proposal_title="Add caching layer",
        proposal_description="Implement in-memory LRU cache",
        turns=[turn],
        final_score=0.92,
        verdict=ConsensusVerdict.APPROVED_AUTONOMOUS,
        specialist_breakdown={"lead_architect": 1.0, "security_auditor": 1.0}
    )
    assert report.verdict == ConsensusVerdict.APPROVED_AUTONOMOUS
    assert report.final_score == 0.92
    assert len(report.turns) == 1


def test_tool_args_schemas():
    """Verify tool argument models validate correctly."""
    dispatch_args = SwarmDispatchSpecialistsArgs(
        title="Refactor auth",
        description="Enhance token expiry",
        risk_tier=1,
        max_rounds=2
    )
    assert dispatch_args.max_rounds == 2
    assert dispatch_args.risk_tier == 1

    status_args = SwarmGetDebateStatusArgs()
    assert status_args.debate_id is None

    decision_args = SwarmSubmitUserDecisionArgs(
        debate_id="test-123",
        decision="approve",
        reason="Manual user override verified"
    )
    assert decision_args.decision == "approve"


@pytest.mark.asyncio
async def test_specialist_persona_evaluation_security_violation():
    """Verify Security Auditor blocks permanent deletion violations (Rule 7)."""
    bad_proposal = SwarmProposal(
        title="Clean temp files",
        description="Use os.remove and rm -rf to wipe folder completely",
        risk_tier=2
    )

    critique = await evaluate_proposal(SpecialistRole.SECURITY_AUDITOR, bad_proposal)
    assert critique.role == SpecialistRole.SECURITY_AUDITOR
    assert critique.verdict == CritiqueVerdict.BLOCK
    assert any("Rule 7" in c for c in critique.concerns)


@pytest.mark.asyncio
async def test_specialist_persona_evaluation_clean_proposal():
    """Verify clean proposal receives APPROVE from all 4 specialists."""
    good_proposal = SwarmProposal(
        title="Add health check endpoint",
        description="FastAPI endpoint returning JSON system status with comprehensive pytest suite",
        diff="def test_health(): assert True",
        risk_tier=1
    )

    for role in SpecialistRole:
        critique = await evaluate_proposal(role, good_proposal)
        assert critique.verdict == CritiqueVerdict.APPROVE
        assert critique.confidence >= 0.80
        assert len(critique.strengths) > 0
