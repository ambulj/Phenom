"""Reflective Post-Mortem & Heuristics Tools Registration for Phenom (Milestone 49 Phase 2, REFL-01, REFL-02, REFL-03).

Exposes:
1. `analyze_failure_postmortem` (Tier 0) - Diagnoses root cause and derives failure signatures from traces.
2. `synthesize_heuristic_rule` (Tier 1) - Compiles and persists AST-validated executable constraints.
3. `generate_proactive_briefing` (Tier 0) - Formulates concise spoken morning briefing and workspace staging.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.schemas.reflective_postmortem import (
    FailureCategory,
    FailureTrace,
    HeuristicRule,
    PostMortemAnalysis,
    SpokenMorningBriefing,
    WorkspacePreStagePlan,
)
from services.backend.safety.postmortem_engine import PostMortemEngine
from services.backend.safety.heuristic_synthesizer import HeuristicSynthesizer
from services.backend.safety.proactive_synthesizer import ProactiveSynthesizer

# Singletons
postmortem_engine = PostMortemEngine()
heuristic_synthesizer = HeuristicSynthesizer()
proactive_synthesizer = ProactiveSynthesizer()


# ============================================================================
# 1. analyze_failure_postmortem (Tier 0)
# ============================================================================

class AnalyzeFailurePostmortemArgs(BaseModel):
    task_id: str = Field(..., description="ID of failing task or mission")
    tool_name: str = Field(..., description="Name of tool or subagent that raised error")
    exception_type: str = Field(..., description="Exception class name")
    error_message: str = Field(..., description="Error message text")
    input_arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments supplied to invocation")


def analyze_failure_postmortem_preview(args: Dict[str, Any]) -> str:
    tool = args.get("tool_name", "unknown")
    exc = args.get("exception_type", "error")
    return f"Analyze failure trace for tool '{tool}' with exception '{exc}'."


@registry.register(
    name="analyze_failure_postmortem",
    tier=0,
    description="Analyzes an execution failure trace to determine root cause, failure signature, and remediation strategy.",
    args_schema=AnalyzeFailurePostmortemArgs,
    preview_fn=analyze_failure_postmortem_preview,
    can_remember_per_folder=False,
)
def handle_analyze_failure_postmortem(
    task_id: str,
    tool_name: str,
    exception_type: str,
    error_message: str,
    input_arguments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    trace = FailureTrace(
        task_id=task_id,
        tool_name=tool_name,
        input_arguments=input_arguments or {},
        exception_type=exception_type,
        error_message=error_message,
    )
    analysis = postmortem_engine.analyze(trace)
    return {
        "status": "success",
        "analysis_id": analysis.analysis_id,
        "category": analysis.category.value,
        "failure_signature": analysis.failure_signature,
        "root_cause": analysis.root_cause_summary,
        "remediation_strategy": analysis.remediation_strategy,
        "proposed_heuristic": analysis.proposed_heuristic,
    }


# ============================================================================
# 2. synthesize_heuristic_rule (Tier 1)
# ============================================================================

class SynthesizeHeuristicRuleArgs(BaseModel):
    tool_name: str = Field(..., description="Target tool name or '*' for all tools")
    failure_signature: str = Field(..., description="Signature this rule mitigates")
    description: str = Field(..., description="Purpose of this heuristic constraint")
    constraint_expression: str = Field(..., description="Python boolean assertion or constraint expression")
    planner_guideline: str = Field(..., description="Natural language guideline for DAG planner context")
    rule_id: Optional[str] = Field(default=None, description="Optional custom rule ID")


def synthesize_heuristic_rule_preview(args: Dict[str, Any]) -> str:
    tool = args.get("tool_name", "*")
    sig = args.get("failure_signature", "general")
    return f"Synthesize and persist heuristic rule for '{tool}' mitigating '{sig}'."


@registry.register(
    name="synthesize_heuristic_rule",
    tier=1,
    description="Compiles, AST-validates, and persists an executable heuristic rule into safety storage.",
    args_schema=SynthesizeHeuristicRuleArgs,
    preview_fn=synthesize_heuristic_rule_preview,
    can_remember_per_folder=False,
)
def handle_synthesize_heuristic_rule(
    tool_name: str,
    failure_signature: str,
    description: str,
    constraint_expression: str,
    planner_guideline: str,
    rule_id: Optional[str] = None,
) -> Dict[str, Any]:
    rid = rule_id or f"heur_{failure_signature}"
    rule = heuristic_synthesizer.register_rule(
        rule_id=rid,
        tool_name=tool_name,
        failure_signature=failure_signature,
        description=description,
        constraint_expression=constraint_expression,
        planner_guideline=planner_guideline,
    )
    return {
        "status": "success",
        "rule_id": rule.rule_id,
        "tool_name": rule.tool_name,
        "is_active": rule.is_active,
        "planner_guideline": rule.planner_guideline,
    }


# ============================================================================
# 3. generate_proactive_briefing (Tier 0)
# ============================================================================

class GenerateProactiveBriefingArgs(BaseModel):
    user_name: str = Field(default="Sir", description="Salutation name for spoken briefing")


def generate_proactive_briefing_preview(args: Dict[str, Any]) -> str:
    name = args.get("user_name", "Sir")
    return f"Generate proactive morning briefing and workspace pre-stage plan for {name}."


@registry.register(
    name="generate_proactive_briefing",
    tier=0,
    description="Generates an anticipated proactive morning briefing (<= 60 words) and workspace staging plan.",
    args_schema=GenerateProactiveBriefingArgs,
    preview_fn=generate_proactive_briefing_preview,
    can_remember_per_folder=False,
)
def handle_generate_proactive_briefing(user_name: str = "Sir") -> Dict[str, Any]:
    briefing = proactive_synthesizer.generate_morning_briefing(user_name=user_name)
    stage_plan = proactive_synthesizer.generate_pre_stage_plan()
    return {
        "status": "success",
        "date": briefing.date_str,
        "briefing_text": briefing.briefing_text,
        "word_count": briefing.word_count,
        "priorities": briefing.priorities,
        "pre_stage_plan": stage_plan.model_dump(),
    }
