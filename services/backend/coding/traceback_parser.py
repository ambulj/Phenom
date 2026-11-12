"""
Multi-Runner Traceback & Error Parser Engine.
Extracts structured diagnostic context from pytest, vitest, tsc, cargo, and python failures.

Part of Phenom 8.0 Proactive Dev Build Sentinel (DEV-02).
"""

import re
from typing import Optional
from pydantic import BaseModel, Field


class BuildFailureDiagnostic(BaseModel):
    runner: str = Field(..., description="Test or build runner: pytest, vitest, tsc, cargo, python")
    failing_file: str = Field(..., description="File path associated with the failure")
    line_number: Optional[int] = Field(default=None, description="Line number where failure occurred")
    test_name: Optional[str] = Field(default=None, description="Test function or suite name if applicable")
    error_type: str = Field(..., description="Class or category of error, e.g. AssertionError, TS2304")
    error_message: str = Field(..., description="Descriptive error message")
    raw_snippet: str = Field(default="", description="Original error context line")


class TracebackParser:
    """
    Parses compiler, test runner, and language runtime error logs into structured diagnostics.
    """

    PYTEST_FAILED_RE = re.compile(
        r"FAILED\s+([^\s:]+)::([^\s]+)\s+-\s+([A-Za-z0-9_.]*(?:Error|Exception|AssertionError)?):\s*(.+)",
        re.MULTILINE,
    )
    PYTEST_SIMPLE_RE = re.compile(
        r"FAILED\s+([^\s:]+)::([^\s]+)\s+-\s+(.+)",
        re.MULTILINE,
    )
    VITEST_FAILED_RE = re.compile(
        r"(?:FAIL|FAILED)\s+([^\s]+)(?:\s*>\s*([^\n]+))?",
        re.MULTILINE,
    )
    TSC_ERROR_RE = re.compile(
        r"^([^(]+)\((\d+),(\d+)\):\s+error\s+(TS\d+):\s+(.+)$",
        re.MULTILINE,
    )
    CARGO_ERROR_RE = re.compile(
        r"error\[(E\d+)\]:\s+(.+)\n\s+-->\s+([^:]+):(\d+):(\d+)",
        re.MULTILINE,
    )
    PYTHON_TRACEBACK_RE = re.compile(
        r'File "([^"]+)", line (\d+), in (.+?)\n(?:\s+.*?\n)*\s*([A-Za-z0-9_.]*(?:Error|Exception)):\s*(.+)',
        re.MULTILINE,
    )

    def parse_pytest(self, output: str) -> Optional[BuildFailureDiagnostic]:
        match = self.PYTEST_FAILED_RE.search(output)
        if match:
            file_path, test_name, err_type, err_msg = match.groups()
            return BuildFailureDiagnostic(
                runner="pytest",
                failing_file=file_path.strip(),
                test_name=test_name.strip(),
                error_type=err_type.strip() or "AssertionError",
                error_message=err_msg.strip(),
                raw_snippet=match.group(0),
            )
        simple = self.PYTEST_SIMPLE_RE.search(output)
        if simple:
            file_path, test_name, err_msg = simple.groups()
            err_type = "AssertionError"
            if ":" in err_msg:
                parts = err_msg.split(":", 1)
                err_type, err_msg = parts[0].strip(), parts[1].strip()
            return BuildFailureDiagnostic(
                runner="pytest",
                failing_file=file_path.strip(),
                test_name=test_name.strip(),
                error_type=err_type,
                error_message=err_msg,
                raw_snippet=simple.group(0),
            )
        return None

    def parse_vitest(self, output: str) -> Optional[BuildFailureDiagnostic]:
        match = self.VITEST_FAILED_RE.search(output)
        if match:
            file_path = match.group(1).strip()
            test_name = match.group(2).strip() if match.group(2) else None
            # Look for AssertionError or Error line
            err_msg = "Test suite failed"
            err_type = "AssertionError"
            err_match = re.search(r"(?:AssertionError|Error):\s*(.+)", output)
            if err_match:
                err_msg = err_match.group(1).strip()
            return BuildFailureDiagnostic(
                runner="vitest",
                failing_file=file_path,
                test_name=test_name,
                error_type=err_type,
                error_message=err_msg,
                raw_snippet=match.group(0),
            )
        return None

    def parse_tsc(self, output: str) -> Optional[BuildFailureDiagnostic]:
        match = self.TSC_ERROR_RE.search(output)
        if match:
            file_path, line_str, _, err_code, err_msg = match.groups()
            return BuildFailureDiagnostic(
                runner="tsc",
                failing_file=file_path.strip(),
                line_number=int(line_str),
                error_type=err_code.strip(),
                error_message=err_msg.strip(),
                raw_snippet=match.group(0),
            )
        return None

    def parse_cargo(self, output: str) -> Optional[BuildFailureDiagnostic]:
        match = self.CARGO_ERROR_RE.search(output)
        if match:
            err_code, err_msg, file_path, line_str, _ = match.groups()
            return BuildFailureDiagnostic(
                runner="cargo",
                failing_file=file_path.strip(),
                line_number=int(line_str),
                error_type=f"error[{err_code}]",
                error_message=err_msg.strip(),
                raw_snippet=match.group(0),
            )
        return None

    def parse_python(self, output: str) -> Optional[BuildFailureDiagnostic]:
        # Reverse search to find the innermost / last traceback entry
        matches = list(self.PYTHON_TRACEBACK_RE.finditer(output))
        if matches:
            last = matches[-1]
            file_path, line_str, func_name, err_type, err_msg = last.groups()
            return BuildFailureDiagnostic(
                runner="python",
                failing_file=file_path.strip(),
                line_number=int(line_str),
                test_name=func_name.strip(),
                error_type=err_type.strip(),
                error_message=err_msg.strip(),
                raw_snippet=last.group(0),
            )
        return None

    def parse(self, output: str) -> Optional[BuildFailureDiagnostic]:
        """
        Unified parser testing all runners in order of specificity.
        """
        if not output:
            return None

        # Try specific runners
        if "FAILED" in output and "::" in output:
            diag = self.parse_pytest(output)
            if diag:
                return diag

        if "FAIL" in output or "vitest" in output:
            diag = self.parse_vitest(output)
            if diag:
                return diag

        if "error TS" in output:
            diag = self.parse_tsc(output)
            if diag:
                return diag

        if "error[E" in output:
            diag = self.parse_cargo(output)
            if diag:
                return diag

        if "Traceback (most recent call last):" in output:
            diag = self.parse_python(output)
            if diag:
                return diag

        return None
