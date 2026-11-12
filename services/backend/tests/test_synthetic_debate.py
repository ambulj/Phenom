"""
Unit Tests for Synthetic Debate Protocol & Consensus Governance (SWM-01)
Validates weighted scoring formula, early exit, Tier 2+ unanimous gating, security veto,
and user escalation rules.
"""

import pytest

from services.backend.schemas.swarm_debate import (
    SpecialistRole,
    CritiqueVerdict,
    ConsensusVerdict,
    SpecialistCritique,
    SwarmProposal,
)
from services.backend.swarm.synthetic_debate import (
    calculate_consensus,
    SyntheticDebateEngine,
    WEIGHT_SECURITY,
    WEIGHT_ARCHITECT,
    WEIGHT_QA,
    WEIGHT_CODE,
)


def test_weighted_consensus_scoring_formula():
    """Verify exact weighted domain scoring arithmetic."""
    # APPROVE=1.0, REQUEST_CHANGES=0.5, BLOCK=0.0
    critiques = {
        SpecialistRole.SECURITY_AUDITOR.value: SpecialistCritique(
            role=SpecialistRole.SECURITY_AUDITOR, verdict=CritiqueVerdict.APPROVE, confidence=0.9
        ),
        SpecialistRole.LEAD_ARCHITECT.value: SpecialistCritique(
            role=SpecialistRole.LEAD_ARCHITECT, verdict=CritiqueVerdict.APPROVE, confidence=0.9
        ),
        SpecialistRole.QA_ENGINEER.value: SpecialistCritique(
            role=SpecialistRole.QA_ENGINEER, verdict=CritiqueVerdict.APPROVE, confidence=0.9
        ),
        SpecialistRole.CODE_REVIEWER.value: SpecialistCritique(
            role=SpecialistRole.CODE_REVIEWER, verdict=CritiqueVerdict.REQUEST_CHANGES, confidence=0.9
        ),
    }

    # Expected: 0.35*1.0 + 0.30*1.0 + 0.20*1.0 + 0.15*0.5 = 0.35 + 0.30 + 0.20 + 0.075 = 0.925
    expected_score = round(0.35 * 1.0 + 0.30 * 1.0 + 0.20 * 1.0 + 0.15 * 0.5, 4)
    score, verdict, reasons, breakdown = calculate_consensus(critiques, proposal_tier=1)

    assert score == expected_score
    assert verdict == ConsensusVerdict.APPROVED_AUTONOMOUS
    assert breakdown[SpecialistRole.CODE_REVIEWER.value] == 0.5
    assert breakdown[SpecialistRole.SECURITY_AUDITOR.value] == 1.0


def test_tier_2_unanimous_gate_enforcement():
    """Verify Tier 2+ proposal requires unanimous APPROVE from Architect, Security, and QA."""
    # Code Reviewer APPROVE, Security APPROVE, QA APPROVE, Architect REQUEST_CHANGES
    critiques = {
        SpecialistRole.SECURITY_AUDITOR.value: SpecialistCritique(
            role=SpecialistRole.SECURITY_AUDITOR, verdict=CritiqueVerdict.APPROVE, confidence=0.9
        ),
        SpecialistRole.LEAD_ARCHITECT.value: SpecialistCritique(
            role=SpecialistRole.LEAD_ARCHITECT, verdict=CritiqueVerdict.REQUEST_CHANGES, confidence=0.9
        ),
        SpecialistRole.QA_ENGINEER.value: SpecialistCritique(
            role=SpecialistRole.QA_ENGINEER, verdict=CritiqueVerdict.APPROVE, confidence=0.9
        ),
        SpecialistRole.CODE_REVIEWER.value: SpecialistCritique(
            role=SpecialistRole.CODE_REVIEWER, verdict=CritiqueVerdict.APPROVE, confidence=0.9
        ),
    }

    # For Tier 1: score = 0.35*1 + 0.30*0.5 + 0.20*1 + 0.15*1 = 0.35 + 0.15 + 0.20 + 0.15 = 0.85
    # score >= 0.85, so for Tier 1 it would pass autonomous approval
    score, verdict_tier1, reasons_tier1, _ = calculate_consensus(critiques, proposal_tier=1)
    assert score >= 0.85
    assert verdict_tier1 == ConsensusVerdict.APPROVED_AUTONOMOUS

    # But for Tier 2: Architect is not APPROVE -> GATED_PENDING_UNANIMOUS
    score, verdict_tier2, reasons_tier2, _ = calculate_consensus(critiques, proposal_tier=2)
    assert verdict_tier2 == ConsensusVerdict.GATED_PENDING_UNANIMOUS
    assert any("strictly requires unanimous APPROVE" in r for r in reasons_tier2)


