"""Safety-Wrapped World-Model Simulation Tools.

Registers tools with ToolRegistry for projecting plan counterfactuals,
inspecting the symbolic virtual state, and forecasting side-effects (Phase 26-03 SIM-01 / EVA-02).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.simulation.world_model_simulator import (
    world_model_simulator,
    VirtualSystemState,
)
from services.backend.simulation.counterfactual_evaluator import (
    counterfactual_evaluator,
    CounterfactualEvaluationReport,
)


# ==========================================
# 1. Simulate Plan Counterfactuals (Tier 0)
# ==========================================

class SimulatePlanCounterfactualsArgs(BaseModel):
    plan_title: str = Field(..., description="Descriptive title of the plan to evaluate")
    steps: List[Dict[str, Any]] = Field(..., description="List of plan action steps with action, target, payload")


def simulate_plan_counterfactuals_preview(args: Dict[str, Any]) -> str:
    title = args.get("plan_title", "Untitled Plan")
    step_count = len(args.get("steps", []))
    return f"Simulate plan counterfactuals for '{title}' ({step_count} steps) in virtual sandbox."


@registry.register(
    name="simulate_plan_counterfactuals",
    tier=0,
    description="Simulates nominal and counterfactual execution branches for a plan candidate before real OS dispatch.",
    args_schema=SimulatePlanCounterfactualsArgs,
    preview_fn=simulate_plan_counterfactuals_preview,
    can_remember_per_folder=False,
)
def handle_simulate_plan_counterfactuals(
    plan_title: str,
    steps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    report = counterfactual_evaluator.evaluate_plan(plan_title=plan_title, steps=steps)
    return report.model_dump()


# ==========================================
# 2. Evaluate World Model State (Tier 0)
# ==========================================

class EvaluateWorldModelStateArgs(BaseModel):
    include_files: bool = Field(True, description="Whether to include virtual filesystem entries in state report")


def evaluate_world_model_state_preview(args: Dict[str, Any]) -> str:
    return "Retrieve current symbolic state snapshot from the in-memory world model simulator."


@registry.register(
    name="evaluate_world_model_state",
    tier=0,
    description="Inspects the current symbolic representation of the virtual environment in memory.",
    args_schema=EvaluateWorldModelStateArgs,
    preview_fn=evaluate_world_model_state_preview,
    can_remember_per_folder=False,
)
def handle_evaluate_world_model_state(include_files: bool = True) -> Dict[str, Any]:
    state = world_model_simulator.get_state()
    res = state.model_dump()
    if not include_files:
        res["files"] = f"{len(state.files)} virtual files (omitted)"
    return res


# ==========================================
# 3. Forecast Side Effects (Tier 0)
# ==========================================

class ForecastSideEffectsArgs(BaseModel):
    steps: List[Dict[str, Any]] = Field(..., description="Planned execution steps to analyze")


def forecast_side_effects_preview(args: Dict[str, Any]) -> str:
    cnt = len(args.get("steps", []))
    return f"Forecast side-effects and risk factors for {cnt} planned operations."


@registry.register(
    name="forecast_side_effects",
    tier=0,
    description="Analyzes planned operations to project collateral side-effects (mutations, window shifts, process lifecycle).",
    args_schema=ForecastSideEffectsArgs,
    preview_fn=forecast_side_effects_preview,
    can_remember_per_folder=False,
)
def handle_forecast_side_effects(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    effects = counterfactual_evaluator.forecast_side_effects(steps=steps)
    return {
        "side_effect_count": len(effects),
        "side_effects": effects,
    }
