"""Proactive Workspace Self-Healing Tools for Phenom (Milestone 31 Phase 4).

Registers 4 specialized tools in ToolRegistry:
1. diagnose_workspace_error (Tier 0)
2. synthesize_ast_hot_patch (Tier 1)
3. apply_workspace_hot_patch (Tier 1)
4. rollback_workspace_hot_patch (Tier 1)
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.evolution.workspace_self_healer import workspace_self_healer


# ==========================================
# 1. Diagnose Workspace Error (Tier 0)
# ==========================================

class DiagnoseWorkspaceErrorArgs(BaseModel):
    raw_trace: str = Field(..., description="Raw compiler failure, pytest traceback, or runtime exception log.")


def preview_diagnose_workspace_error(args: Dict[str, Any]) -> str:
    trace = args.get("raw_trace", "")
    preview_txt = (trace[:60] + "...") if len(trace) > 60 else trace
    return f"Diagnose workspace error trace: \"{preview_txt}\""


@registry.register(
    name="diagnose_workspace_error",
    tier=0,
    description="Analyzes workspace compiler errors, broken test traces, or runtime exceptions and formulates repair hypothesis (Tier 0 read-only).",
    args_schema=DiagnoseWorkspaceErrorArgs,
    preview_fn=preview_diagnose_workspace_error,
    can_remember_per_folder=False,
)
def handle_diagnose_workspace_error(raw_trace: str) -> Dict[str, Any]:
    diagnosis = workspace_self_healer.diagnose_error(raw_trace)
    return diagnosis.model_dump()


# ==========================================
# 2. Synthesize AST Hot-Patch (Tier 1)
# ==========================================

class SynthesizeASTHotPatchArgs(BaseModel):
    diagnosis_id: str = Field(..., description="ID of diagnosis to patch.")
    file_path: str = Field(..., description="Target file path.")
    target_snippet: str = Field(..., description="Offending code snippet to replace.")
    replacement_snippet: str = Field(..., description="Verified repaired replacement code snippet.")


def preview_synthesize_ast_hot_patch(args: Dict[str, Any]) -> str:
    f_path = args.get("file_path", "file")
    return f"Synthesize unified diff AST hot-patch for [{f_path}]"


@registry.register(
    name="synthesize_ast_hot_patch",
    tier=1,
    description="Synthesizes a unified diff AST hot-patch for a diagnosed issue (Tier 1 staging).",
    args_schema=SynthesizeASTHotPatchArgs,
    preview_fn=preview_synthesize_ast_hot_patch,
    can_remember_per_folder=False,
)
def handle_synthesize_ast_hot_patch(
    diagnosis_id: str,
    file_path: str,
    target_snippet: str,
    replacement_snippet: str,
) -> Dict[str, Any]:
    patch = workspace_self_healer.synthesize_hot_patch(
        diagnosis_id=diagnosis_id,
        file_path=file_path,
        target_snippet=target_snippet,
        replacement_snippet=replacement_snippet,
    )
    return patch.model_dump()


# ==========================================
# 3. Apply Workspace Hot-Patch (Tier 1)
# ==========================================

class ApplyWorkspaceHotPatchArgs(BaseModel):
    patch_id: str = Field(..., description="ID of hot patch to apply.")


def preview_apply_workspace_hot_patch(args: Dict[str, Any]) -> str:
    p_id = args.get("patch_id", "patch")
    return f"Apply workspace hot-patch [{p_id}] with non-destructive snapshot backup"


@registry.register(
    name="apply_workspace_hot_patch",
    tier=1,
    description="Applies a staged hot-patch to the workspace, creating a snapshot for 1-click rollback (Tier 1 reversible action).",
    args_schema=ApplyWorkspaceHotPatchArgs,
    preview_fn=preview_apply_workspace_hot_patch,
    can_remember_per_folder=False,
)
def handle_apply_workspace_hot_patch(patch_id: str) -> Dict[str, Any]:
    result = workspace_self_healer.apply_patch(patch_id=patch_id)
    return result.model_dump()


# ==========================================
# 4. Rollback Workspace Hot-Patch (Tier 1)
# ==========================================

class RollbackWorkspaceHotPatchArgs(BaseModel):
    patch_id: str = Field(..., description="ID of applied hot patch to revert.")


def preview_rollback_workspace_hot_patch(args: Dict[str, Any]) -> str:
    p_id = args.get("patch_id", "patch")
    return f"Revert workspace hot-patch [{p_id}] to pre-patch snapshot"


@registry.register(
    name="rollback_workspace_hot_patch",
    tier=1,
    description="Reverts a previously applied hot-patch using its snapshot backup (Tier 1 reversible action).",
    args_schema=RollbackWorkspaceHotPatchArgs,
    preview_fn=preview_rollback_workspace_hot_patch,
    can_remember_per_folder=False,
)
def handle_rollback_workspace_hot_patch(patch_id: str) -> Dict[str, Any]:
    result = workspace_self_healer.rollback_patch(patch_id=patch_id)
    return result.model_dump()
