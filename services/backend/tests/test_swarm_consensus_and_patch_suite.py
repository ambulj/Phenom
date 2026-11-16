"""Comprehensive Unit Test Suite for Multi-Agent Consensus Engine & Automated PR/Patch Review Quorum.

Phase 48-02: CONS-01, CONS-02, CONS-03.
Tests peer review auditing (syntax, tests, paths, secrets, PII), two-tier quorum consensus,
unilateral security veto, architect deadlock arbitration, signed patch bundler, and ToolRegistry tools.
"""

import pytest
from typing import Dict, Any

from services.backend.schemas.swarm_auction import AgentRole
from services.backend.schemas.swarm_consensus import (
    ReviewVerdict,
    FindingCategory,
    FindingSeverity,
    ReviewFinding,
    AgentReviewVote,
    QuorumState,
    QuorumEvaluationResult,
    PatchBundle,
)
from services.backend.swarm.peer_review import PeerReviewAuditor
from services.backend.swarm.consensus_engine import TwoTierConsensusEngine
from services.backend.swarm.patch_bundler import PatchBundler, ConsensusNotReachedError
import services.backend.tools.consensus_tools
from services.backend.safety.registry import registry


# ============================================================================
# 1. Consensus Schemas Validation
# ============================================================================

def test_consensus_schemas():
    """Verify enum values, model dump serialization, and signature hash fields."""
    finding = ReviewFinding(
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.CRITICAL,
        message="Potential credential leak",
        file_path="src/config.py",
        line_number=42,
    )
    dumped = finding.model_dump()
    assert dumped["category"] == "security"
    assert dumped["severity"] == "critical"

    vote = AgentReviewVote(
        agent_role=AgentRole.SECURITY_AUDITOR,
        verdict=ReviewVerdict.APPROVE,
        confidence=0.98,
        findings=[finding],
        comments="Approved with notes",
        signature_hash="a" * 64,
    )
    assert vote.agent_role == AgentRole.SECURITY_AUDITOR
    assert len(vote.signature_hash) == 64


# ============================================================================
# 2. Peer Review Auditor: Syntax & Test Checks (CONS-01)
# ============================================================================

def test_peer_review_auditor_syntax_and_tests():
    """Verify AST syntax validation and test outcome parsing."""
    # 1. Clean Python AST
    clean_files = {"app.py": "def add(a: int, b: int) -> int:\n    return a + b\n"}
    findings = PeerReviewAuditor.audit_code_syntax(clean_files)
    assert len(findings) == 0

    # 2. Syntax Error in Python
    broken_files = {"bad.py": "def broken_func(\n    return 42\n"}
    findings_bad = PeerReviewAuditor.audit_code_syntax(broken_files)
    assert len(findings_bad) == 1
    assert findings_bad[0].category == FindingCategory.SYNTAX
    assert findings_bad[0].severity == FindingSeverity.CRITICAL

    # 3. Test Suite Pass
    tests_pass = {"passed": True, "exit_code": 0, "total_tests": 12, "failed_count": 0}
    t_findings_pass = PeerReviewAuditor.audit_test_results(tests_pass)
    assert len(t_findings_pass) == 0

    # 4. Test Suite Failure
    tests_fail = {"passed": False, "exit_code": 1, "total_tests": 12, "failed_count": 2}
    t_findings_fail = PeerReviewAuditor.audit_test_results(tests_fail)
    assert len(t_findings_fail) == 1
    assert t_findings_fail[0].severity == FindingSeverity.CRITICAL


# ============================================================================
# 3. Peer Review Auditor: Path Safety & Secrets (CONS-01)
# ============================================================================

def test_peer_review_auditor_path_and_secrets():
    """Verify detection of path traversals, credential exposure, and PII."""
    # 1. Path Safety Check
    safe_paths = ["src/components/Button.tsx", "services/backend/main.py"]
    assert len(PeerReviewAuditor.audit_path_safety(safe_paths)) == 0

    dangerous_paths = [
        "../etc/passwd",
        r"C:\Windows\System32\drivers.sys",
        "home/user/.ssh/id_rsa",
        ".env",
    ]
    path_findings = PeerReviewAuditor.audit_path_safety(dangerous_paths)
    assert len(path_findings) == 4
    assert all(f.severity == FindingSeverity.CRITICAL for f in path_findings)

    # 2. Secret Exposure Check (construct prefix dynamically to prevent pre-commit trigger)
    fake_nv_key = "nv" + "api-1234567890abcdef1234567890"
    diff_with_secret = f"""--- a/config.py
+++ b/config.py
@@ -1 +1 @@
+API_KEY = "{fake_nv_key}"
"""
    secret_findings = PeerReviewAuditor.audit_secrets_and_pii(diff_with_secret)
    assert len(secret_findings) == 1
    assert secret_findings[0].category == FindingCategory.SECURITY
    assert secret_findings[0].severity == FindingSeverity.CRITICAL

    # 3. PII Check (Aadhaar pattern)
    diff_with_pii = """--- a/user.py
+++ b/user.py
@@ -1 +1 @@
+USER_AADHAAR = "2345 6789 0123"
"""
    pii_findings = PeerReviewAuditor.audit_secrets_and_pii(diff_with_pii)
    assert len(pii_findings) == 1
    assert pii_findings[0].category == FindingCategory.PII


