"""
Metacognitive Self-Reflection & Execution Calibration Engine.
Evaluates completed agentic execution trajectories against user intent, calculates
epistemic confidence and calibration accuracy scores, and synthesizes prompt mitigations.

Part of Phenom 23.0 Sovereign Neural Evolution (META-01.1 / META-01.2).
"""

import time
import uuid
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.automation.gui_controller import Rule8ViolationError

RULE_8_PAYMENT_RE = re.compile(
    r"\b(?:checkout|place\s+order|pay\s+now|buy\s+now|complete\s+purchase|complete\s+payment|payment|credit\s+card|cvv|password)\b",
    re.IGNORECASE
)


class ExecutionStep(BaseModel):
    step_id: int
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="success", description="success, error, retry, skipped")
    latency_ms: float = 0.0
    error_message: Optional[str] = None


class TrajectoryAudit(BaseModel):
    audit_id: str
    user_intent: str
    steps_count: int
    successful_steps: int
    failed_steps: int
    epistemic_confidence: float = Field(..., description="Estimated self-confidence before execution (0.0 to 1.0)")
    calibration_score: float = Field(..., description="Alignment between confidence and actual success (0.0 to 1.0)")
    root_cause_analysis: Optional[str] = None
    suggested_prompt_mitigation: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


class ReflectiveAuditor:
    """
    Audits execution trajectories, assesses calibration drift, and formulates prompt adjustments.
    """

    def __init__(self):
        self._audits: Dict[str, TrajectoryAudit] = {}

    def audit_trajectory(
        self,
        user_intent: str,
        steps: List[ExecutionStep],
        prior_confidence: float = 0.9,
    ) -> TrajectoryAudit:
        """
        Audits an execution trajectory against original intent.
        Strictly verifies Guardian kill switch (< 25.0ms SLA).
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Metacognitive audit halted.")

        if RULE_8_PAYMENT_RE.search(user_intent):
            raise Rule8ViolationError(f"Rule 8 Violation: Cannot audit trajectories targeting payment/checkout: {user_intent}")

        t0 = time.perf_counter()
        aid = f"audit_{uuid.uuid4().hex[:8]}"

        success_count = sum(1 for s in steps if s.status == "success")
        fail_count = len(steps) - success_count
        actual_success_rate = (success_count / len(steps)) if steps else 1.0

        # Calibration score: 1.0 - |prior_confidence - actual_success_rate|
        # 1.0 indicates perfect calibration; lower indicates overconfidence or underconfidence
        calibration = max(0.0, 1.0 - abs(prior_confidence - actual_success_rate))

        root_cause = None
        mitigation = None

        if fail_count > 0:
            first_fail = next((s for s in steps if s.status != "success"), None)
            err_msg = first_fail.error_message if first_fail else "Unknown error"
            root_cause = f"Step {first_fail.step_id} ({first_fail.tool_name}) failed: {err_msg}"
            mitigation = f"Verify preconditions and parameter constraints for tool '{first_fail.tool_name}' prior to dispatch."
        else:
            root_cause = "All execution steps succeeded within nominal SLA parameters."
            mitigation = "Maintain current planning heuristic and wave grouping."

        audit = TrajectoryAudit(
            audit_id=aid,
            user_intent=user_intent,
            steps_count=len(steps),
            successful_steps=success_count,
            failed_steps=fail_count,
            epistemic_confidence=min(1.0, max(0.0, prior_confidence)),
            calibration_score=round(calibration, 4),
            root_cause_analysis=root_cause,
            suggested_prompt_mitigation=mitigation,
            created_at=time.time(),
        )

        self._audits[aid] = audit
        return audit

    def get_audit(self, audit_id: str) -> Optional[TrajectoryAudit]:
        return self._audits.get(audit_id)

    def get_calibration_stats(self) -> Dict[str, Any]:
        """Returns aggregate calibration statistics across all recorded audits."""
        if not self._audits:
            return {
                "total_audits": 0,
                "average_calibration_score": 1.0,
                "average_confidence": 0.95,
            }

        scores = [a.calibration_score for a in self._audits.values()]
        confidences = [a.epistemic_confidence for a in self._audits.values()]

        return {
            "total_audits": len(self._audits),
            "average_calibration_score": round(sum(scores) / len(scores), 4),
            "average_confidence": round(sum(confidences) / len(confidences), 4),
            "recent_audits": [a.model_dump() for a in list(self._audits.values())[-5:]],
        }


# Global singleton
reflective_auditor = ReflectiveAuditor()
