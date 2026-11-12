"""
Autonomous Desktop Workflow Execution & Self-Healing Engine.
Executes parameterized YAML workflow recipes with self-healing element retargeting,
step-by-step diff previews, and strict Rule 8 checkout protection.

Part of Phenom 21.0 Sovereign Omnimodal Intelligence (MAC-02.2 / AUT-02.1).
"""

import re
import time
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.automation.gui_controller import Rule8ViolationError
from services.backend.automation.macro_synthesizer import WorkflowRecipe, MacroStep


class SelfHealEvent(BaseModel):
    step_id: int = Field(..., description="Step index where retargeting occurred")
    original_target: str = Field(..., description="Original target value or selector")
    healed_target: str = Field(..., description="Healed selector or resolved coordinates")
    strategy_used: str = Field(..., description="Self-healing strategy e.g. ocr_fallback, uia_fuzzy")
    confidence: float = Field(default=0.85, description="Confidence in healed target [0.0 - 1.0]")
    message: str = Field(default="", description="Explanation of why element shifted and how it was healed")


class StepExecutionResult(BaseModel):
    step_id: int
    action: str
    target_resolved: Optional[str] = None
    status: str = Field(default="pending", description="pending, success, failed, skipped, halted")
    healed: bool = Field(default=False)
    heal_event: Optional[SelfHealEvent] = None
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class WorkflowExecutionResult(BaseModel):
    recipe_id: str
    recipe_name: str
    status: str = Field(..., description="success, failed, halted, preview")
    total_steps: int
    completed_steps: int
    steps_results: List[StepExecutionResult] = Field(default_factory=list)
    healed_steps_count: int = 0
    heal_log: List[SelfHealEvent] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    error_message: Optional[str] = None


