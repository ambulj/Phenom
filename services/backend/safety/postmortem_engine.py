"""Autonomous Post-Mortem Root-Cause Reflection Engine (Milestone 49 Phase 2, REFL-01).

Analyzes tool and subagent failure traces to diagnose root causes, extract deterministic
failure signatures, and formulate preventive remediation strategies.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional

from services.backend.schemas.reflective_postmortem import (
    FailureCategory,
    FailureTrace,
    PostMortemAnalysis,
)
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.safety.postmortem_engine")


class PostMortemEngine:
    """Evaluates raw execution failure traces into structured diagnostic post-mortems."""

    _RULE_8_PATTERN = re.compile(
        r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
        re.IGNORECASE,
    )

    _CREDENTIAL_PATTERN = re.compile(
        r"(?i)['\"]?\b(api[_-]?key|secret|token|password|bearer|auth[_-]?token|passwd|pwd)\b['\"]?\s*[:=\s]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"
    )

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._analyses: Dict[str, PostMortemAnalysis] = {}

    def _assert_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Post-mortem analysis aborted.")

    def _sanitize_text(self, text: str) -> str:
        if not text:
            return ""
        if self._RULE_8_PATTERN.search(text):
            text = self._RULE_8_PATTERN.sub("[REDACTED_FINANCIAL]", text)
        text = self._CREDENTIAL_PATTERN.sub(r"\1: [REDACTED_SECRET]", text)
        return text

    def analyze(self, trace: FailureTrace) -> PostMortemAnalysis:
        """Decomposes a FailureTrace into a structured PostMortemAnalysis."""
        self._assert_guardian()

        with self._lock:
            clean_msg = self._sanitize_text(trace.error_message)
            category = self._classify_category(trace.exception_type, clean_msg)
            signature = self._generate_signature(trace.tool_name, category, clean_msg)

            root_cause, remediation, heuristic_dict = self._synthesize_remediation(
                trace.tool_name, category, signature, clean_msg, trace.input_arguments
            )

            analysis_id = f"pm_{int(time.time() * 1000)}_{trace.task_id[:8]}"
            analysis = PostMortemAnalysis(
                analysis_id=analysis_id,
                task_id=trace.task_id,
                tool_name=trace.tool_name,
                category=category,
                failure_signature=signature,
                root_cause_summary=root_cause,
                remediation_strategy=remediation,
                proposed_heuristic=heuristic_dict,
                confidence=0.95,
                timestamp=time.time(),
            )
            self._analyses[analysis_id] = analysis
            return analysis

    def _classify_category(self, exc_type: str, msg: str) -> FailureCategory:
        text = f"{exc_type} {msg}".lower()
        if any(w in text for w in ("timeout", "timed out", "deadline exceeded")):
            return FailureCategory.TIMEOUT
        if any(w in text for w in ("notfound", "not found", "no such file", "does not exist", "missing target")):
            return FailureCategory.RESOURCE_NOT_FOUND
        if any(w in text for w in ("validation", "invalid argument", "value_error", "out of range", "type error")):
            return FailureCategory.VALIDATION_FAILED
        if any(w in text for w in ("permission", "denied", "unauthorized", "rule 8", "rule 4", "forbidden")):
            return FailureCategory.SAFETY_RESTRICTION
        if any(w in text for w in ("precondition", "prerequisite", "not ready", "not running", "window not focused")):
            return FailureCategory.PRECONDITION_FAILED
        if any(w in text for w in ("connection refused", "econnreset", "socket", "network", "subsystem")):
            return FailureCategory.ENVIRONMENT_ERROR
        return FailureCategory.UNKNOWN_ERROR

    def _generate_signature(self, tool_name: str, category: FailureCategory, msg: str) -> str:
        # Extract core tokens from message for signature
        tokens = re.findall(r"[A-Za-z_]{3,}", msg.lower())
        sig_tokens = "_".join(tokens[:4]) if tokens else "error"
        raw = f"{tool_name}|{category.value}|{sig_tokens}"
        sig_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
        return f"sig_{tool_name}_{category.value.lower()}_{sig_hash}"

    def _synthesize_remediation(
        self,
        tool_name: str,
        category: FailureCategory,
        signature: str,
        clean_msg: str,
        args: Dict[str, Any],
    ) -> tuple[str, str, Dict[str, Any]]:
        if category == FailureCategory.RESOURCE_NOT_FOUND:
            root_cause = f"Tool '{tool_name}' failed because target resource was missing: {clean_msg}"
            remediation = f"Enforce resource existence verification pre-check prior to invoking '{tool_name}'."
            heuristic = {
                "rule_id": f"heur_{signature}",
                "tool_name": tool_name,
                "failure_signature": signature,
                "description": f"Pre-check resource existence for {tool_name}",
                "constraint_expression": "assert args.get('path') is None or os.path.exists(str(args.get('path'))), 'Target path does not exist'",
                "planner_guideline": f"Before calling '{tool_name}', always verify that target file, window, or resource exists.",
            }
        elif category == FailureCategory.TIMEOUT:
            root_cause = f"Tool '{tool_name}' execution exceeded maximum time limit: {clean_msg}"
            remediation = f"Clamp execution timeout and split long-running operation into smaller checkpoints."
            heuristic = {
                "rule_id": f"heur_{signature}",
                "tool_name": tool_name,
                "failure_signature": signature,
                "description": f"Timeout clamp and async checkpointing for {tool_name}",
                "constraint_expression": "args.get('timeout', 30.0) <= 60.0",
                "planner_guideline": f"Keep timeouts for '{tool_name}' bounded to 60s max and poll for completion asynchronously.",
            }
        elif category == FailureCategory.PRECONDITION_FAILED:
            root_cause = f"Tool '{tool_name}' invoked when target application or window was not in expected active state."
            remediation = f"Enforce semantic window focus assertion before dispatching desktop input."
            heuristic = {
                "rule_id": f"heur_{signature}",
                "tool_name": tool_name,
                "failure_signature": signature,
                "description": f"Enforce window focus precondition for {tool_name}",
                "constraint_expression": "args.get('target_window') is not None",
                "planner_guideline": f"Prior to calling '{tool_name}', explicitly assert that the required target window is active.",
            }
        elif category == FailureCategory.VALIDATION_FAILED:
            root_cause = f"Tool '{tool_name}' received invalid argument format or out-of-range value: {clean_msg}"
            remediation = f"Sanitize and clamp tool input arguments against schema boundaries."
            heuristic = {
                "rule_id": f"heur_{signature}",
                "tool_name": tool_name,
                "failure_signature": signature,
                "description": f"Input validation guard for {tool_name}",
                "constraint_expression": "all(v is not None for v in args.values())",
                "planner_guideline": f"Validate all arguments for '{tool_name}' against schema constraints before dispatching.",
            }
        elif category == FailureCategory.SAFETY_RESTRICTION:
            root_cause = f"Operation triggered Phenom Safety Gate restriction: {clean_msg}"
            remediation = f"Strictly prohibit restricted parameters or prompt injection payloads."
            heuristic = {
                "rule_id": f"heur_{signature}",
                "tool_name": tool_name,
                "failure_signature": signature,
                "description": f"Safety restriction guard for {tool_name}",
                "constraint_expression": "not any(k in str(args).lower() for k in ('checkout', 'payment', 'credit_card'))",
                "planner_guideline": f"Never invoke '{tool_name}' with financial, checkout, or credential payloads.",
            }
        else:
            root_cause = f"Unexpected failure in tool '{tool_name}': {clean_msg}"
            remediation = f"Wrap execution in circuit breaker and report diagnostic stack to operator."
            heuristic = {
                "rule_id": f"heur_{signature}",
                "tool_name": tool_name,
                "failure_signature": signature,
                "description": f"General circuit breaker guard for {tool_name}",
                "constraint_expression": "True",
                "planner_guideline": f"Handle '{tool_name}' with safe fallback handling.",
            }

        return root_cause, remediation, heuristic

    def get_analysis(self, analysis_id: str) -> Optional[PostMortemAnalysis]:
        self._assert_guardian()
        with self._lock:
            return self._analyses.get(analysis_id)

    def list_all_analyses(self) -> List[PostMortemAnalysis]:
        self._assert_guardian()
        with self._lock:
            return list(self._analyses.values())
