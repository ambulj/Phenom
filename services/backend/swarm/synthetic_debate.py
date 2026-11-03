"""
Phenom Multi-Turn Synthetic Debate Protocol & Consensus Governance Engine (SWM-01)
Executes concurrent specialist reviews, multi-turn cross-critique, weighted domain consensus scoring,
strict Tier 2+ unanimous gating, security veto enforcement, and user escalation routing.
"""

import asyncio
from typing import Dict, List, Tuple, Optional

from services.backend.schemas.swarm_debate import (
    SpecialistRole,
    CritiqueVerdict,
    ConsensusVerdict,
    SpecialistCritique,
    DebateTurn,
    ConsensusReport,
    SwarmProposal,
    current_iso_time,
    generate_id,
)
from services.backend.swarm.specialist_personas import evaluate_proposal

# Domain Weights: Security (35%), Architect (30%), QA (20%), Code (15%)
WEIGHT_SECURITY = 0.35
WEIGHT_ARCHITECT = 0.30
WEIGHT_QA = 0.20
WEIGHT_CODE = 0.15

VERDICT_VALUES = {
    CritiqueVerdict.APPROVE: 1.0,
    CritiqueVerdict.REQUEST_CHANGES: 0.5,
    CritiqueVerdict.BLOCK: 0.0,
}


def calculate_consensus(
    critiques: Dict[str, SpecialistCritique],
    proposal_tier: int
) -> Tuple[float, ConsensusVerdict, List[str], Dict[str, float]]:
    """
    Computes weighted multi-agent consensus score and evaluates governance rules:
    - Weighted Formula: 0.35*security + 0.30*architect + 0.20*qa + 0.15*code
    - Strict Tier 2+ Unanimous Gate: If tier >= 2, Architect, Security, and QA must ALL be APPROVE.
    - Security Veto: Any Security Auditor BLOCK halts autonomous approval.
    - Escalation Threshold: If score < 0.85, escalate to user.
    """
    gating_reasons: List[str] = []

    # Extract verdicts with defaults if any missing
    sec_critique = critiques.get(SpecialistRole.SECURITY_AUDITOR.value)
    arch_critique = critiques.get(SpecialistRole.LEAD_ARCHITECT.value)
    qa_critique = critiques.get(SpecialistRole.QA_ENGINEER.value)
    code_critique = critiques.get(SpecialistRole.CODE_REVIEWER.value)

    sec_val = VERDICT_VALUES.get(sec_critique.verdict, 0.0) if sec_critique else 0.0
    arch_val = VERDICT_VALUES.get(arch_critique.verdict, 0.0) if arch_critique else 0.0
    qa_val = VERDICT_VALUES.get(qa_critique.verdict, 0.0) if qa_critique else 0.0
    code_val = VERDICT_VALUES.get(code_critique.verdict, 0.0) if code_critique else 0.0

    breakdown = {
        SpecialistRole.SECURITY_AUDITOR.value: sec_val,
        SpecialistRole.LEAD_ARCHITECT.value: arch_val,
        SpecialistRole.QA_ENGINEER.value: qa_val,
        SpecialistRole.CODE_REVIEWER.value: code_val,
    }

    raw_score = (
        WEIGHT_SECURITY * sec_val +
        WEIGHT_ARCHITECT * arch_val +
        WEIGHT_QA * qa_val +
        WEIGHT_CODE * code_val
    )
    score = round(min(max(raw_score, 0.0), 1.0), 4)

    verdict = ConsensusVerdict.APPROVED_AUTONOMOUS

    # 1. Security Veto Rule
    has_security_veto = sec_critique and sec_critique.verdict == CritiqueVerdict.BLOCK
    if has_security_veto:
        gating_reasons.append("Security Auditor veto: proposal contains blocking safety violation.")

    # 2. Strict Tier 2+ Unanimous Gate Rule
    is_gated_tier2 = False
    if proposal_tier >= 2:
        non_approving: List[str] = []
        for role in [SpecialistRole.SECURITY_AUDITOR, SpecialistRole.LEAD_ARCHITECT, SpecialistRole.QA_ENGINEER]:
            c = critiques.get(role.value)
            if not c or c.verdict != CritiqueVerdict.APPROVE:
                non_approving.append(role.value)

        if non_approving:
            is_gated_tier2 = True
            gating_reasons.append(
                f"Tier {proposal_tier} proposal strictly requires unanimous APPROVE from Lead Architect, "
                f"Security Auditor, and QA Engineer. Non-approving roles: {', '.join(non_approving)}."
            )
            verdict = ConsensusVerdict.GATED_PENDING_UNANIMOUS

    # 3. Score Escalation Threshold (< 0.85)
    if score < 0.85:
        gating_reasons.append(
            f"Aggregate consensus score {score:.2f} is below autonomous approval threshold (0.85)."
        )
        if not is_gated_tier2:
            verdict = ConsensusVerdict.ESCALATED_TO_USER

    # If security veto was triggered and tier < 2, ensure verdict is ESCALATED_TO_USER
    if has_security_veto and verdict == ConsensusVerdict.APPROVED_AUTONOMOUS:
        verdict = ConsensusVerdict.ESCALATED_TO_USER

    return score, verdict, gating_reasons, breakdown


