"""Cross-Application Workflow Orchestrator for Phenom (Milestone 25 Phase 3).

Coordinates inter-application data pipelining, state machines, and context handoffs
across disparate desktop apps (Browser, IDE, Terminal, Notes) with strict safety boundaries (AUT-05.1).
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.orchestrator.cross_app")


class Rule8ViolationError(Exception):
    """Raised when a cross-app workflow involves checkout, payment, or banking automation."""
    pass


class CrossAppStep(BaseModel):
    step_id: int
    app_name: str  # e.g., "Edge", "VSCode", "Windows Terminal", "Obsidian"
    action: str  # EXTRACT_SELECTION, PASTE_TRANSFORM, EXECUTE_COMMAND, SYNC_STATE
    input_payload: Optional[str] = None
    output_variable: Optional[str] = None
    status: str = "PENDING"  # PENDING, SUCCESS, FAILED
    result_data: Optional[str] = None


class CrossAppWorkflow(BaseModel):
    workflow_id: str = Field(default_factory=lambda: f"wf_{uuid.uuid4().hex[:8]}")
    title: str
    steps: List[CrossAppStep]
    shared_pipeline_context: Dict[str, Any] = Field(default_factory=dict)
    status: str = "INITIALIZED"  # INITIALIZED, RUNNING, COMPLETED, FAILED


class CrossAppOrchestrator:
    """Pipelines context and state across desktop applications."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing|stripe|paypal)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._active_workflow: Optional[CrossAppWorkflow] = None

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Cross-app workflow halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: cross-app workflow targeting payments or checkout is strictly prohibited. Found: {text}"
            )

    def create_workflow(self, title: str, steps: List[CrossAppStep]) -> CrossAppWorkflow:
        """Initialize a new multi-app workflow with Rule 8 screening."""
        self._check_guardian()
        self._validate_rule_8(title)
        for s in steps:
            self._validate_rule_8(s.app_name)
            if s.input_payload:
                self._validate_rule_8(s.input_payload)

        wf = CrossAppWorkflow(title=title, steps=steps)
        self._active_workflow = wf
        return wf

    def execute_workflow(self, workflow_id: Optional[str] = None) -> CrossAppWorkflow:
        """Sequentially execute cross-app workflow steps, propagating output variables."""
        self._check_guardian()

        wf = self._active_workflow
        if not wf:
            raise ValueError("No active workflow to execute.")

        wf.status = "RUNNING"
        context = dict(wf.shared_pipeline_context)

        for step in wf.steps:
            self._check_guardian()
            # Resolve variable interpolation if input_payload has ${var}
            payload = step.input_payload or ""
            if "${" in payload:
                for k, v in context.items():
                    payload = payload.replace(f"${{{k}}}", str(v))

            self._validate_rule_8(payload)

            # Simulate app execution
            if step.action == "EXTRACT_SELECTION":
                output = f"Extracted from {step.app_name}: sample data payload"
            elif step.action == "PASTE_TRANSFORM":
                output = f"Transformed in {step.app_name} with: {payload}"
            elif step.action == "EXECUTE_COMMAND":
                output = f"Command output from {step.app_name}: OK"
            else:
                output = f"Synced with {step.app_name}"

            step.status = "SUCCESS"
            step.result_data = output

            if step.output_variable:
                context[step.output_variable] = output

        wf.shared_pipeline_context = context
        wf.status = "COMPLETED"
        return wf

    def get_active_workflow(self) -> Optional[CrossAppWorkflow]:
        """Query currently active workflow status."""
        self._check_guardian()
        return self._active_workflow


# Singleton instance
cross_app_orchestrator = CrossAppOrchestrator()
