"""
Consensus Governance & Safety Gating Verification Suites (SWM-01, SAF-01)
Rigorous validation of:
1. Strict Tier 2+ Unanimous Gate (Architect, Security, QA).
2. Security Auditor Unilateral Veto.
3. Sub-85% User Escalation Threshold.
4. Early Convergence on Unanimous Consensus.
"""

import pytest

from services.backend.schemas.swarm_debate import (
    SpecialistRole,
    CritiqueVerdict,
    ConsensusVerdict,
    SpecialistCritique,
    SwarmProposal,
)
from services.backend.swarm.synthetic_debate import calculate_consensus, SyntheticDebateEngine


def create_critiques(sec: CritiqueVerdict, arch: CritiqueVerdict, qa: CritiqueVerdict, code: CritiqueVerdict):
    return {
        SpecialistRole.SECURITY_AUDITOR.value: SpecialistCritique(
            role=SpecialistRole.SECURITY_AUDITOR, verdict=sec, confidence=0.9
        ),
        SpecialistRole.LEAD_ARCHITECT.value: SpecialistCritique(
            role=SpecialistRole.LEAD_ARCHITECT, verdict=arch, confidence=0.9
        ),
        SpecialistRole.QA_ENGINEER.value: SpecialistCritique(
            role=SpecialistRole.QA_ENGINEER, verdict=qa, confidence=0.9
        ),
        SpecialistRole.CODE_REVIEWER.value: SpecialistCritique(
            role=SpecialistRole.CODE_REVIEWER, verdict=code, confidence=0.9
        ),
    }


def test_tier_2_unanimous_gate_architect_dissent():
    """Tier 2 proposal with Architect dissenting is gated despite high score."""
    critiques = create_critiques(
        sec=CritiqueVerdict.APPROVE,
        arch=CritiqueVerdict.REQUEST_CHANGES,
        qa=CritiqueVerdict.APPROVE,
        code=CritiqueVerdict.APPROVE
    )
    score, verdict, reasons, _ = calculate_consensus(critiques, proposal_tier=2)
    assert score == 0.85
    assert verdict == ConsensusVerdict.GATED_PENDING_UNANIMOUS
    assert any("Lead Architect" in r for r in reasons)


def test_tier_2_unanimous_gate_qa_dissent():
    """Tier 2 proposal with QA dissenting is gated."""
    critiques = create_critiques(
        sec=CritiqueVerdict.APPROVE,
        arch=CritiqueVerdict.APPROVE,
        qa=CritiqueVerdict.REQUEST_CHANGES,
        code=CritiqueVerdict.APPROVE
    )
    score, verdict, reasons, _ = calculate_consensus(critiques, proposal_tier=2)
    assert score == 0.90
    assert verdict == ConsensusVerdict.GATED_PENDING_UNANIMOUS
    assert any("QA Engineer" in r for r in reasons)


def test_tier_2_unanimous_gate_code_reviewer_non_blocking():
    """Tier 2 proposal with Code Reviewer REQUEST_CHANGES passes if Architect, Security, and QA approve."""
    critiques = create_critiques(
        sec=CritiqueVerdict.APPROVE,
        arch=CritiqueVerdict.APPROVE,
        qa=CritiqueVerdict.APPROVE,
        code=CritiqueVerdict.REQUEST_CHANGES
    )
    # Score = 0.35 + 0.30 + 0.20 + 0.075 = 0.925 (>= 0.85)
    score, verdict, reasons, _ = calculate_consensus(critiques, proposal_tier=2)
    assert score == 0.925
    assert verdict == ConsensusVerdict.APPROVED_AUTONOMOUS
    assert len(reasons) == 0


def test_security_veto_in_tier_1_and_tier_2():
    """Security Auditor BLOCK must veto in both Tier 1 and Tier 2."""
    critiques = create_critiques(
        sec=CritiqueVerdict.BLOCK,
        arch=CritiqueVerdict.APPROVE,
        qa=CritiqueVerdict.APPROVE,
        code=CritiqueVerdict.APPROVE
    )

    # Tier 1
    score1, verdict1, reasons1, _ = calculate_consensus(critiques, proposal_tier=1)
    assert score1 == 0.65
    assert verdict1 == ConsensusVerdict.ESCALATED_TO_USER
    assert any("Security Auditor veto" in r for r in reasons1)

    # Tier 2
    score2, verdict2, reasons2, _ = calculate_consensus(critiques, proposal_tier=2)
    assert score2 == 0.65
    assert verdict2 == ConsensusVerdict.GATED_PENDING_UNANIMOUS
    assert any("Security Auditor veto" in r for r in reasons2)


def test_escalation_threshold_boundaries():
    """Verify consensus score boundary at exactly 0.85."""
    # Score = 0.85 exactly: Security=1.0 (0.35), Arch=0.5 (0.15), QA=1.0 (0.20), Code=1.0 (0.15) = 0.85
    critiques_exact = create_critiques(
        sec=CritiqueVerdict.APPROVE,
        arch=CritiqueVerdict.REQUEST_CHANGES,
        qa=CritiqueVerdict.APPROVE,
        code=CritiqueVerdict.APPROVE
    )
    score, verdict, _, _ = calculate_consensus(critiques_exact, proposal_tier=1)
    assert score == 0.85
    assert verdict == ConsensusVerdict.APPROVED_AUTONOMOUS

    # Score = 0.8499 or slightly below: Code Reviewer BLOCK -> Code=0.0 -> score = 0.35 + 0.30 + 0.20 + 0.0 = 0.85
    # Let's make QA REQUEST_CHANGES (0.5) -> QA=0.10, Code=0.15, Arch=0.30, Sec=0.35 -> sum = 0.90
    # Make QA=0.5 (0.10) and Code=0.5 (0.075) -> score = 0.35 + 0.30 + 0.10 + 0.075 = 0.825 (< 0.85)
    critiques_below = create_critiques(
        sec=CritiqueVerdict.APPROVE,
        arch=CritiqueVerdict.APPROVE,
        qa=CritiqueVerdict.REQUEST_CHANGES,
        code=CritiqueVerdict.REQUEST_CHANGES
    )
    score_below, verdict_below, reasons_below, _ = calculate_consensus(critiques_below, proposal_tier=1)
    assert score_below == 0.825
    assert verdict_below == ConsensusVerdict.ESCALATED_TO_USER
    assert any("below autonomous approval threshold" in r for r in reasons_below)


@pytest.mark.asyncio
async def test_full_debate_early_exit_on_unanimous():
    """Verify engine runs only 1 round when all specialists approve with score >= 0.95."""
    engine = SyntheticDebateEngine()
    proposal = SwarmProposal(
        title="Safe clean patch",
        description="Add helper function with unit tests and typed schemas",
        diff="def test_example(): assert True",
        risk_tier=1
    )

    report = await engine.run_debate(proposal, max_rounds=3)
    assert len(report.turns) == 1
    assert report.verdict == ConsensusVerdict.APPROVED_AUTONOMOUS
    assert report.final_score == 1.0