# ============================================================================
# 4. Two-Tier Quorum Consensus Engine (CONS-02)
# ============================================================================

def test_two_tier_quorum_consensus_happy_path():
    """Verify unanimous sign-off between Coder and Security Auditor reaches quorum."""
    diff = "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n+x = 10\n"
    tests = {"passed": True, "exit_code": 0, "total_tests": 4, "failed_count": 0}
    touched = ["app.py"]

    vote_coder = PeerReviewAuditor.generate_agent_vote(AgentRole.CODER, diff, tests, touched)
    vote_sec = PeerReviewAuditor.generate_agent_vote(AgentRole.SECURITY_AUDITOR, diff, tests, touched)
    vote_arch = PeerReviewAuditor.generate_agent_vote(AgentRole.ARCHITECT, diff, tests, touched)

    assert vote_coder.verdict == ReviewVerdict.APPROVE
    assert vote_sec.verdict == ReviewVerdict.APPROVE

    quorum = TwoTierConsensusEngine.evaluate_quorum([vote_coder, vote_sec, vote_arch])
    assert quorum.state == QuorumState.QUORUM_REACHED
    assert quorum.is_approved is True
    assert quorum.coder_approved is True
    assert quorum.security_approved is True
    assert len(quorum.blocking_reasons) == 0


def test_two_tier_quorum_consensus_security_veto():
    """Verify unilateral Security Auditor veto when secrets or path violations exist."""
    fake_nv = "nv" + "api-secretkeyvalue1234567890"
    diff_bad = f"--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n+KEY = '{fake_nv}'\n"
    tests = {"passed": True, "exit_code": 0, "total_tests": 4, "failed_count": 0}
    touched = ["app.py"]

    vote_coder = PeerReviewAuditor.generate_agent_vote(AgentRole.CODER, diff_bad, tests, touched)
    vote_sec = PeerReviewAuditor.generate_agent_vote(AgentRole.SECURITY_AUDITOR, diff_bad, tests, touched)

    assert vote_coder.verdict == ReviewVerdict.APPROVE  # Coder thinks code is valid
    assert vote_sec.verdict == ReviewVerdict.REJECT   # Security Auditor vetoes!

    quorum = TwoTierConsensusEngine.evaluate_quorum([vote_coder, vote_sec])
    assert quorum.state == QuorumState.VETOED
    assert quorum.is_approved is False
    assert quorum.coder_approved is True
    assert quorum.security_approved is False
    assert any("Security Auditor VETO" in r for r in quorum.blocking_reasons)


def test_two_tier_quorum_consensus_coder_rejection():
    """Verify rejection when tests fail or syntax is invalid."""
    diff = "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n+x = 10\n"
    tests_failing = {"passed": False, "exit_code": 1, "total_tests": 4, "failed_count": 1}
    touched = ["app.py"]

    vote_coder = PeerReviewAuditor.generate_agent_vote(AgentRole.CODER, diff, tests_failing, touched)
    vote_sec = PeerReviewAuditor.generate_agent_vote(AgentRole.SECURITY_AUDITOR, diff, tests_failing, touched)

    assert vote_coder.verdict == ReviewVerdict.REJECT
    assert vote_sec.verdict == ReviewVerdict.APPROVE

    quorum = TwoTierConsensusEngine.evaluate_quorum([vote_coder, vote_sec])
    assert quorum.state == QuorumState.INSUFFICIENT_VOTES
    assert quorum.is_approved is False
    assert quorum.coder_approved is False


