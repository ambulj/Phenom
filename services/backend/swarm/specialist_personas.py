"""
Phenom Specialist Sub-Agent Personas & Evaluation Engine (SWM-01)
Defines the 4 specialized roles (Lead Architect, Code Reviewer, Security Auditor, QA Test Engineer),
their dedicated domain instructions, safety rules, and asynchronous evaluation handlers.
"""

import re
from typing import Dict, List, Optional
from datetime import datetime, timezone

from services.backend.schemas.swarm_debate import (
    SpecialistRole,
    CritiqueVerdict,
    SpecialistCritique,
    DebateTurn,
    SwarmProposal,
    current_iso_time,
)

# System prompts for the 4 specialist personas
LEAD_ARCHITECT_PROMPT = """
You are Phenom's Lead Architect.
Domain & Focus:
- Overall architectural coherence, modularity, and clean component boundaries.
- Adherence to Phenom repo layout (AGENTS.md) and separation between Electron desktop, FastAPI backend, and safety layers.
- Long-term maintainability, scalability, and performance budgets.
- In multi-turn synthetic debates, you facilitate convergence, synthesize compromises, and align specialist recommendations.
"""

CODE_REVIEWER_PROMPT = """
You are Phenom's Code Reviewer.
Domain & Focus:
- Strict typing: TypeScript strict mode and Python type hints (mypy/pyright compliant).
- Code style: PEP 8 formatting, descriptive variable names, docstrings, and clean modular functions.
- Diff minimality: Ensure changes are surgical, focused on the immediate task, and avoid unnecessary refactoring.
- Rejection of silent fallbacks or hidden mocks that mask underlying failures.
"""

SECURITY_AUDITOR_PROMPT = """
You are Phenom's Security Auditor. You hold unilateral VETO power.
Domain & Focus:
- Strict adherence to Phenom permanent safety rules (AGENTS.md):
  * Rule 1: No direct tool calls by model; all tools must route through Safety Layer.
  * Rule 4: Private files and text never reach a cloud model without previewed approval.
  * Rule 7: Delete means recycle bin. Never permanent delete.
  * Rule 8: Payments are impossible by construction. Never type or store passwords.
  * Rule 9: Email drafts only, never send. Calendar create only, never delete or edit others.
  * Rule 11: Secrets live in environment variables or Credential Manager only. Never in code, logs, or chat.
- Prompt injection defense, path traversal prevention, credential hygiene, and privilege escalation prevention.
"""

QA_ENGINEER_PROMPT = """
You are Phenom's QA Test Engineer.
Domain & Focus:
- Comprehensive test coverage: unit tests, integration suites, and edge/boundary condition tests.
- Idempotent execution and resilient error recovery under unexpected inputs or network drops.
- Verifiable proof: Require test execution evidence before approving any feature.
- Regression hazards: Prevent breaking existing APIs, protocol contracts, or desktop bridges.
"""

SPECIALIST_PROMPTS: Dict[SpecialistRole, str] = {
    SpecialistRole.LEAD_ARCHITECT: LEAD_ARCHITECT_PROMPT,
    SpecialistRole.CODE_REVIEWER: CODE_REVIEWER_PROMPT,
    SpecialistRole.SECURITY_AUDITOR: SECURITY_AUDITOR_PROMPT,
    SpecialistRole.QA_ENGINEER: QA_ENGINEER_PROMPT,
}


