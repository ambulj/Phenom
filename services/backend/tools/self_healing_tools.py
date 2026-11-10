"""Safety-Wrapped Autonomous Neuro-Symbolic Self-Healing Tools.

Registers tools with ToolRegistry for traceback fault diagnosis, symbolic AST patch
synthesis, and reversible patch application (Phase 24-01 HEAL-01 / SYM-02).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.healing.diagnostic_engine import diagnostic_engine
from services.backend.healing.patch_synthesizer import patch_synthesizer


# ==========================================
# 1. Diagnose Runtime Failure (Tier 0)
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
# 2. Synthesize Healing Patch (Tier 0)
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
# 3. Apply Healing Patch (Tier 1)
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
