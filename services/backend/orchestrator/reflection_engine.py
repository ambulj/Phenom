"""
Error Traceback & State Reflection Engine (Phase 47-04, HEAL-01).
Captures stderr, exception tracebacks, and DOM failure states, analyzes root causes,
and synthesizes targeted remediation plans and patches for self-healing loops.
"""

import re
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ErrorCategory(str, Enum):
    SYNTAX = "syntax"
    IMPORT_MISSING = "import_missing"
    FILE_NOT_FOUND = "file_not_found"
    SELECTOR_MISSING = "selector_missing"
    TIMEOUT = "timeout"
    PERMISSION = "permission"
    LOGIC = "logic"
    UNKNOWN = "unknown"


class RetryStrategy(str, Enum):
    PATCH_CODE = "patch_code"
    INSTALL_DEPENDENCY = "install_dependency"
    CREATE_FILE = "create_file"
    ALTERNATIVE_SELECTOR = "alternative_selector"
    RETRY_WITH_DELAY = "retry_with_delay"
    ESCALATE_TO_USER = "escalate_to_user"


class ReflectionDiagnosis(BaseModel):
    """Structured diagnostic and remediation outcome produced by the reflection engine."""
    error_category: ErrorCategory = Field(..., description="Classified error category")
    root_cause: str = Field(..., description="Extracted root cause explanation")
    failing_file: Optional[str] = Field(default=None, description="Path to file where error occurred")
    line_number: Optional[int] = Field(default=None, description="Line number of failure if identifiable")
    proposed_fix: str = Field(..., description="Actionable proposed fix")
    retry_strategy: RetryStrategy = Field(..., description="Recommended remediation strategy")
    patch_diff: Optional[str] = Field(default=None, description="Optional synthesized patch diff")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Confidence score of the diagnosis")


class ReflectionEngine:
    """Diagnoses runtime, syntax, and UI failures to guide self-healing retries."""

    def __init__(self):
        pass

    def diagnose_failure(
        self,
        error_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ReflectionDiagnosis:
        """
        Analyzes standard error text, tracebacks, or DOM diffs and generates actionable diagnosis.
        """
        raw = error_text.strip()
        ctx = context or {}

        # 1. SyntaxError
        syntax_match = re.search(r"SyntaxError:\s*(.*?)(?:\n|\Z)", raw)
        if syntax_match:
            file_match = re.search(r'File "([^"]+)", line (\d+)', raw)
            f_path = file_match.group(1) if file_match else ctx.get("file_path")
            line_no = int(file_match.group(2)) if file_match else None
            msg = syntax_match.group(1).strip()

            return ReflectionDiagnosis(
                error_category=ErrorCategory.SYNTAX,
                root_cause=f"Python syntax violation at line {line_no or 'unknown'}: {msg}",
                failing_file=f_path,
                line_number=line_no,
                proposed_fix=f"Parse AST in-memory and repair syntax around line {line_no or 'failing region'}: {msg}",
                retry_strategy=RetryStrategy.PATCH_CODE,
                confidence=0.95
            )

        # 2. ModuleNotFoundError / ImportError
        import_match = re.search(r"(?:ModuleNotFoundError|ImportError):\s*No module named ['\"]([^'\"]+)['\"]", raw)
        if import_match:
            missing_mod = import_match.group(1).split(".")[0]
            file_match = re.search(r'File "([^"]+)", line (\d+)', raw)
            f_path = file_match.group(1) if file_match else ctx.get("file_path")
            line_no = int(file_match.group(2)) if file_match else None

            return ReflectionDiagnosis(
                error_category=ErrorCategory.IMPORT_MISSING,
                root_cause=f"Missing Python package/module dependency: '{missing_mod}'",
                failing_file=f_path,
                line_number=line_no,
                proposed_fix=f"Verify dependency against typosquatting guard and install '{missing_mod}'",
                retry_strategy=RetryStrategy.INSTALL_DEPENDENCY,
                confidence=0.92
            )

        # 3. FileNotFoundError
        fnf_match = re.search(r"FileNotFoundError:.*?(?:No such file or directory: ['\"]([^'\"]+)['\"]|['\"]([^'\"]+)['\"])", raw)
        if fnf_match or "No such file or directory" in raw:
            missing_path = fnf_match.group(1) or fnf_match.group(2) if fnf_match else "target file"
            return ReflectionDiagnosis(
                error_category=ErrorCategory.FILE_NOT_FOUND,
                root_cause=f"Referenced path does not exist on disk: '{missing_path}'",
                failing_file=missing_path,
                proposed_fix=f"Ensure parent directory exists and initialize missing file: '{missing_path}'",
                retry_strategy=RetryStrategy.CREATE_FILE,
                confidence=0.90
            )

        # 4. DOM / UI Selector Failure
        if any(term in raw.lower() for term in ["selector", "element not found", "cannot find element", "waiting for locator"]):
            selector_match = re.search(r"['\"]([#\.\w\-\[\]=:]+)['\"]", raw)
            selector = selector_match.group(1) if selector_match else "requested selector"
            return ReflectionDiagnosis(
                error_category=ErrorCategory.SELECTOR_MISSING,
                root_cause=f"UI element locator '{selector}' was not found in active application window DOM",
                proposed_fix=f"Refresh DOM tree, scroll element into view, or use fuzzy UIA text/name fallback",
                retry_strategy=RetryStrategy.ALTERNATIVE_SELECTOR,
                confidence=0.88
            )

        # 5. Timeout
        if any(term in raw.lower() for term in ["timeout", "timed out", "timeoutexpired"]):
            return ReflectionDiagnosis(
                error_category=ErrorCategory.TIMEOUT,
                root_cause="Operation exceeded execution timeout limit without completing",
                proposed_fix="Retry with exponential backoff or increase step timeout threshold",
                retry_strategy=RetryStrategy.RETRY_WITH_DELAY,
                confidence=0.85
            )

        # 6. Permission / Security Failure
        if any(term in raw.lower() for term in ["permissionerror", "access is denied", "pathsecurityviolation"]):
            return ReflectionDiagnosis(
                error_category=ErrorCategory.PERMISSION,
                root_cause="Security or filesystem permission policy blocked the requested action",
                proposed_fix="Escalate to operator for explicit confirmation or adjust path allowlist",
                retry_strategy=RetryStrategy.ESCALATE_TO_USER,
                confidence=0.95
            )

        # 7. Generic Logic / Assertion Failure
        assert_match = re.search(r"AssertionError(?::\s*(.*?))?(?:\n|\Z)", raw)
        if assert_match:
            detail = assert_match.group(1) or "Assertion check failed"
            return ReflectionDiagnosis(
                error_category=ErrorCategory.LOGIC,
                root_cause=f"Assertion failure: {detail.strip()}",
                proposed_fix="Inspect expected vs actual state and update logic implementation",
                retry_strategy=RetryStrategy.PATCH_CODE,
                confidence=0.80
            )

        # Default fallback
        return ReflectionDiagnosis(
            error_category=ErrorCategory.UNKNOWN,
            root_cause=f"Unclassified failure: {raw[:150]}",
            proposed_fix="Inspect error logs and request operator guidance",
            retry_strategy=RetryStrategy.ESCALATE_TO_USER,
            confidence=0.50
        )


# Global singleton instance
reflection_engine = ReflectionEngine()
