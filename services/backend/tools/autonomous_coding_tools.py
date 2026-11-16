"""
Autonomous Coding Tools Registration (Phase 47-02, EXEC-01, EXEC-02, EXEC-03).
Exposes isolated workspace cloning, in-memory AST validation, test running, and diff application
as first-class safety-registered tools for Phenom's Mission Orchestrator.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.coding.workspace_cloner import workspace_cloner
from services.backend.coding.ast_validator import ast_validator
from services.backend.coding.test_runner import workspace_test_runner
from services.backend.coding.diff_engine import workspace_diff_engine


# ============================================================================
# 1. clone_isolated_workspace (Tier 1)
# ============================================================================

class CloneIsolatedWorkspaceArgs(BaseModel):
    project_path: str = Field(..., description="Path to target project to clone and isolate")
    task_description: Optional[str] = Field(default=None, description="Optional description of the task or bug to fix")

def clone_isolated_workspace_preview(args: Dict[str, Any]) -> str:
    path = args.get("project_path", "")
    return f"Clone project at '{path}' into an isolated sandbox workspace with pre-execution snapshot."

@registry.register(
    name="clone_isolated_workspace",
    tier=1,
    description="Clones a target project directory into an isolated sandbox workspace in .workspaces with snapshotting.",
    args_schema=CloneIsolatedWorkspaceArgs,
    preview_fn=clone_isolated_workspace_preview,
    can_remember_per_folder=True
)
def handle_clone_isolated_workspace(project_path: str, task_description: Optional[str] = None) -> Dict[str, Any]:
    ctx = workspace_cloner.clone_project(project_path, task_name=task_description)
    return ctx.model_dump()


# ============================================================================
# 2. validate_ast_syntax (Tier 0 - Read Only)
# ============================================================================

class ValidateASTSyntaxArgs(BaseModel):
    code: str = Field(..., description="Source code text to validate in memory")
    language: Optional[str] = Field(default="python", description="Target language (python, typescript, javascript, json)")
    file_path: Optional[str] = Field(default=None, description="Optional file path used for language detection")

def validate_ast_syntax_preview(args: Dict[str, Any]) -> str:
    lang = args.get("language") or "python"
    return f"Validate in-memory {lang} source code syntax using AST parser."

@registry.register(
    name="validate_ast_syntax",
    tier=0,
    description="Performs in-memory AST syntax validation to prevent broken code from touching disk.",
    args_schema=ValidateASTSyntaxArgs,
    preview_fn=validate_ast_syntax_preview
)
def handle_validate_ast_syntax(
    code: str,
    language: Optional[str] = "python",
    file_path: Optional[str] = None
) -> Dict[str, Any]:
    if file_path and not language:
        lang = ast_validator.detect_language(file_path)
    else:
        lang = language or "python"
    res = ast_validator.validate_code(code, language=lang)
    return res.model_dump()


# ============================================================================
# 3. run_workspace_tests (Tier 1)
# ============================================================================

class RunWorkspaceTestsArgs(BaseModel):
    workspace_dir: str = Field(..., description="Path to the isolated workspace containing test suite")
    framework: Optional[str] = Field(default=None, description="Optional test runner override (pytest, npm, unittest)")
    test_target: Optional[str] = Field(default=None, description="Optional specific test file or target path")
    timeout_seconds: Optional[int] = Field(default=120, description="Hard execution timeout in seconds")

def run_workspace_tests_preview(args: Dict[str, Any]) -> str:
    ws = args.get("workspace_dir", "")
    fw = args.get("framework") or "auto-detected"
    return f"Execute {fw} test suite in isolated workspace '{ws}' with Guardian tracking."

@registry.register(
    name="run_workspace_tests",
    tier=1,
    description="Executes test runner in an isolated workspace under Guardian monitoring and parses tracebacks.",
    args_schema=RunWorkspaceTestsArgs,
    preview_fn=run_workspace_tests_preview,
    can_remember_per_folder=True
)
def handle_run_workspace_tests(
    workspace_dir: str,
    framework: Optional[str] = None,
    test_target: Optional[str] = None,
    timeout_seconds: Optional[int] = 120
) -> Dict[str, Any]:
    res = workspace_test_runner.run_tests(
        workspace_dir=workspace_dir,
        framework=framework,
        test_target=test_target,
        timeout_seconds=timeout_seconds or 120
    )
    return res.model_dump()


# ============================================================================
# 4. apply_workspace_diff (Tier 2 - Confirmation Required)
# ============================================================================

class ApplyWorkspaceDiffArgs(BaseModel):
    original_dir: str = Field(..., description="Target source repository directory")
    workspace_dir: str = Field(..., description="Isolated workspace directory containing verified changes")
    create_backup: Optional[bool] = Field(default=True, description="Whether to take a pre-apply rollback snapshot")

def apply_workspace_diff_preview(args: Dict[str, Any]) -> str:
    orig = args.get("original_dir", "")
    ws = args.get("workspace_dir", "")
    return f"Apply verified changes from isolated workspace '{ws}' to original repository '{orig}' with rollback snapshot."

@registry.register(
    name="apply_workspace_diff",
    tier=2,
    description="Applies tested changes from an isolated workspace back to the original repository with pre-apply rollback backup.",
    args_schema=ApplyWorkspaceDiffArgs,
    preview_fn=apply_workspace_diff_preview
)
def handle_apply_workspace_diff(
    original_dir: str,
    workspace_dir: str,
    create_backup: Optional[bool] = True
) -> Dict[str, Any]:
    res = workspace_diff_engine.apply_diff(
        original_dir=original_dir,
        workspace_dir=workspace_dir,
        create_backup=True if create_backup is None else create_backup
    )
    return res.model_dump()