def test_security_veto_rule():
    """Verify any Security Auditor BLOCK halts autonomous approval regardless of other votes."""
    critiques = {
        SpecialistRole.SECURITY_AUDITOR.value: SpecialistCritique(
            role=SpecialistRole.SECURITY_AUDITOR, verdict=CritiqueVerdict.BLOCK, confidence=0.99
        ),
        SpecialistRole.LEAD_ARCHITECT.value: SpecialistCritique(
            role=SpecialistRole.LEAD_ARCHITECT, verdict=CritiqueVerdict.APPROVE, confidence=0.95
        ),
        SpecialistRole.QA_ENGINEER.value: SpecialistCritique(
            role=SpecialistRole.QA_ENGINEER, verdict=CritiqueVerdict.APPROVE, confidence=0.95
        ),
        SpecialistRole.CODE_REVIEWER.value: SpecialistCritique(
            role=SpecialistRole.CODE_REVIEWER, verdict=CritiqueVerdict.APPROVE, confidence=0.95
        ),
    }

    score, verdict, reasons, _ = calculate_consensus(critiques, proposal_tier=1)
    # Score = 0.35*0 + 0.30*1 + 0.20*1 + 0.15*1 = 0.65 (< 0.85)
    assert score == 0.65
    assert verdict == ConsensusVerdict.ESCALATED_TO_USER
    assert any("Security Auditor veto" in r for r in reasons)


def test_escalation_threshold_below_85():
    """Verify consensus score below 0.85 escalates to user."""
    # Architect=0.5, QA=0.5, Code=0.5, Security=1.0
    # Score = 0.35*1.0 + 0.30*0.5 + 0.20*0.5 + 0.15*0.5 = 0.35 + 0.15 + 0.10 + 0.075 = 0.675
    critiques = {
        SpecialistRole.SECURITY_AUDITOR.value: SpecialistCritique(
            role=SpecialistRole.SECURITY_AUDITOR, verdict=CritiqueVerdict.APPROVE, confidence=0.9
        ),
        SpecialistRole.LEAD_ARCHITECT.value: SpecialistCritique(
            role=SpecialistRole.LEAD_ARCHITECT, verdict=CritiqueVerdict.REQUEST_CHANGES, confidence=0.8
        ),
        SpecialistRole.QA_ENGINEER.value: SpecialistCritique(
            role=SpecialistRole.QA_ENGINEER, verdict=CritiqueVerdict.REQUEST_CHANGES, confidence=0.8
        ),
        SpecialistRole.CODE_REVIEWER.value: SpecialistCritique(
            role=SpecialistRole.CODE_REVIEWER, verdict=CritiqueVerdict.REQUEST_CHANGES, confidence=0.8
        ),
    }

    score, verdict, reasons, _ = calculate_consensus(critiques, proposal_tier=1)
    assert score < 0.85
    assert verdict == ConsensusVerdict.ESCALATED_TO_USER
    assert any("below autonomous approval threshold" in r for r in reasons)


@pytest.mark.asyncio
async def test_synthetic_debate_engine_early_exit():
    """Verify debate terminates in 1 round upon high confidence unanimous approval."""
    engine = SyntheticDebateEngine()
    proposal = SwarmProposal(
        title="Refactor string utility",
        description="Extract string helper with complete test suite",
        diff="def test_clean(): assert True",
        risk_tier=1
    )

    report = await engine.run_debate(proposal, max_rounds=3)
    assert report.verdict == ConsensusVerdict.APPROVED_AUTONOMOUS
    assert report.final_score == 1.0
    # Should exit early in Round 1
    assert len(report.turns) == 1
    assert "Terminated early" in report.turns[0].turn_summary


@pytest.mark.asyncio
async def test_synthetic_debate_engine_multi_round_and_hard_cap():
    """Verify debate respects max_rounds and hard caps at 3 turns."""
    engine = SyntheticDebateEngine()
    proposal = SwarmProposal(
        title="Complex architectural migration",
        description="Migrate component [request_changes:lead_architect] but include unit test plan",
        risk_tier=1
    )

    # Even if max_rounds=5 is requested, it should be capped at 3
    report = await engine.run_debate(proposal, max_rounds=5)
    assert len(report.turns) <= 3
    assert report.completed_at is not None
