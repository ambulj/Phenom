"""
Asynchronous Diagnostic Test Runner Daemon.
Executes test suites and compiler checks (pytest, vitest, tsc) in workspace or
isolated worktree sandboxes, extracting structured failure diagnostics.

Part of Phenom 20.0 Sovereign Autonomous Developer (DEV-02.2, SAF-01, SAF-02).
"""

import asyncio
import os
import re
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from services.backend.coding.traceback_parser import TracebackParser, BuildFailureDiagnostic
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.coding.test_runner")


class TestRunResult(BaseModel):
    runner: str = Field(..., description="Test or build runner: pytest, vitest, tsc, generic")
    status: str = Field(..., description="Run outcome: passed, failed, error, timeout, aborted")
    total_tests: int = Field(default=0, description="Total number of tests discovered/run")
    passed_tests: int = Field(default=0, description="Number of passed tests")
    failed_tests: int = Field(default=0, description="Number of failed tests")
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    diagnostics: List[BuildFailureDiagnostic] = Field(default_factory=list, description="Extracted failure diagnostics")
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")


class TestRunnerDaemon:
    """
    Executes and parses test/compiler runs inside workspace or isolated worktrees.
    """

    PYTEST_SUMMARY_RE = re.compile(
        r"(?:=+\s*)?(?:(\d+)\s+passed)?[,\s]*(?:(\d+)\s+failed)?[,\s]*(?:(\d+)\s+errors?)?.*(?:in\s+([\d.]+)\s*s)?",
        re.IGNORECASE,
    )

    def __init__(self):
        self.parser = TracebackParser()

    async def run_pytest(
        self,
        target_path: Optional[str] = None,
        working_dir: Optional[str] = None,
        timeout_seconds: int = 60,
        extra_args: Optional[List[str]] = None,
    ) -> TestRunResult:
        """
        Runs pytest asynchronously against target_path inside working_dir.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Test execution halted.")
        t0 = time.perf_counter()

        cmd = [sys.executable, "-m", "pytest", "-v"]
        if target_path:
            cmd.append(target_path)
        if extra_args:
            cmd.extend(extra_args)

        cwd = working_dir or str(Path.cwd())

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=float(timeout_seconds),
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except Exception:
                    pass
                t1 = time.perf_counter()
                return TestRunResult(
                    runner="pytest",
                    status="timeout",
                    duration_ms=(t1 - t0) * 1000.0,
                    stderr=f"Test runner exceeded timeout limit of {timeout_seconds}s",
                )

            t1 = time.perf_counter()
            duration_ms = (t1 - t0) * 1000.0
            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")
            combined_output = stdout_str + "\n" + stderr_str

            # Parse counts
            passed = 0
            failed = 0
            for line in combined_output.splitlines():
                if "passed" in line or "failed" in line:
                    match = self.PYTEST_SUMMARY_RE.search(line)
                    if match:
                        p_str, f_str, e_str, _ = match.groups()
                        if p_str:
                            passed = max(passed, int(p_str))
                        if f_str:
                            failed = max(failed, int(f_str))
                        if e_str:
                            failed += int(e_str)

            # Parse diagnostics
            diagnostics: List[BuildFailureDiagnostic] = []
            diag = self.parser.parse_pytest(combined_output)
            if diag:
                diagnostics.append(diag)
            else:
                # Try generic python traceback if any
                py_diag = self.parser.parse_python(combined_output)
                if py_diag:
                    diagnostics.append(py_diag)

            status = "passed" if process.returncode == 0 else "failed"
            if process.returncode != 0 and failed == 0 and len(diagnostics) == 0:
                # General error
                status = "error"

            total = passed + failed

            return TestRunResult(
                runner="pytest",
                status=status,
                total_tests=total,
                passed_tests=passed,
                failed_tests=failed,
                duration_ms=duration_ms,
                diagnostics=diagnostics,
                stdout=stdout_str,
                stderr=stderr_str,
            )

        except Exception as e:
            t1 = time.perf_counter()
            return TestRunResult(
                runner="pytest",
                status="error",
                duration_ms=(t1 - t0) * 1000.0,
                stderr=str(e),
            )

    async def run_tsc(
        self,
        working_dir: Optional[str] = None,
        timeout_seconds: int = 60,
    ) -> TestRunResult:
        """
        Runs TypeScript compiler check (tsc --noEmit) asynchronously.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Test execution halted.")
        t0 = time.perf_counter()

        cmd = ["npx", "tsc", "--noEmit"]
        cwd = working_dir or str(Path.cwd() / "apps" / "desktop")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=float(timeout_seconds),
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except Exception:
                    pass
                t1 = time.perf_counter()
                return TestRunResult(
                    runner="tsc",
                    status="timeout",
                    duration_ms=(t1 - t0) * 1000.0,
                    stderr=f"TypeScript compiler check exceeded timeout of {timeout_seconds}s",
                )

            t1 = time.perf_counter()
            duration_ms = (t1 - t0) * 1000.0
            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")
            combined_output = stdout_str + "\n" + stderr_str

            diagnostics: List[BuildFailureDiagnostic] = []
            diag = self.parser.parse_tsc(combined_output)
            if diag:
                diagnostics.append(diag)

            status = "passed" if process.returncode == 0 else "failed"

            return TestRunResult(
                runner="tsc",
                status=status,
                total_tests=1,
                passed_tests=1 if status == "passed" else 0,
                failed_tests=1 if status == "failed" else 0,
                duration_ms=duration_ms,
                diagnostics=diagnostics,
                stdout=stdout_str,
                stderr=stderr_str,
            )

        except Exception as e:
            t1 = time.perf_counter()
            return TestRunResult(
                runner="tsc",
                status="error",
                duration_ms=(t1 - t0) * 1000.0,
                stderr=str(e),
            )


# Global singleton
test_runner_daemon = TestRunnerDaemon()
