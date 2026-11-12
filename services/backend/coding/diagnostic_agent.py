"""
Autonomous Diagnostic Test-Runner & Self-Healing Worktree Mission Agent.
Orchestrates isolated sandbox creation, test execution, failure diagnosis,
patch drafting, verification, and automatic rollback without dirtying user workspace.

Part of Phenom 20.0 Sovereign Autonomous Developer (MIS-02.1, DEV-02.1, SAF-01, SAF-02).
"""

import difflib
import logging
import time
import uuid
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from services.backend.coding.worktree_manager import worktree_manager
from services.backend.coding.test_runner_daemon import test_runner_daemon, TestRunResult
from services.backend.coding.traceback_parser import BuildFailureDiagnostic
from services.backend.coding.refactor_engine import refactor_engine
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.coding.diagnostic_agent")


class MissionRequest(BaseModel):
    test_path: str = Field(..., description="Target test file or test node to execute")
    target_file: Optional[str] = Field(default=None, description="Source file suspected of failure")
    patch_code: Optional[str] = Field(default=None, description="Proposed replacement code or patch snippet")
    search_target: Optional[str] = Field(default=None, description="Target substring to replace if using replacement")
    replacement_target: Optional[str] = Field(default=None, description="Replacement substring if using replacement")
    max_retries: int = Field(default=2, description="Maximum healing attempts")


class MissionReport(BaseModel):
    mission_id: str = Field(..., description="Unique mission execution ID")
    status: str = Field(..., description="Outcome: healed, baseline_passed, failed_verification, rolled_back, error")
    worktree_id: str = Field(..., description="Isolated worktree sandbox ID used")
    initial_failure: Optional[BuildFailureDiagnostic] = Field(default=None, description="Initial failure diagnostic")
    patch_diff: str = Field(default="", description="Unified diff of verified patch")
    verified_pass: bool = Field(default=False, description="Whether patch verified green in sandbox")
    iterations_count: int = Field(default=0, description="Number of healing cycles executed")
    duration_ms: float = Field(default=0.0, description="Total execution duration in milliseconds")
    logs: List[str] = Field(default_factory=list, description="Step-by-step audit logs")


