"""Self-Healing, Fault Localization & Dynamic Error Interception Tools.

Combines Milestone 24 Autonomous Neuro-Symbolic Self-Healing Tools:
1. diagnose_runtime_failure (Tier 0)
2. synthesize_healing_patch (Tier 0)
3. apply_healing_patch (Tier 1)

And Milestone 28 Dynamic Planning Error Interception Tools:
4. intercept_and_heal_failure (Tier 1)
5. diagnose_execution_error (Tier 0)
6. get_active_healing_journal (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.healing.diagnostic_engine import diagnostic_engine
from services.backend.healing.patch_synthesizer import patch_synthesizer
from services.backend.planning.error_interceptor import error_interceptor
from services.backend.planning.self_healing_orchestrator import self_healing_orchestrator


# ==========================================
# 1. Diagnose Runtime Failure (Tier 0) - M24
# ==========================================

class DiagnoseRuntimeFailureArgs(BaseModel):
    traceback_text: str = Field(..., description="Full Python traceback or exception error text")
    source_code: Optional[str] = Field(
        default=None,
        description="Optional source code of the failing module to improve fault localization",
    )


def diagnose_runtime_failure_preview(args: Dict[str, Any]) -> str:
    tb = args.get("traceback_text", "")
    snippet = tb.splitlines()[-1] if tb.splitlines() else "exception"
    return f"Diagnose runtime failure and localize fault for: '{snippet}'."


@registry.register(
    name="diagnose_runtime_failure",
    tier=0,
    description="Parses runtime exception tracebacks, isolates culprit AST frames, and classifies fault categories.",
    args_schema=DiagnoseRuntimeFailureArgs,
    preview_fn=diagnose_runtime_failure_preview,
    can_remember_per_folder=False,
)
def handle_diagnose_runtime_failure(
    traceback_text: str,
    source_code: Optional[str] = None,
) -> Dict[str, Any]:
    report = diagnostic_engine.diagnose_traceback(
        traceback_text=traceback_text,
        source_code=source_code,
    )
    return report.model_dump()


# ==========================================
# 2. Synthesize Healing Patch (Tier 0) - M24
# ==========================================

class SynthesizeHealingPatchArgs(BaseModel):
    traceback_text: str = Field(..., description="Exception traceback text to repair")
    source_code: str = Field(..., description="Source code of the failing file")
    dry_run: Optional[bool] = Field(
        default=True,
        description="Whether to generate candidate unified diff without modifying file on disk",
    )


def synthesize_healing_patch_preview(args: Dict[str, Any]) -> str:
    dr = " (dry-run candidate)" if args.get("dry_run", True) else ""
    return f"Synthesize deterministic AST repair patch with unified diff{dr}."


@registry.register(
    name="synthesize_healing_patch",
    tier=0,
    description="Deterministically synthesizes symbolic AST repair patches and generates unified diff previews.",
    args_schema=SynthesizeHealingPatchArgs,
    preview_fn=synthesize_healing_patch_preview,
    can_remember_per_folder=False,
)
def handle_synthesize_healing_patch(
    traceback_text: str,
    source_code: str,
    dry_run: bool = True,
) -> Dict[str, Any]:
    report = diagnostic_engine.diagnose_traceback(
        traceback_text=traceback_text,
        source_code=source_code,
    )
    res = patch_synthesizer.synthesize_patch(
        report=report,
        source_code=source_code,
        dry_run=dry_run,
    )
    return res.model_dump()


# ==========================================
# 3. Apply Healing Patch (Tier 1) - M24
# ==========================================

class ApplyHealingPatchArgs(BaseModel):
    patch_id: str = Field(..., description="Unique patch ID returned from synthesize_healing_patch")


def apply_healing_patch_preview(args: Dict[str, Any]) -> str:
    pid = args.get("patch_id", "patch")
    return f"Apply synthesized healing patch '{pid}' to target file with reversible rollback snapshot."


@registry.register(
    name="apply_healing_patch",
    tier=1,
    description="Applies a synthesized AST patch to target source code with atomic transaction rollback checkpoint.",
    args_schema=ApplyHealingPatchArgs,
    preview_fn=apply_healing_patch_preview,
    can_remember_per_folder=False,
)
def handle_apply_healing_patch(patch_id: str) -> Dict[str, Any]:
    return patch_synthesizer.apply_patch(patch_id=patch_id)


# Programmatic aliases M24
diagnose_runtime_failure = handle_diagnose_runtime_failure
synthesize_healing_patch = handle_synthesize_healing_patch
apply_healing_patch = handle_apply_healing_patch


# ==========================================
# 4. Intercept and Heal Failure (Tier 1) - M28
# ==========================================

class InterceptAndHealFailureArgs(BaseModel):
    target_tree_id: str = Field(..., description="ID of the plan tree containing the failing node.")
    failing_node_id: str = Field(..., description="Node ID within the tree that experienced execution failure.")
    raw_error: str = Field(..., description="Raw exception message or stack trace symptom.")


def preview_intercept_and_heal_failure(args: Dict[str, Any]) -> str:
    tid = args.get("target_tree_id", "active_tree")
    nid = args.get("failing_node_id", "failing_node")
    err = args.get("raw_error", "Unknown error")[:35]
    return f"Diagnose error '{err}' and dynamically graft compensatory repair sub-plan under node '{nid}' in tree '{tid}'."


@registry.register(
    name="intercept_and_heal_failure",
    tier=1,
    description="Diagnoses execution failure, classifies fault taxonomy, and dynamically grafts compensatory sub-plans into the active plan tree.",
    args_schema=InterceptAndHealFailureArgs,
    preview_fn=preview_intercept_and_heal_failure,
    can_remember_per_folder=False,
)
def handle_intercept_and_heal_failure(
    target_tree_id: str,
    failing_node_id: str,
    raw_error: str,
) -> Dict[str, Any]:
    return self_healing_orchestrator.heal_failure(
        target_tree_id=target_tree_id,
        failing_node_id=failing_node_id,
        raw_error=raw_error,
    )


# ==========================================
# 5. Diagnose Execution Error (Tier 0) - M28
# ==========================================

class DiagnoseExecutionErrorArgs(BaseModel):
    raw_error: str = Field(..., description="Raw error string or exception traceback.")
    target_tree_id: str = Field(default="active_plan", description="Optional ID of the related plan tree.")


def preview_diagnose_execution_error(args: Dict[str, Any]) -> str:
    err = args.get("raw_error", "error")[:35]
    return f"Perform causal diagnostic taxonomy on error: '{err}'."


@registry.register(
    name="diagnose_execution_error",
    tier=0,
    description="Analyzes an execution error string, classifies its failure taxonomy, and evaluates self-healing eligibility.",
    args_schema=DiagnoseExecutionErrorArgs,
    preview_fn=preview_diagnose_execution_error,
    can_remember_per_folder=False,
)
def handle_diagnose_execution_error(
    raw_error: str,
    target_tree_id: str = "active_plan",
) -> Dict[str, Any]:
    diagnosis = error_interceptor.diagnose_error(raw_error)
    return diagnosis.model_dump()


# ==========================================
# 6. Get Active Healing Journal (Tier 0) - M28
# ==========================================

class GetActiveHealingJournalArgs(BaseModel):
    pass


def preview_get_active_healing_journal(args: Dict[str, Any]) -> str:
    return "Retrieve active self-healing execution journal records and remediation history."


@registry.register(
    name="get_active_healing_journal",
    tier=0,
    description="Retrieves the chronological audit journal of all dynamic error interceptions and self-healing actions taken.",
    args_schema=GetActiveHealingJournalArgs,
    preview_fn=preview_get_active_healing_journal,
    can_remember_per_folder=False,
)
def handle_get_active_healing_journal() -> Dict[str, Any]:
    journal = self_healing_orchestrator.get_journal()
    return {
        "total_records": len(journal),
        "journal": journal,
    }
