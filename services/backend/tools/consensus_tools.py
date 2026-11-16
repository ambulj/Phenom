"""Consensus Tools Registration (Phase 48-02, CONS-01, CONS-02, CONS-03).

Registers multi-agent peer review quorum evaluation and automated PR/patch bundling
into Phenom's Safety ToolRegistry.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.schemas.swarm_auction import AgentRole
from services.backend.swarm.consensus_engine import TwoTierConsensusEngine
from services.backend.swarm.patch_bundler import PatchBundler
from services.backend.swarm.peer_review import PeerReviewAuditor


# ============================================================================
# 1. evaluate_swarm_consensus (Tier 0 - Read Only)
# ============================================================================

class EvaluateSwarmConsensusArgs(BaseModel):
    unified_diff: str = Field(..., description="Unified diff text proposed by an agent")
    test_results: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional test suite execution output (passed, exit_code, total_tests, failed_count)",
    )
    touched_files: Optional[List[str]] = Field(
        default=None,
        description="Optional list of file paths modified in the patch",
    )
    file_contents: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional dictionary mapping modified file paths to their full source code",
    )


def evaluate_swarm_consensus_preview(args: Dict[str, Any]) -> str:
    diff_len = len(args.get("unified_diff", ""))
    return f"Evaluate two-tier quorum consensus (Coder + Security Auditor) across diff ({diff_len} chars)."


@registry.register(
    name="evaluate_swarm_consensus",
    tier=0,
    description="Audits workspace diff against two-tier consensus quorum (Coder + Security Auditor sign-off).",
    args_schema=EvaluateSwarmConsensusArgs,
    preview_fn=evaluate_swarm_consensus_preview,
)
def handle_evaluate_swarm_consensus(
    unified_diff: str,
    test_results: Optional[Dict[str, Any]] = None,
    touched_files: Optional[List[str]] = None,
    file_contents: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    touched = touched_files or PatchBundler.extract_touched_files(unified_diff)
    tests = test_results or {"passed": True, "exit_code": 0, "total_tests": 1, "failed_count": 0}

    # Generate votes from all 4 agent roles
    votes = [
        PeerReviewAuditor.generate_agent_vote(role, unified_diff, tests, touched, file_contents)
        for role in (AgentRole.CODER, AgentRole.SECURITY_AUDITOR, AgentRole.ARCHITECT, AgentRole.WEB_SCOUT)
    ]

    quorum_result = TwoTierConsensusEngine.evaluate_quorum(votes)
    return quorum_result.model_dump()


# ============================================================================
# 2. bundle_signed_patch (Tier 1)
# ============================================================================

class BundleSignedPatchArgs(BaseModel):
    target_project: str = Field(..., description="Target repository or directory path")
    unified_diff: str = Field(..., description="Unified diff text to package")
    test_results: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Test suite execution output",
    )
    rollback_snapshot_id: Optional[str] = Field(
        default=None,
        description="Optional pre-apply rollback snapshot identifier",
    )


def bundle_signed_patch_preview(args: Dict[str, Any]) -> str:
    target = args.get("target_project", "")
    return f"Bundle signed, quorum-verified patch for project '{target}' with rollback snapshot."


@registry.register(
    name="bundle_signed_patch",
    tier=1,
    description="Packages approved workspace diff into a signed PatchBundle with rollback snapshot.",
    args_schema=BundleSignedPatchArgs,
    preview_fn=bundle_signed_patch_preview,
    can_remember_per_folder=False,
)
def handle_bundle_signed_patch(
    target_project: str,
    unified_diff: str,
    test_results: Optional[Dict[str, Any]] = None,
    rollback_snapshot_id: Optional[str] = None,
) -> Dict[str, Any]:
    touched = PatchBundler.extract_touched_files(unified_diff)
    tests = test_results or {"passed": True, "exit_code": 0, "total_tests": 1, "failed_count": 0}

    # Evaluate quorum
    votes = [
        PeerReviewAuditor.generate_agent_vote(role, unified_diff, tests, touched, None)
        for role in (AgentRole.CODER, AgentRole.SECURITY_AUDITOR, AgentRole.ARCHITECT, AgentRole.WEB_SCOUT)
    ]
    quorum_result = TwoTierConsensusEngine.evaluate_quorum(votes)

    bundle = PatchBundler.bundle_patch(
        target_project=target_project,
        unified_diff=unified_diff,
        quorum_result=quorum_result,
        rollback_snapshot_id=rollback_snapshot_id,
    )
    return bundle.model_dump()
