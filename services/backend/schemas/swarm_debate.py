"""
Phenom Multi-Agent Swarm & Synthetic Debate Schemas
Strictly typed Pydantic models for specialist roles, critiques, debate turns,
consensus scoring reports, and swarm tool arguments. (SWM-01, SAF-01, SAF-02)
"""

from enum import Enum
from typing import Dict, List, Optional, Literal
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field


def current_iso_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_id() -> str:
    return str(uuid.uuid4())


class SpecialistRole(str, Enum):
    LEAD_ARCHITECT = "lead_architect"
    CODE_REVIEWER = "code_reviewer"
    SECURITY_AUDITOR = "security_auditor"
    QA_ENGINEER = "qa_engineer"


class CritiqueVerdict(str, Enum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    BLOCK = "BLOCK"


class ConsensusVerdict(str, Enum):
    APPROVED_AUTONOMOUS = "APPROVED_AUTONOMOUS"
    GATED_PENDING_UNANIMOUS = "GATED_PENDING_UNANIMOUS"
    ESCALATED_TO_USER = "ESCALATED_TO_USER"
    REJECTED_BY_USER = "REJECTED_BY_USER"
    APPROVED_BY_USER = "APPROVED_BY_USER"
    HALTED = "HALTED"


class SpecialistCritique(BaseModel):
    role: SpecialistRole
    verdict: CritiqueVerdict
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    strengths: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=current_iso_time)


class DebateTurn(BaseModel):
    round_number: int = Field(ge=1, le=3)
    critiques: Dict[str, SpecialistCritique] = Field(default_factory=dict)
    cross_rebuttals: List[str] = Field(default_factory=list)
    turn_summary: str = ""


class ConsensusReport(BaseModel):
    debate_id: str = Field(default_factory=generate_id)
    proposal_title: str
    proposal_description: str
    proposal_diff: Optional[str] = None
    risk_tier: int = Field(default=1, ge=0, le=3)
    turns: List[DebateTurn] = Field(default_factory=list)
    final_score: float = Field(ge=0.0, le=1.0, default=0.0)
    verdict: ConsensusVerdict = ConsensusVerdict.ESCALATED_TO_USER
    gating_reasons: List[str] = Field(default_factory=list)
    specialist_breakdown: Dict[str, float] = Field(default_factory=dict)
    started_at: str = Field(default_factory=current_iso_time)
    completed_at: Optional[str] = None


class SwarmProposal(BaseModel):
    proposal_id: str = Field(default_factory=generate_id)
    title: str
    description: str
    diff: Optional[str] = None
    risk_tier: int = Field(default=1, ge=0, le=3)
    constraints: List[str] = Field(default_factory=list)
    context_files: List[str] = Field(default_factory=list)


# Tool argument schemas
class SwarmDispatchSpecialistsArgs(BaseModel):
    title: str = Field(description="Title or goal of the code proposal to debate")
    description: str = Field(description="Detailed description of changes or architectural proposal")
    diff: Optional[str] = Field(default=None, description="Unified git diff or code snippet to review")
    risk_tier: int = Field(default=1, ge=0, le=3, description="Risk tier of the proposed action (0-3)")
    max_rounds: int = Field(default=3, ge=1, le=3, description="Maximum synthetic debate rounds (1-3)")


class SwarmGetDebateStatusArgs(BaseModel):
    debate_id: Optional[str] = Field(default=None, description="Debate ID to query, or None for recent status")


class SwarmSubmitUserDecisionArgs(BaseModel):
    debate_id: str = Field(description="Debate ID to resolve")
    decision: Literal["approve", "reject"] = Field(description="'approve' to override/accept, 'reject' to decline")
    reason: Optional[str] = Field(default=None, description="Optional user justification or feedback")
