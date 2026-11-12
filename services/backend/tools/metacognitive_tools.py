"""Metacognitive Introspection & Strategy Reflection Tools for Phenom Autonomous Planning (Milestone 28 Phase 4).

Registers 3 planning tools in ToolRegistry:
1. evaluate_metacognitive_drift (Tier 0)
2. reflect_on_plan_efficiency (Tier 0)
3. record_strategy_heuristic (Tier 1)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.planning.metacognitive_evaluator import metacognitive_evaluator
from services.backend.planning.strategy_reflector import strategy_reflector


# ==========================================
# 1. Evaluate Metacognitive Drift (Tier 0)
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
# 2. Reflect on Plan Efficiency (Tier 0)
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
# 3. Record Strategy Heuristic (Tier 1)
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