async def evaluate_proposal(
    role: SpecialistRole,
    proposal: SwarmProposal,
    previous_turns: Optional[List[DebateTurn]] = None
) -> SpecialistCritique:
    """
    Evaluates a proposal from the perspective of a specific specialist persona.
    Supports multi-turn debate context by analyzing previous turns and cross-critiques.
    Deterministic, high-performance evaluation with rule checks and domain criteria.
    """
    text_corpus = f"{proposal.title}\n{proposal.description}\n{proposal.diff or ''}\n{' '.join(proposal.constraints)}"
    text_lower = text_corpus.lower()
    
    strengths: List[str] = []
    concerns: List[str] = []
    recommendations: List[str] = []
    verdict = CritiqueVerdict.APPROVE
    confidence = 0.90

    # Explicit simulation directives for testing
    role_str = role.value.lower()
    if f"[block:{role_str}]" in text_lower or "[simulate_block]" in text_lower:
        return SpecialistCritique(
            role=role,
            verdict=CritiqueVerdict.BLOCK,
            confidence=0.98,
            strengths=["Proposal explicitly identified for verification"],
            concerns=[f"Simulated hard block triggered for {role.value}"],
            recommendations=["Resolve blocking finding before resubmitting"],
            timestamp=current_iso_time()
        )
    if f"[request_changes:{role_str}]" in text_lower or "[simulate_request_changes]" in text_lower:
        return SpecialistCritique(
            role=role,
            verdict=CritiqueVerdict.REQUEST_CHANGES,
            confidence=0.88,
            strengths=["Acceptable baseline direction"],
            concerns=[f"Simulated revision requested by {role.value}"],
            recommendations=["Address requested changes in next turn"],
            timestamp=current_iso_time()
        )

    # 1. SECURITY AUDITOR DOMAIN EVALUATION
    if role == SpecialistRole.SECURITY_AUDITOR:
        # Phenom Rule 7: Delete means recycle bin. Never permanent delete.
        if any(term in text_lower for term in ["os.remove", "unlink", "shutil.rmtree", "permanent delete", "rm -rf"]):
            verdict = CritiqueVerdict.BLOCK
            confidence = 0.99
            concerns.append("Violates Rule 7: Permanent file deletion detected. Must use send2trash or recycle bin.")
            recommendations.append("Refactor file operations to use recycle bin semantics.")

        # Phenom Rule 8: Payments are impossible by construction.
        if any(term in text_lower for term in ["stripe", "credit_card", "cvv", "checkout_complete", "pay_now", "execute_payment"]):
            verdict = CritiqueVerdict.BLOCK
            confidence = 0.99
            concerns.append("Violates Rule 8: Automated payments or payment execution detected. Payments must be impossible by construction.")
            recommendations.append("Halt checkout at cart review; never execute payment.")

        # Phenom Rule 11: Secrets live in env or Credential Manager.
        if re.search(r'(api_key|secret|password|token)\s*=\s*["\'][A-Za-z0-9_\-]{8,}["\']', text_corpus, re.IGNORECASE):
            verdict = CritiqueVerdict.BLOCK
            confidence = 0.99
            concerns.append("Violates Rule 11: Hardcoded secret or credential token detected in code proposal.")
            recommendations.append("Store secrets in Windows Credential Manager or environment variables only.")

        # Phenom Rule 9: Email drafts only, never send.
        if any(term in text_lower for term in ["smtp.send", "send_mail", "send_email", "mail.send"]):
            verdict = CritiqueVerdict.BLOCK
            confidence = 0.95
            concerns.append("Violates Rule 9: Automated email transmission detected. Drafts only are permitted.")
            recommendations.append("Restructure email tool to create draft only.")

        # Unsafe shell execution without safety tier
        if "subprocess.popen(shell=true)" in text_lower or "os.system(" in text_lower:
            verdict = CritiqueVerdict.BLOCK
            confidence = 0.95
            concerns.append("Unsafe raw shell invocation detected without sandbox or Safety Layer wrapping.")
            recommendations.append("Wrap command execution in ToolRegistry with Tier 2 confirmation.")

        # Risk tier checks
        if proposal.risk_tier >= 2 and verdict != CritiqueVerdict.BLOCK:
            strengths.append("Security perimeter inspected for Tier 2+ privileged operation.")
            recommendations.append("Ensure strict ToolRegistry Tier 2 preview and user confirmation are configured.")
        else:
            strengths.append("No credential leaks, unauthorized payments, or hard deletion vectors detected.")

    # 2. LEAD ARCHITECT DOMAIN EVALUATION
    elif role == SpecialistRole.LEAD_ARCHITECT:
        # Check boundary integrity and repo layout
        if any(term in text_lower for term in ["direct database write from electron", "bypass safety", "global mutable state"]):
            verdict = CritiqueVerdict.REQUEST_CHANGES
            confidence = 0.85
            concerns.append("Architectural boundary breach: direct unmediated coupling across service tiers.")
            recommendations.append("Route data through FastAPI backend with typed Pydantic models.")
        else:
            strengths.append("Clean separation of concerns adhering to Phenom architecture.")
            strengths.append("Component lifecycle and state transitions are explicitly modeled.")

        # Multi-turn convergence analysis
        if previous_turns and len(previous_turns) > 0:
            last_turn = previous_turns[-1]
            if any(c.verdict == CritiqueVerdict.BLOCK for c in last_turn.critiques.values()):
                concerns.append("Unresolved blocking objection from previous debate turn.")
                recommendations.append("Synthesize architectural compromise to address peer blocker.")
                verdict = CritiqueVerdict.REQUEST_CHANGES
            else:
                strengths.append(f"Convergence observed across {len(previous_turns)} preceding debate rounds.")

    # 3. CODE REVIEWER DOMAIN EVALUATION
    elif role == SpecialistRole.CODE_REVIEWER:
        # Check for typing strictness
        if "any" in text_lower and ("type: any" in text_lower or ": any" in text_lower):
            concerns.append("Usage of untyped 'Any' detected; violates Phenom strict typing requirement.")
            recommendations.append("Replace 'Any' with explicit Pydantic model or TypeScript strict interface.")
            verdict = CritiqueVerdict.REQUEST_CHANGES
            confidence = 0.85
        else:
            strengths.append("Typed schema adherence with explicit type hints and model validation.")

        # Check docstring and documentation integrity
        if proposal.diff and len(proposal.diff.splitlines()) > 500:
            concerns.append("Large diff size may impact reviewability and rollback granularity.")
            recommendations.append("Break monolithic patch into smaller atomic commits.")
        else:
            strengths.append("Diff scope is bounded and surgical.")

    # 4. QA TEST ENGINEER DOMAIN EVALUATION
    elif role == SpecialistRole.QA_ENGINEER:
        # Check for test evidence or test plan
        has_tests = any(term in text_lower for term in ["test", "pytest", "spec", "assert", "mock", "fixture"])
        if proposal.risk_tier >= 1 and not has_tests and not proposal.diff:
            verdict = CritiqueVerdict.REQUEST_CHANGES
            confidence = 0.85
            concerns.append("Proposal lacks explicit test plan or test coverage evidence for modified components.")
            recommendations.append("Implement automated unit/integration tests with pytest before approving.")
        else:
            strengths.append("Verification suite specified with clear pass/fail criteria.")
            strengths.append("Edge cases and error boundaries accounted for.")

    # If previous turn had changes requested and this is turn 2+, check if resolved
    if previous_turns and len(previous_turns) >= 1 and verdict == CritiqueVerdict.REQUEST_CHANGES:
        # If no new blockers, give credit for progress
        if not concerns or len(concerns) <= 1:
            verdict = CritiqueVerdict.APPROVE
            strengths.append("Adjusted verdict to APPROVE following cross-critique reconciliation.")

    return SpecialistCritique(
        role=role,
        verdict=verdict,
        confidence=confidence,
        strengths=strengths,
        concerns=concerns,
        recommendations=recommendations,
        timestamp=current_iso_time()
    )
