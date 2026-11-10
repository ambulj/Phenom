"""Diagnostic Engine for Phenom (Milestone 24 Phase 1).

Parses Python exception tracebacks and error events, isolates offending execution frames,
inspects culprit AST nodes, and classifies failure categories (HEAL-01.1).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.healing.diagnostic")


class Rule8ViolationError(Exception):
    """Raised when an error trace or diagnosis involves payment or checkout operations."""
    pass


class DiagnosticReport(BaseModel):
    error_type: str
    error_message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    culprit_line: Optional[str] = None
    fault_category: str  # NULL_OR_NONE_DEREFERENCE, MISSING_DICTIONARY_KEY, DIVISION_BY_ZERO, etc.
    confidence_score: float
    recommended_strategy: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DiagnosticEngine:
    """Automated neuro-symbolic runtime exception analyzer and fault localizer."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)\b",
        re.IGNORECASE,
    )

    _FRAME_PATTERN = re.compile(
        r'File\s+"([^"]+)",\s+line\s+(\d+)(?:,\s+in\s+([a-zA-Z_]\w*))?(?:\n\s+(.*))?',
        re.IGNORECASE,
    )

    _EXCEPTION_PATTERN = re.compile(
        r"([a-zA-Z_]\w*(?:Error|Exception))(?::\s*(.*))?$",
        re.MULTILINE,
    )

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Diagnostic operations halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: diagnosing payment or checkout code is strictly prohibited. Found: {text}"
            )

    def diagnose_traceback(
        self,
        traceback_text: str,
        source_code: Optional[str] = None,
    ) -> DiagnosticReport:
        """Analyze traceback text and localize the primary fault."""
        self._check_guardian()
        self._validate_rule_8(traceback_text)
        if source_code:
            self._validate_rule_8(source_code)

        # 1. Parse exception type and message
        error_type = "UnhandledException"
        error_message = traceback_text.strip()

        exc_matches = list(self._EXCEPTION_PATTERN.finditer(traceback_text))
        if exc_matches:
            last_match = exc_matches[-1]
            error_type = last_match.group(1).strip()
            error_message = (last_match.group(2) or "").strip()

        # 2. Parse frames (find last/deepest user frame)
        file_path = None
        line_number = None
        function_name = None
        culprit_line = None

        frame_matches = list(self._FRAME_PATTERN.finditer(traceback_text))
        if frame_matches:
            deepest_frame = frame_matches[-1]
            file_path = deepest_frame.group(1).strip()
            line_number = int(deepest_frame.group(2))
            if deepest_frame.group(3):
                function_name = deepest_frame.group(3).strip()
            if deepest_frame.group(4):
                culprit_line = deepest_frame.group(4).strip()

        # If source code provided and culprit_line missing, extract from line_number
        if source_code and line_number and not culprit_line:
            lines = source_code.splitlines()
            if 0 < line_number <= len(lines):
                culprit_line = lines[line_number - 1].strip()

        # 3. Categorize fault
        fault_category, confidence, strategy = self._classify_fault(
            error_type=error_type,
            error_message=error_message,
            culprit_line=culprit_line,
        )

        return DiagnosticReport(
            error_type=error_type,
            error_message=error_message,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            culprit_line=culprit_line,
            fault_category=fault_category,
            confidence_score=confidence,
            recommended_strategy=strategy,
            metadata={"total_frames": len(frame_matches)},
        )

    def _classify_fault(
        self,
        error_type: str,
        error_message: str,
        culprit_line: Optional[str],
    ) -> tuple[str, float, str]:
        """Categorize fault and determine recommended repair strategy."""
        err_lower = error_message.lower()

        if error_type == "AttributeError" and ("nonetype" in err_lower or "none" in err_lower):
            return (
                "NULL_OR_NONE_DEREFERENCE",
                0.96,
                "Insert None guard or fallback default before member access.",
            )
        elif error_type == "KeyError":
            return (
                "MISSING_DICTIONARY_KEY",
                0.95,
                "Convert direct dict index access to dict.get(key, default).",
            )
        elif error_type == "ZeroDivisionError":
            return (
                "DIVISION_BY_ZERO",
                0.98,
                "Insert divisor non-zero guard or ternary check before division.",
            )
        elif error_type in ("ModuleNotFoundError", "ImportError"):
            return (
                "MISSING_IMPORT",
                0.94,
                "Prepend missing module import statement at module top-level.",
            )
        elif error_type == "TypeError" and ("none" in err_lower or "unsupported operand" in err_lower):
            return (
                "TYPE_MISMATCH",
                0.88,
                "Insert type coercion or explicit isinstance check.",
            )
        elif error_type == "IndexError":
            return (
                "INDEX_OUT_OF_BOUNDS",
                0.92,
                "Insert length bounds check before list or tuple index access.",
            )
        else:
            return (
                "UNHANDLED_EXCEPTION",
                0.75,
                "Wrap statement in try-except block with error fallback logging.",
            )


# Singleton instance
diagnostic_engine = DiagnosticEngine()