def test_two_tier_quorum_deadlock_and_arbitration():
    """Verify deadlock detection and Architect resolution."""
    vote_coder = AgentReviewVote(
        agent_role=AgentRole.CODER,
        verdict=ReviewVerdict.APPROVE,
        signature_hash="c" * 64,
    )
    # Auditor has non-critical reservations -> requests changes
    vote_sec = AgentReviewVote(
        agent_role=AgentRole.SECURITY_AUDITOR,
        verdict=ReviewVerdict.REQUEST_CHANGES,
        findings=[
            ReviewFinding(
                category=FindingCategory.STYLE,
                severity=FindingSeverity.LOW,
                message="Consider renaming variable for clarity",
            )
        ],
        signature_hash="s" * 64,
    )

    deadlock = TwoTierConsensusEngine.evaluate_quorum([vote_coder, vote_sec])
    assert deadlock.state == QuorumState.DEADLOCKED
    assert deadlock.is_approved is False

    # Architect arbitrates: approves override
    resolved_approve = TwoTierConsensusEngine.arbitrate_deadlock(
        deadlock,
        architect_override=True,
        arbitration_notes="Non-critical style finding waived for immediate hotfix.",
    )
    assert resolved_approve.state == QuorumState.QUORUM_REACHED
    assert resolved_approve.is_approved is True
    assert resolved_approve.architect_arbitrated is True

    # Architect arbitrates: upholds rejection
    resolved_reject = TwoTierConsensusEngine.arbitrate_deadlock(
        deadlock,
        architect_override=False,
        arbitration_notes="Style alignment is required per PEP 8 guidelines.",
    )
    assert resolved_reject.state == QuorumState.INSUFFICIENT_VOTES
    assert resolved_reject.is_approved is False


# ============================================================================
# 5. Automated PR/Patch Bundler (CONS-03)
# ============================================================================

def test_patch_bundler_success_and_rejection():
    """Verify patch bundle packaging, rollback snapshot linkage, and failure on unapproved quorum."""
    diff = "--- a/services/math.py\n+++ b/services/math.py\n@@ -1 +1 @@\n+def square(x): return x * x\n"
    touched = ["services/math.py"]
    tests = {"passed": True, "exit_code": 0, "total_tests": 2, "failed_count": 0}

    vote_coder = PeerReviewAuditor.generate_agent_vote(AgentRole.CODER, diff, tests, touched)
    vote_sec = PeerReviewAuditor.generate_agent_vote(AgentRole.SECURITY_AUDITOR, diff, tests, touched)
    quorum_approved = TwoTierConsensusEngine.evaluate_quorum([vote_coder, vote_sec])

    # 1. Success case
    bundle = PatchBundler.bundle_patch(
        target_project="C:/Phenom",
        unified_diff=diff,
        quorum_result=quorum_approved,
        rollback_snapshot_id="snap_20261117_010000",
    )
    assert bundle.target_project == "C:/Phenom"
    assert bundle.files_changed == ["services/math.py"]
    assert bundle.rollback_snapshot_id == "snap_20261117_010000"
    assert "Two-Tier Quorum:" in bundle.summary_markdown
    assert "Multi-Agent Quorum Verification Table" in bundle.summary_markdown

    # 2. Failure case: Unapproved quorum
    fake_nv = "nv" + "api-badsecretvalue123456789"
    diff_bad = f"--- a/math.py\n+++ b/math.py\n@@ -1 +1 @@\n+KEY = '{fake_nv}'\n"
    vote_bad_sec = PeerReviewAuditor.generate_agent_vote(AgentRole.SECURITY_AUDITOR, diff_bad, tests, touched)
    quorum_vetoed = TwoTierConsensusEngine.evaluate_quorum([vote_coder, vote_bad_sec])

    with pytest.raises(ConsensusNotReachedError):
        PatchBundler.bundle_patch(
            target_project="C:/Phenom",
            unified_diff=diff_bad,
            quorum_result=quorum_vetoed,
        )


# ============================================================================
# 6. Tool Registry Integration & Execution
# ============================================================================

def test_consensus_tools_registry():
    """Verify tool registration, tier numbers, preview generation, and execution."""
    tool_eval = registry.get("evaluate_swarm_consensus")
    tool_bundle = registry.get("bundle_signed_patch")

    assert tool_eval is not None
    assert tool_eval.tier == 0  # Tier 0 read-only evaluation
    assert tool_bundle is not None
    assert tool_bundle.tier == 1  # Tier 1 state-modifying bundle generation

    # Execute evaluate_swarm_consensus
    diff = "--- a/utils.py\n+++ b/utils.py\n@@ -1 +1 @@\n+VERSION = '1.0.0'\n"
    res_eval = tool_eval.handler_fn(
        unified_diff=diff,
        test_results={"passed": True, "exit_code": 0, "total_tests": 1, "failed_count": 0},
    )
    assert res_eval["state"] == "quorum_reached"
    assert res_eval["is_approved"] is True

    # Execute bundle_signed_patch
    res_bundle = tool_bundle.handler_fn(
        target_project="C:/Phenom",
        unified_diff=diff,
        test_results={"passed": True, "exit_code": 0, "total_tests": 1, "failed_count": 0},
        rollback_snapshot_id="snap_test_001",
    )
    assert res_bundle["target_project"] == "C:/Phenom"
    assert res_bundle["files_changed"] == ["utils.py"]
    assert res_bundle["rollback_snapshot_id"] == "snap_test_001"
    assert "Phenom Autonomous Patch Bundle" in res_bundle["summary_markdown"]
