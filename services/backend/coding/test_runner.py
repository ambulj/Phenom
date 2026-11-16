"""
Workspace Test Runner with Guardian Tracking & Error Traceback Extraction (Phase 47-02, EXEC-02).
Executes test suites strictly inside an isolated workspace with hard runtime bounds.
Invariants:
1. Child process PIDs tracked by Guardian kill switch (guardian.track_pid).
2. Runtime capped by configurable timeout (default 120s).
3. Parses structured test counts (passed, failed, skipped) and failure tracebacks.
"""

import os
import sys
import time
import subprocess
import re
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian


class TestExecutionResult(BaseModel):
    """Structured test suite execution report."""
    __test__ = False
    success: bool = Field(..., description="True if test suite passed with exit code 0")
    framework: str = Field(..., description="Test framework invoked (pytest, npm, unittest)")
    exit_code: int = Field(..., description="Subprocess exit code")
    duration_seconds: float = Field(..., description="Execution duration in seconds")
    passed_count: int = Field(default=0, description="Number of passing test cases")
    failed_count: int = Field(default=0, description="Number of failing test cases")
    skipped_count: int = Field(default=0, description="Number of skipped test cases")
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    error_traceback: Optional[str] = Field(default=None, description="Extracted failure traceback snippet")


class WorkspaceTestRunner:
    """Executes test suites inside isolated workspaces under strict safety boundaries."""

    def __init__(self):
        pass

    @staticmethod
    def auto_detect_framework(workspace_dir: str) -> str:
        """Inspects workspace files to detect the appropriate test runner."""
        if not os.path.exists(workspace_dir):
            return "pytest"

        has_package_json = os.path.exists(os.path.join(workspace_dir, "package.json"))
        has_python_tests = (
            os.path.exists(os.path.join(workspace_dir, "pytest.ini")) or
            os.path.exists(os.path.join(workspace_dir, "pyproject.toml")) or
            os.path.exists(os.path.join(workspace_dir, "setup.py")) or
            any(f.endswith(".py") for root, _, files in os.walk(workspace_dir) for f in files if "test" in f)
        )

        if has_python_tests:
            return "pytest"
        elif has_package_json:
            return "npm"
        return "pytest"

    def run_tests(
        self,
        workspace_dir: str,
        framework: Optional[str] = None,
        test_target: Optional[str] = None,
        timeout_seconds: int = 120
    ) -> TestExecutionResult:
        """
        Executes test suite in the specified isolated workspace directory.
        Tracks child PID in Guardian and parses execution diagnostics.
        """
        if guardian.is_halted:
            return TestExecutionResult(
                success=False,
                framework=framework or "unknown",
                exit_code=-99,
                duration_seconds=0.0,
                error_traceback="Guardian kill switch is active. Test execution halted."
            )

        if not os.path.exists(workspace_dir):
            raise FileNotFoundError(f"Isolated workspace directory not found: {workspace_dir}")

        chosen_framework = (framework or self.auto_detect_framework(workspace_dir)).lower()

        # Build command line
        if chosen_framework == "pytest":
            cmd = [sys.executable, "-m", "pytest"]
            if test_target:
                cmd.append(test_target)
            cmd.extend(["-v", "--tb=short"])
        elif chosen_framework == "npm":
            cmd = ["npm.cmd" if os.name == "nt" else "npm", "test"]
            if test_target:
                cmd.extend(["--", test_target])
        else:
            cmd = [sys.executable, "-m", "unittest", "discover"]
            if test_target:
                cmd.extend(["-s", test_target])

        start_time = time.perf_counter()
        proc = None
        stdout_str = ""
        stderr_str = ""
        exit_code = 1

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=workspace_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            guardian.track_pid(proc.pid)

            try:
                stdout_str, stderr_str = proc.communicate(timeout=timeout_seconds)
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout_str, stderr_str = proc.communicate()
                exit_code = -1
                stderr_str += f"\n[TIMEOUT] Test execution exceeded hard limit of {timeout_seconds}s."

        except Exception as exc:
            stderr_str = str(exc)
            exit_code = -1
        finally:
            if proc:
                guardian.untrack_pid(proc.pid)

        duration = time.perf_counter() - start_time

        # Parse test metrics from stdout/stderr
        passed, failed, skipped, traceback_snippet = self._parse_test_metrics(
            chosen_framework, stdout_str, stderr_str
        )

        return TestExecutionResult(
            success=(exit_code == 0),
            framework=chosen_framework,
            exit_code=exit_code,
            duration_seconds=duration,
            passed_count=passed,
            failed_count=failed,
            skipped_count=skipped,
            stdout=stdout_str,
            stderr=stderr_str,
            error_traceback=traceback_snippet
        )

    @staticmethod
    def _parse_test_metrics(
        framework: str, stdout: str, stderr: str
    ) -> (int, int, int, Optional[str]):
        """Extracts passed/failed counts and failure tracebacks from console output."""
        passed = 0
        failed = 0
        skipped = 0
        traceback_snippet = None

        combined = f"{stdout}\n{stderr}"

        if framework == "pytest":
            # Pytest summary pattern: e.g. "== 2 passed, 1 failed, 1 skipped in 0.5s =="
            pass_match = re.search(r"(\d+)\s+passed", combined)
            fail_match = re.search(r"(\d+)\s+failed", combined)
            skip_match = re.search(r"(\d+)\s+skipped", combined)

            if pass_match:
                passed = int(pass_match.group(1))
            if fail_match:
                failed = int(fail_match.group(1))
            if skip_match:
                skipped = int(skip_match.group(1))

            # Extract failure section
            if "=== FAILURES ===" in combined:
                parts = combined.split("=== FAILURES ===")
                if len(parts) > 1:
                    tb_part = parts[1].split("=== short test summary info ===")[0]
                    traceback_snippet = tb_part.strip()
            elif failed > 0 and "Traceback" in combined:
                tb_matches = re.findall(r"Traceback.*?(?=(?:\n\n|\Z))", combined, re.DOTALL)
                if tb_matches:
                    traceback_snippet = tb_matches[-1].strip()

        elif framework == "npm":
            pass_match = re.search(r"(\d+)\s+(?:passing|passed)", combined)
            fail_match = re.search(r"(\d+)\s+(?:failing|failed)", combined)
            if pass_match:
                passed = int(pass_match.group(1))
            if fail_match:
                failed = int(fail_match.group(1))
            if failed > 0:
                traceback_snippet = stderr.strip() if stderr.strip() else stdout[-500:].strip()

        return passed, failed, skipped, traceback_snippet


# Global singleton instance
workspace_test_runner = WorkspaceTestRunner()
