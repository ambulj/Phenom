"""Safe GUI Step Executor for Phenom (Milestone 25 Phase 2).

Safely dispatches virtual GUI actions with pre-action coordinate verification,
human takeover abort detection, dry-run simulations, and Guardian SLA halt (ACT-02.2, EXEC-03.1).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.actor.gui_action_synthesizer import (
    GuiActionStep,
    GuiActionPlan,
    Rule8ViolationError,
)

logger = logging.getLogger("phenom.actor.gui_step_executor")


class StepExecutionResult(BaseModel):
    step_id: int
    action_type: str
    status: str  # SUCCESS, ABORTED_BY_HUMAN, OUT_OF_BOUNDS, FAILED, DRY_RUN
    target_coordinates: Optional[Tuple[int, int]] = None
    execution_duration_ms: float
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlanExecutionSummary(BaseModel):
    plan_id: str
    user_goal: str
    status: str  # COMPLETED, ABORTED_BY_HUMAN, PARTIAL_FAILURE
    completed_steps: int
    total_steps: int
    total_duration_ms: float
    step_results: List[StepExecutionResult]


class GuiStepExecutor:
    """Dispatches virtual desktop interactions under safety bounds and takeover monitoring."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing|stripe|paypal)\b",
        re.IGNORECASE,
    )

    SCREEN_BOUNDS = {"max_x": 1920, "max_y": 1080}

    def __init__(self) -> None:
        self._human_takeover_flag: bool = False
        self._last_cursor_position: Tuple[int, int] = (0, 0)

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. GUI step execution halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: GUI execution involving payments or checkouts is strictly prohibited. Found: {text}"
            )

    def trigger_human_takeover(self) -> None:
        """Trigger simulated human takeover override."""
        self._human_takeover_flag = True

    def reset_human_takeover(self) -> None:
        """Reset human takeover state."""
        self._human_takeover_flag = False

    def execute_step(
        self,
        step: GuiActionStep,
        dry_run: bool = False,
        simulated_human_takeover: bool = False,
    ) -> StepExecutionResult:
        """Execute a single declarative GUI action step."""
        t0 = time.perf_counter()
        self._check_guardian()

        # Rule 8 verification
        self._validate_rule_8(step.description)
        if step.text_payload:
            self._validate_rule_8(step.text_payload)

        # 1. Human Takeover Check
        if self._human_takeover_flag or simulated_human_takeover:
            duration = (time.perf_counter() - t0) * 1000.0
            return StepExecutionResult(
                step_id=step.step_id,
                action_type=step.action_type,
                status="ABORTED_BY_HUMAN",
                target_coordinates=step.target_coordinates,
                execution_duration_ms=round(duration, 3),
                message="Human operator touched mouse or pressed takeover key. Action sequence halted immediately.",
            )

        # 2. Coordinate Bounds Verification
        if step.target_coordinates:
            x, y = step.target_coordinates
            if x < 0 or x > self.SCREEN_BOUNDS["max_x"] or y < 0 or y > self.SCREEN_BOUNDS["max_y"]:
                duration = (time.perf_counter() - t0) * 1000.0
                return StepExecutionResult(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    status="OUT_OF_BOUNDS",
                    target_coordinates=step.target_coordinates,
                    execution_duration_ms=round(duration, 3),
                    message=f"Target coordinates ({x}, {y}) exceed screen bounds (0..1920, 0..1080).",
                )

        # 3. Dry-Run Check
        if dry_run:
            duration = (time.perf_counter() - t0) * 1000.0
            return StepExecutionResult(
                step_id=step.step_id,
                action_type=step.action_type,
                status="DRY_RUN",
                target_coordinates=step.target_coordinates,
                execution_duration_ms=round(duration, 3),
                message=f"[Dry-Run Simulation] Verified {step.action_type} at {step.target_coordinates}.",
            )

        # 4. In a real desktop environment, virtual input is sent via pywin32 / pyautogui / uia
        # Here we simulate the safe dispatch and duration
        duration = (time.perf_counter() - t0) * 1000.0

        return StepExecutionResult(
            step_id=step.step_id,
            action_type=step.action_type,
            status="SUCCESS",
            target_coordinates=step.target_coordinates,
            execution_duration_ms=round(duration, 3),
            message=f"Successfully dispatched {step.action_type} for step {step.step_id}: {step.description}",
        )

    def execute_plan(
        self,
        plan: GuiActionPlan,
        dry_run: bool = False,
        takeover_at_step: Optional[int] = None,
    ) -> PlanExecutionSummary:
        """Execute a full action plan sequentially with takeover and safety guards."""
        t0 = time.perf_counter()
        self._check_guardian()

        results: List[StepExecutionResult] = []
        overall_status = "COMPLETED"

        for step in plan.steps:
            is_takeover = takeover_at_step is not None and step.step_id >= takeover_at_step
            res = self.execute_step(step, dry_run=dry_run, simulated_human_takeover=is_takeover)
            results.append(res)

            if res.status == "ABORTED_BY_HUMAN":
                overall_status = "ABORTED_BY_HUMAN"
                break
            elif res.status not in ("SUCCESS", "DRY_RUN"):
                overall_status = "PARTIAL_FAILURE"
                break

        total_duration = (time.perf_counter() - t0) * 1000.0

        completed = sum(1 for r in results if r.status in ("SUCCESS", "DRY_RUN"))

        return PlanExecutionSummary(
            plan_id=plan.plan_id,
            user_goal=plan.user_goal,
            status=overall_status,
            completed_steps=completed,
            total_steps=len(plan.steps),
            total_duration_ms=round(total_duration, 3),
            step_results=results,
        )


# Singleton instance
gui_step_executor = GuiStepExecutor()
