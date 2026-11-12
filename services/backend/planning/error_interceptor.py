"""Error Interceptor & Taxonomy Classifier for Phenom Autonomous Planning (Milestone 28 Phase 3).

Intercepts step execution failures, analyzes error signatures, and maps them to standard
fault taxonomies (PERMISSION_DENIED, RESOURCE_NOT_FOUND, TIMEOUT_INTERRUPT, MALFORMED_OUTPUT, ENVIRONMENT_FAULT)
with zero cloud egress (HEAL-01.1, HEAL-01.2).
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.planning.goal_decomposition_engine import Rule8ViolationError

logger = logging.getLogger("phenom.planning.error_interceptor")


class ErrorTaxonomy(str, Enum):
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    TIMEOUT_INTERRUPT = "TIMEOUT_INTERRUPT"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    ENVIRONMENT_FAULT = "ENVIRONMENT_FAULT"
    UNKNOWN_FAULT = "UNKNOWN_FAULT"


class DiagnosedError(BaseModel):
    error_id: str = Field(default_factory=lambda: f"err_{uuid.uuid4().hex[:8]}")
    taxonomy: ErrorTaxonomy
    raw_message: str
    target_node_id: str
    target_tree_id: str
    confidence: float = 0.90  # 0.0 - 1.0
    recommended_strategy: str
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class ErrorInterceptor:
    """Intercepts and classifies execution exceptions using heuristic pattern matching."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    # Heuristic signature patterns
    _TAXONOMY_PATTERNS = [
        (
            ErrorTaxonomy.PERMISSION_DENIED,
            re.compile(r"(permission\s*denied|access\s*denied|eacces|unauthorized|forbidden|read-only\s*filesystem|privilege)", re.I),
            "ELEVATE_OR_ISOLATE_IN_SANDBOX",
        ),
        (
            ErrorTaxonomy.RESOURCE_NOT_FOUND,
            re.compile(r"(no\s*such\s*file|not\s*found|enoent|missing\s*dependency|module\s*not\s*found|undefined\s*variable)", re.I),
            "RECONSTRUCT_OR_PULL_DEPENDENCY",
        ),
        (
            ErrorTaxonomy.TIMEOUT_INTERRUPT,
            re.compile(r"(timed?\s*out|deadline\s*exceeded|etimedout|sla\s*breach|hung\s*process|operation\s*cancelled)", re.I),
            "CHUNKED_RETRY_WITH_ADAPTIVE_SLA",
        ),
        (
            ErrorTaxonomy.MALFORMED_OUTPUT,
            re.compile(r"(jsondecodeerror|parse\s*error|invalid\s*schema|validation\s*error|syntaxerror|unexpected\s*token)", re.I),
            "SCHEMA_REPAIR_AND_SANITIZATION",
        ),
        (
            ErrorTaxonomy.ENVIRONMENT_FAULT,
            re.compile(r"(out\s*of\s*memory|oom|device\s*busy|locked|socket\s*closed|connection\s*reset|disk\s*full)", re.I),
            "FLUSH_TRANSIENT_BUFFERS_AND_RETRY",
        ),
    ]

    def __init__(self) -> None:
        self._interception_history: List[DiagnosedError] = []

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Error interceptor halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: error diagnostics involving payments is strictly prohibited. Found: {text}"
            )

    def diagnose_error(
        self,
        raw_error: str,
        target_tree_id: str,
        target_node_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DiagnosedError:
        """Diagnoses a raw execution error and classifies it into an actionable error taxonomy."""
        self._check_guardian()
        self._validate_rule_8(raw_error)
        self._validate_rule_8(target_tree_id)
        self._validate_rule_8(target_node_id)

        matched_taxonomy = ErrorTaxonomy.UNKNOWN_FAULT
        matched_strategy = "GENERIC_FALLBACK_AND_NOTIFY"
        matched_confidence = 0.50

        for taxonomy, pattern, strategy in self._TAXONOMY_PATTERNS:
            if pattern.search(raw_error):
                matched_taxonomy = taxonomy
                matched_strategy = strategy
                matched_confidence = 0.95
                break

        diagnosis = DiagnosedError(
            taxonomy=matched_taxonomy,
            raw_message=raw_error,
            target_tree_id=target_tree_id,
            target_node_id=target_node_id,
            confidence=matched_confidence,
            recommended_strategy=matched_strategy,
            context=context or {},
        )

        self._interception_history.append(diagnosis)
        return diagnosis

    def get_history(self) -> List[DiagnosedError]:
        self._check_guardian()
        return list(self._interception_history)


# Global singleton instance
error_interceptor = ErrorInterceptor()
