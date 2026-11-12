"""Metacognitive Auditing, Reflection & Planning Strategy Tools.

Combines Milestone 23 Metacognitive Auditing & Calibration Tools:
1. audit_execution_trajectory (Tier 0)
2. record_reflection_note (Tier 1)
3. get_metacognitive_calibration_stats (Tier 0)

And Milestone 28 Planning Introspection & Strategy Reflection Tools:
4. evaluate_metacognitive_drift (Tier 0)
5. reflect_on_plan_efficiency (Tier 0)
6. record_strategy_heuristic (Tier 1)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.metacognition.reflective_auditor import (
    reflective_auditor,
    ExecutionStep,
    TrajectoryAudit,
)
from services.backend.metacognition.reflection_vault_logger import reflection_vault_logger
from services.backend.planning.metacognitive_evaluator import metacognitive_evaluator
from services.backend.planning.strategy_reflector import strategy_reflector


# ==========================================
# 1. Audit Execution Trajectory (Tier 0) - M23
# ==========================================

class AuditExecutionTrajectoryArgs(BaseModel):
    user_intent: str = Field(..., description="Original goal or user prompt")
    steps: List[Dict[str, Any]] = Field(..., description="List of ExecutionStep dictionaries")
    prior_confidence: Optional[float] = Field(default=0.90, description="Estimated confidence before run (0.0 to 1.0)")


def audit_execution_trajectory_preview(args: Dict[str, Any]) -> str:
    intent = args.get("user_intent", "task")
    steps_len = len(args.get("steps", []))
    return f"Audit trajectory of {steps_len} steps against user intent '{intent[:45]}...'."


@registry.register(
    name="audit_execution_trajectory",
    tier=0,
    description="Audits completed tool execution trajectory, calculates epistemic confidence and calibration accuracy scores.",
    args_schema=AuditExecutionTrajectoryArgs,
    preview_fn=audit_execution_trajectory_preview,
    can_remember_per_folder=False,
)
def handle_audit_execution_trajectory(
    user_intent: str,
    steps: List[Dict[str, Any]],
    prior_confidence: Optional[float] = 0.90,
) -> Dict[str, Any]:
    step_objs = [ExecutionStep(**s) for s in steps]
    audit = reflective_auditor.audit_trajectory(
        user_intent=user_intent,
        steps=step_objs,
        prior_confidence=prior_confidence or 0.90,
    )
    return audit.model_dump()


# ==========================================
# 2. Record Reflection Note (Tier 1) - M23
# ==========================================

class RecordReflectionNoteArgs(BaseModel):
    audit_id: str = Field(..., description="Trajectory audit identifier to persist as reflection note")


def record_reflection_note_preview(args: Dict[str, Any]) -> str:
    aid = args.get("audit_id", "audit")
    return f"Persist structured metacognitive reflection note for audit '{aid}' under .phenom/reflection/."


@registry.register(
    name="record_reflection_note",
    tier=1,
    description="Writes a structured post-mortem reflection note with frontmatter metadata to .phenom/reflection/.",
    args_schema=RecordReflectionNoteArgs,
    preview_fn=record_reflection_note_preview,
    can_remember_per_folder=False,
)
def handle_record_reflection_note(audit_id: str) -> Dict[str, Any]:
    audit = reflective_auditor.get_audit(audit_id)
    if not audit:
        return {"error": f"Trajectory audit '{audit_id}' not found"}

    filepath = reflection_vault_logger.log_reflection_note(audit)
    return {
        "status": "recorded",
        "audit_id": audit_id,
        "filepath": filepath,
        "calibration_score": audit.calibration_score,
    }


# ==========================================
# 3. Get Metacognitive Calibration Stats (Tier 0) - M23
# ==========================================

class GetMetacognitiveCalibrationStatsArgs(BaseModel):
    pass


def get_metacognitive_calibration_stats_preview(args: Dict[str, Any]) -> str:
    return "Inspect aggregate metacognitive calibration scores and recent execution trajectory audits."


@registry.register(
    name="get_metacognitive_calibration_stats",
    tier=0,
    description="Returns aggregate confidence calibration metrics, audit counts, and drift statistics.",
    args_schema=GetMetacognitiveCalibrationStatsArgs,
    preview_fn=get_metacognitive_calibration_stats_preview,
    can_remember_per_folder=False,
)
def handle_get_metacognitive_calibration_stats() -> Dict[str, Any]:
    return reflective_auditor.get_calibration_stats()


# Programmatic aliases M23
audit_execution_trajectory = handle_audit_execution_trajectory
record_reflection_note = handle_record_reflection_note
get_metacognitive_calibration_stats = handle_get_metacognitive_calibration_stats


# ==========================================
# 4. Evaluate Metacognitive Drift (Tier 0) - M28
# ==========================================

class EvaluateMetacognitiveDriftArgs(BaseModel):
    target_id: str = Field(..., description="Plan tree ID or goal objective to evaluate for cognitive drift and reasoning quality.")


def preview_evaluate_metacognitive_drift(args: Dict[str, Any]) -> str:
    tid = args.get("target_id", "active_plan")
    return f"Evaluate reasoning trajectory efficiency, cognitive drift, and hallucination risk for '{tid}'."


@registry.register(
    name="evaluate_metacognitive_drift",
    tier=0,
    description="Evaluates reasoning trajectory efficiency, semantic drift, and hallucination risk scores for an active plan tree.",
    args_schema=EvaluateMetacognitiveDriftArgs,
    preview_fn=preview_evaluate_metacognitive_drift,
    can_remember_per_folder=False,
)
def handle_evaluate_metacognitive_drift(
    target_id: str,
) -> Dict[str, Any]:
    report = metacognitive_evaluator.evaluate_plan(target_id)
    return report.model_dump()


# ==========================================
# 5. Reflect on Plan Efficiency (Tier 0) - M28
# ==========================================

class ReflectOnPlanEfficiencyArgs(BaseModel):
    target_id: str = Field(..., description="Target plan tree ID or goal to reflect on.")


def preview_reflect_on_plan_efficiency(args: Dict[str, Any]) -> str:
    tid = args.get("target_id", "active_plan")
    return f"Synthesize strategic reflection recommendations and matching heuristics for '{tid}'."


@registry.register(
    name="reflect_on_plan_efficiency",
    tier=0,
    description="Synthesizes reflective planning recommendations and retrieves matching strategy heuristics for a target plan tree.",
    args_schema=ReflectOnPlanEfficiencyArgs,
    preview_fn=preview_reflect_on_plan_efficiency,
    can_remember_per_folder=False,
)
def handle_reflect_on_plan_efficiency(
    target_id: str,
) -> Dict[str, Any]:
    return strategy_reflector.reflect_on_plan_efficiency(target_id)


# ==========================================
# 6. Record Strategy Heuristic (Tier 1) - M28
# ==========================================

class RecordStrategyHeuristicArgs(BaseModel):
    domain: str = Field(..., description="Strategic domain: DAG_DECOMPOSITION, SANDBOX_ISOLATION, SLA_VERIFICATION, CONCURRENCY, etc.")
    rule_pattern: str = Field(..., description="Actionable planning heuristic or guideline rule pattern.")
    initial_confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Initial confidence weighting [0.0 - 1.0].")


def preview_record_strategy_heuristic(args: Dict[str, Any]) -> str:
    dom = args.get("domain", "GENERAL")
    rule = args.get("rule_pattern", "Rule")[:35]
    return f"Record or reinforce strategic planning heuristic in domain '{dom}': '{rule}'."


@registry.register(
    name="record_strategy_heuristic",
    tier=1,
    description="Records a new planning meta-heuristic or reinforces existing heuristic confidence upon repeated successful observation.",
    args_schema=RecordStrategyHeuristicArgs,
    preview_fn=preview_record_strategy_heuristic,
    can_remember_per_folder=False,
)
def handle_record_strategy_heuristic(
    domain: str,
    rule_pattern: str,
    initial_confidence: float = 0.85,
) -> Dict[str, Any]:
    heuristic = strategy_reflector.record_heuristic(
        domain=domain,
        rule_pattern=rule_pattern,
        initial_confidence=initial_confidence,
    )
    return {
        "status": "RECORDED",
        "heuristic": heuristic.model_dump(),
    }
