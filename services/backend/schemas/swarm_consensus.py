"""Pydantic v2 schemas for Multi-Agent Consensus Engine & Automated PR/Patch Review Quorum.

Phase 48-02: CONS-01, CONS-02, CONS-03.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.schemas.swarm_auction import AgentRole


class ReviewVerdict(str, Enum):
    """Verdict cast by an agent reviewer on a proposed patch or action."""
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    ABSTAIN = "abstain"


class FindingCategory(str, Enum):
    """Categorization of peer review findings."""
    SYNTAX = "syntax"
    TESTS = "tests"
    SECURITY = "security"
    PATH = "path"
    PII = "pii"
    MODULARITY = "modularity"
    STYLE = "style"


class FindingSeverity(str, Enum):
    """Severity classification for review findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ReviewFinding(BaseModel):
    """A granular issue, alert, or observation flagged during peer review."""
    category: FindingCategory
    severity: FindingSeverity
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    remediation_hint: Optional[str] = None


class AgentReviewVote(BaseModel):
    """A signed vote and critique from a specialized agent role."""
    agent_role: AgentRole
    verdict: ReviewVerdict
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    findings: List[ReviewFinding] = Field(default_factory=list)
    comments: str = Field(default="")
    signature_hash: str = Field(..., description="Cryptographic SHA-256 hash over vote contents")
    timestamp: float = Field(default_factory=time.time)


class QuorumState(str, Enum):
    """Overall status of multi-agent quorum evaluation."""
    QUORUM_REACHED = "quorum_reached"
    VETOED = "vetoed"
    DEADLOCKED = "deadlocked"
    INSUFFICIENT_VOTES = "insufficient_votes"


class QuorumEvaluationResult(BaseModel):
    """Consolidated outcome of the two-tier quorum consensus protocol."""
    state: QuorumState
    is_approved: bool
    coder_approved: bool = Field(default=False)
    security_approved: bool = Field(default=False)
    architect_arbitrated: bool = Field(default=False)
    votes: Dict[AgentRole, AgentReviewVote] = Field(default_factory=dict)
    blocking_reasons: List[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class PatchBundle(BaseModel):
    """A fully verified, signed PR/patch package ready for user presentation or merge."""
    patch_id: str
    target_project: str
    unified_diff: str
    files_changed: List[str] = Field(default_factory=list)
    quorum_result: QuorumEvaluationResult
    rollback_snapshot_id: Optional[str] = None
    summary_markdown: str = Field(default="")
    created_at: float = Field(default_factory=time.time)