class SyntheticDebateEngine:
    """
    Executes multi-turn synthetic debates across the 4 specialist sub-agents.
    """

    async def run_debate(
        self,
        proposal: SwarmProposal,
        max_rounds: int = 3
    ) -> ConsensusReport:
        """
        Runs structured synthetic debate rounds (1 to max_rounds).
        Supports early exit upon high-confidence unanimous approval.
        """
        debate_id = generate_id()
        started_at = current_iso_time()
        max_rounds = max(1, min(max_rounds, 3))
        turns: List[DebateTurn] = []

        final_score = 0.0
        final_verdict = ConsensusVerdict.ESCALATED_TO_USER
        final_reasons: List[str] = []
        final_breakdown: Dict[str, float] = {}

        for round_idx in range(1, max_rounds + 1):
            # Concurrent evaluation of all 4 specialists
            roles = [
                SpecialistRole.LEAD_ARCHITECT,
                SpecialistRole.CODE_REVIEWER,
                SpecialistRole.SECURITY_AUDITOR,
                SpecialistRole.QA_ENGINEER,
            ]

            critique_results = await asyncio.gather(
                *[evaluate_proposal(role, proposal, previous_turns=turns) for role in roles]
            )

            critiques_dict: Dict[str, SpecialistCritique] = {
                critique.role.value: critique for critique in critique_results
            }

            # Generate cross-rebuttals and turn summary
            cross_rebuttals: List[str] = []
            if round_idx > 1 and turns:
                prev_turn = turns[-1]
                for role_val, critique in critiques_dict.items():
                    prev_c = prev_turn.critiques.get(role_val)
                    if prev_c and prev_c.verdict != critique.verdict:
                        cross_rebuttals.append(
                            f"[{role_val}] Adjusted stance from {prev_c.verdict.value} to {critique.verdict.value}."
                        )
                    elif critique.concerns:
                        cross_rebuttals.append(
                            f"[{role_val}] Reasserted concerns: {'; '.join(critique.concerns[:2])}."
                        )

            score, verdict, gating_reasons, breakdown = calculate_consensus(
                critiques_dict,
                proposal.risk_tier
            )

            turn_summary = f"Round {round_idx}: Consensus Score={score:.2f}, Verdict={verdict.value}."

            current_turn = DebateTurn(
                round_number=round_idx,
                critiques=critiques_dict,
                cross_rebuttals=cross_rebuttals,
                turn_summary=turn_summary
            )
            turns.append(current_turn)

            final_score = score
            final_verdict = verdict
            final_reasons = gating_reasons
            final_breakdown = breakdown

            # Early Exit Check: Unanimous APPROVE with consensus score >= 0.95
            all_approved = all(c.verdict == CritiqueVerdict.APPROVE for c in critiques_dict.values())
            if all_approved and score >= 0.95 and verdict == ConsensusVerdict.APPROVED_AUTONOMOUS:
                current_turn.turn_summary += " (Terminated early on high-confidence unanimous consensus)."
                break

        return ConsensusReport(
            debate_id=debate_id,
            proposal_title=proposal.title,
            proposal_description=proposal.description,
            proposal_diff=proposal.diff,
            risk_tier=proposal.risk_tier,
            turns=turns,
            final_score=final_score,
            verdict=final_verdict,
            gating_reasons=final_reasons,
            specialist_breakdown=final_breakdown,
            started_at=started_at,
            completed_at=current_iso_time()
        )