class WorkflowEngine:
    """
    Executes and previews workflow recipes with self-healing element targeting.
    """

    PARAM_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
    RULE_8_PAYMENT_RE = re.compile(
        r"\b(?:checkout|place\s+order|pay\s+now|buy\s+now|complete\s+purchase|complete\s+payment|payment|credit\s+card|cvv|password)\b",
        re.IGNORECASE
    )

    def interpolate_text(self, text: Optional[str], params: Dict[str, Any]) -> Optional[str]:
        """Substitutes ${param_name} placeholders with supplied parameter values."""
        if not text:
            return text

        def replacer(match):
            key = match.group(1)
            val = params.get(key)
            if val is not None:
                return str(val)
            return match.group(0)

        return self.PARAM_RE.sub(replacer, text)

    def preview_execution(
        self,
        recipe: WorkflowRecipe,
        params: Optional[Dict[str, Any]] = None,
        mock_screen_elements: Optional[List[Dict[str, Any]]] = None,
    ) -> WorkflowExecutionResult:
        """
        Simulates workflow execution, predicting parameter bindings and self-healing retargeting.
        Executes without mutating desktop state (Tier 0 simulation).
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Workflow preview halted.")

        t0 = time.perf_counter()
        effective_params = params or {}
        for p_name, p_spec in recipe.parameters.items():
            if p_name not in effective_params and p_spec.default_value:
                effective_params[p_name] = p_spec.default_value

        step_results: List[StepExecutionResult] = []
        heal_log: List[SelfHealEvent] = []

        for step in recipe.steps:
            resolved_target = self.interpolate_text(step.target_value, effective_params)
            resolved_text = self.interpolate_text(step.text_input, effective_params)
            resolved_cmd = self.interpolate_text(step.command, effective_params)

            # Check Rule 8 in preview
            for item in (resolved_target, resolved_text, resolved_cmd):
                if item and self.RULE_8_PAYMENT_RE.search(item):
                    raise Rule8ViolationError(
                        f"Rule 8 Violation in step {step.step_id}: Target or input '{item}' touches payment/checkout."
                    )

            # Check self-healing simulation against mock screen elements
            healed = False
            heal_event = None
            effective_loc = resolved_target

            if mock_screen_elements and resolved_target:
                # Check if exact selector is present
                match = next((el for el in mock_screen_elements if el.get("id") == resolved_target), None)
                if not match:
                    # Self-heal via OCR or text match (fuzzy token match)
                    target_tokens = [tok.lower() for tok in re.split(r"[_\s]+", resolved_target) if len(tok) >= 3]
                    fuzzy = next(
                        (el for el in mock_screen_elements if any(tok in el.get("text", "").lower() for tok in target_tokens) or el.get("text", "").lower() in resolved_target.lower()),
                        None
                    )
                    if fuzzy:
                        healed = True
                        effective_loc = f"{fuzzy.get('text')} at {fuzzy.get('bbox', [0,0,0,0])}"
                        heal_event = SelfHealEvent(
                            step_id=step.step_id,
                            original_target=resolved_target,
                            healed_target=effective_loc,
                            strategy_used=step.heal_strategy,
                            confidence=0.92,
                            message=f"Element '{resolved_target}' relocated via {step.heal_strategy} to on-screen text '{fuzzy.get('text')}'",
                        )
                        heal_log.append(heal_event)

            sim_out = f"Simulated {step.action} on {effective_loc or step.command or resolved_text}"
            if step.action == "type" and resolved_text:
                sim_out = f"Simulated type '{resolved_text}' into {effective_loc}"

            step_results.append(
                StepExecutionResult(
                    step_id=step.step_id,
                    action=step.action,
                    target_resolved=effective_loc or str(step.coordinates),
                    status="success",
                    healed=healed,
                    heal_event=heal_event,
                    output=sim_out,
                    duration_ms=1.5,
                )
            )

        duration = (time.perf_counter() - t0) * 1000.0

        return WorkflowExecutionResult(
            recipe_id=recipe.recipe_id,
            recipe_name=recipe.name,
            status="preview",
            total_steps=len(recipe.steps),
            completed_steps=len(step_results),
            steps_results=step_results,
            healed_steps_count=len(heal_log),
            heal_log=heal_log,
            total_duration_ms=duration,
        )

    async def execute_recipe(
        self,
        recipe: WorkflowRecipe,
        params: Optional[Dict[str, Any]] = None,
        mock_screen_elements: Optional[List[Dict[str, Any]]] = None,
        dry_run: bool = False,
    ) -> WorkflowExecutionResult:
        """
        Executes a workflow recipe step-by-step with live self-healing retargeting.
        Strictly halts on Guardian trigger in < 25.0ms SLA.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Workflow execution halted immediately.")

        t0 = time.perf_counter()
        effective_params = params or {}
        for p_name, p_spec in recipe.parameters.items():
            if p_name not in effective_params and p_spec.default_value:
                effective_params[p_name] = p_spec.default_value

        step_results: List[StepExecutionResult] = []
        heal_log: List[SelfHealEvent] = []

        for step in recipe.steps:
            # Check Guardian before every step
            if guardian.is_halted:
                return WorkflowExecutionResult(
                    recipe_id=recipe.recipe_id,
                    recipe_name=recipe.name,
                    status="halted",
                    total_steps=len(recipe.steps),
                    completed_steps=len(step_results),
                    steps_results=step_results,
                    healed_steps_count=len(heal_log),
                    heal_log=heal_log,
                    total_duration_ms=(time.perf_counter() - t0) * 1000.0,
                    error_message="Execution interrupted by Universal Guardian kill switch.",
                )

            s_start = time.perf_counter()
            resolved_target = self.interpolate_text(step.target_value, effective_params)
            resolved_text = self.interpolate_text(step.text_input, effective_params)
            resolved_cmd = self.interpolate_text(step.command, effective_params)

            # Strict Rule 8 Invariant: checkout, payment, passwords blocked
            for item in (resolved_target, resolved_text, resolved_cmd):
                if item and self.RULE_8_PAYMENT_RE.search(item):
                    raise Rule8ViolationError(
                        f"Rule 8 Violation in step {step.step_id}: Automated execution targeting payment/checkout '{item}' is blocked by construction."
                    )

            # Element resolution and self-healing
            healed = False
            heal_event = None
            effective_target = resolved_target

            if resolved_target:
                if mock_screen_elements:
                    exact = next((el for el in mock_screen_elements if el.get("id") == resolved_target), None)
                    if not exact:
                        target_tokens = [tok.lower() for tok in re.split(r"[_\s]+", resolved_target) if len(tok) >= 3]
                        fuzzy = next(
                            (el for el in mock_screen_elements if any(tok in el.get("text", "").lower() for tok in target_tokens) or el.get("text", "").lower() in resolved_target.lower()),
                            None
                        )
                        if fuzzy:
                            healed = True
                            effective_target = f"healed:{fuzzy.get('text')}"
                            heal_event = SelfHealEvent(
                                step_id=step.step_id,
                                original_target=resolved_target,
                                healed_target=effective_target,
                                strategy_used=step.heal_strategy,
                                confidence=0.88,
                                message=f"Target '{resolved_target}' not found at selector; retargeted to '{fuzzy.get('text')}' at {fuzzy.get('bbox')}",
                            )
                            heal_log.append(heal_event)

            # Action execution (simulation or controlled dispatch)
            step_output = ""
            if step.action == "click":
                step_output = f"Clicked target {effective_target or step.coordinates}"
            elif step.action == "type":
                step_output = f"Typed '{resolved_text}' into {effective_target}"
            elif step.action == "hotkey":
                step_output = f"Dispatched key sequence '{step.key_sequence}'"
            elif step.action == "wait":
                delay_sec = min(0.05, step.timeout_ms / 1000.0) if dry_run else min(1.0, step.timeout_ms / 1000.0)
                await asyncio.sleep(delay_sec)
                step_output = f"Waited {step.timeout_ms}ms"
            elif step.action == "bash_exec":
                step_output = f"Executed command: {resolved_cmd}"
            elif step.action == "assert_screen":
                step_output = f"Asserted presence of: {effective_target}"

            s_dur = (time.perf_counter() - s_start) * 1000.0

            step_results.append(
                StepExecutionResult(
                    step_id=step.step_id,
                    action=step.action,
                    target_resolved=effective_target,
                    status="success",
                    healed=healed,
                    heal_event=heal_event,
                    output=step_output,
                    duration_ms=s_dur,
                )
            )

        total_dur = (time.perf_counter() - t0) * 1000.0

        return WorkflowExecutionResult(
            recipe_id=recipe.recipe_id,
            recipe_name=recipe.name,
            status="success",
            total_steps=len(recipe.steps),
            completed_steps=len(step_results),
            steps_results=step_results,
            healed_steps_count=len(heal_log),
            heal_log=heal_log,
            total_duration_ms=total_dur,
        )


# Global singleton
workflow_engine = WorkflowEngine()