class DiagnosticMissionAgent:
    """
    Autonomous self-healing test agent operating in isolated worktree sandboxes.
    Guarantees Rule 1 (Safety confirmation), Rule 4 (Zero egress), and Rule 7 (Reversibility).
    """

    async def execute_mission(self, request: MissionRequest) -> MissionReport:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Diagnostic mission halted.")
        t0 = time.perf_counter()
        mission_id = f"mission_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        logs: List[str] = [f"Mission {mission_id} started for test: {request.test_path}"]

        # Step 1: Create isolated worktree sandbox
        sandbox = worktree_manager.create_worktree(sandbox_id=f"wt_{mission_id}")
        logs.append(f"Created isolated worktree sandbox: {sandbox.sandbox_id} at {sandbox.path}")

        try:
            # Step 2: Run baseline test inside sandbox
            logs.append("Running baseline test in sandbox...")
            baseline_result = await test_runner_daemon.run_pytest(
                target_path=request.test_path,
                working_dir=sandbox.path,
                timeout_seconds=30,
            )

            # If already passing, no healing needed
            if baseline_result.status == "passed":
                logs.append("Baseline test passed green! No patch needed.")
                t1 = time.perf_counter()
                worktree_manager.remove_worktree(sandbox.sandbox_id)
                return MissionReport(
                    mission_id=mission_id,
                    status="baseline_passed",
                    worktree_id=sandbox.sandbox_id,
                    initial_failure=None,
                    patch_diff="",
                    verified_pass=True,
                    iterations_count=0,
                    duration_ms=(t1 - t0) * 1000.0,
                    logs=logs,
                )

            # Baseline failed: capture initial diagnostic
            diag = baseline_result.diagnostics[0] if baseline_result.diagnostics else None
            logs.append(f"Baseline test failed: {diag.error_type if diag else 'Unknown error'} in {diag.failing_file if diag else 'unknown file'}")

            # Identify target file to heal
            target_rel = request.target_file
            if not target_rel and diag and diag.failing_file:
                target_rel = diag.failing_file

            if not target_rel:
                logs.append("Could not determine target source file from diagnostics.")
                worktree_manager.remove_worktree(sandbox.sandbox_id)
                t1 = time.perf_counter()
                return MissionReport(
                    mission_id=mission_id,
                    status="error",
                    worktree_id=sandbox.sandbox_id,
                    initial_failure=diag,
                    patch_diff="",
                    verified_pass=False,
                    iterations_count=1,
                    duration_ms=(t1 - t0) * 1000.0,
                    logs=logs,
                )

            target_file_path = Path(sandbox.path) / target_rel
            if not target_file_path.exists():
                logs.append(f"Target file does not exist in sandbox: {target_file_path}")
                worktree_manager.remove_worktree(sandbox.sandbox_id)
                t1 = time.perf_counter()
                return MissionReport(
                    mission_id=mission_id,
                    status="error",
                    worktree_id=sandbox.sandbox_id,
                    initial_failure=diag,
                    patch_diff="",
                    verified_pass=False,
                    iterations_count=1,
                    duration_ms=(t1 - t0) * 1000.0,
                    logs=logs,
                )

            original_content = target_file_path.read_text(encoding="utf-8", errors="replace")

            # Step 3: Apply candidate patch inside sandbox
            patched_content = original_content
            if request.patch_code:
                patched_content = request.patch_code
            elif request.search_target and request.replacement_target:
                patched_content = original_content.replace(request.search_target, request.replacement_target)
            else:
                logs.append("No patch code or replacement target provided for self-healing.")
                worktree_manager.remove_worktree(sandbox.sandbox_id)
                t1 = time.perf_counter()
                return MissionReport(
                    mission_id=mission_id,
                    status="failed_verification",
                    worktree_id=sandbox.sandbox_id,
                    initial_failure=diag,
                    patch_diff="",
                    verified_pass=False,
                    iterations_count=1,
                    duration_ms=(t1 - t0) * 1000.0,
                    logs=logs,
                )

            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                original_content.splitlines(keepends=True),
                patched_content.splitlines(keepends=True),
                fromfile=f"a/{target_rel}",
                tofile=f"b/{target_rel}",
            ))
            patch_diff = "".join(diff_lines)

            # Write patch into sandbox
            target_file_path.write_text(patched_content, encoding="utf-8")
            logs.append(f"Applied patch to {target_rel} inside isolated sandbox.")

            # Step 4: Re-run verification test in sandbox
            if guardian.is_halted:
                raise PermissionError("Guardian kill switch is active. Diagnostic mission halted.")
            logs.append("Executing verification test run in sandbox...")
            verify_result = await test_runner_daemon.run_pytest(
                target_path=request.test_path,
                working_dir=sandbox.path,
                timeout_seconds=30,
            )

            t1 = time.perf_counter()
            duration_ms = (t1 - t0) * 1000.0

            if verify_result.status == "passed":
                logs.append("Verification test PASSED! Patch verified healthy.")
                # Clean up sandbox
                worktree_manager.remove_worktree(sandbox.sandbox_id)
                return MissionReport(
                    mission_id=mission_id,
                    status="healed",
                    worktree_id=sandbox.sandbox_id,
                    initial_failure=diag,
                    patch_diff=patch_diff,
                    verified_pass=True,
                    iterations_count=1,
                    duration_ms=duration_ms,
                    logs=logs,
                )
            else:
                logs.append("Verification test FAILED. Rolling back sandbox changes.")
                # Revert changes in sandbox
                target_file_path.write_text(original_content, encoding="utf-8")
                worktree_manager.remove_worktree(sandbox.sandbox_id)
                return MissionReport(
                    mission_id=mission_id,
                    status="rolled_back",
                    worktree_id=sandbox.sandbox_id,
                    initial_failure=diag,
                    patch_diff=patch_diff,
                    verified_pass=False,
                    iterations_count=1,
                    duration_ms=duration_ms,
                    logs=logs,
                )

        except Exception as e:
            logs.append(f"Mission execution error: {str(e)}")
            try:
                worktree_manager.remove_worktree(sandbox.sandbox_id)
            except Exception:
                pass
            t1 = time.perf_counter()
            return MissionReport(
                mission_id=mission_id,
                status="error",
                worktree_id=sandbox.sandbox_id,
                initial_failure=None,
                patch_diff="",
                verified_pass=False,
                iterations_count=1,
                duration_ms=(t1 - t0) * 1000.0,
                logs=logs,
            )


# Global singleton
diagnostic_mission_agent = DiagnosticMissionAgent()
