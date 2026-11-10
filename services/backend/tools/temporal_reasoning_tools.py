"""
Safety-Wrapped Temporal Intent Memory & Decision Reasoning Tools.
Registers tools with ToolRegistry for recording temporal preferences, querying intent graphs,
and explaining decision rationales (Phase 22-02 MEM-03 / RSN-01).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.memory.temporal_intent_graph import (
    temporal_intent_graph,
    TemporalIntentNode,
)
from services.backend.reasoning.decision_explainer import (
    decision_explainer,
    DecisionAlternative,
)


# ==========================================
# 1. Record Temporal Preference (Tier 1)
# ==========================================

class RecordTemporalPreferenceArgs(BaseModel):
    category: str = Field(..., description="Preference domain e.g. 'coding_style', 'toolchain', 'privacy'")
    statement: str = Field(..., description="Directive or preference statement")
    supersedes_id: Optional[str] = Field(default=None, description="Optional ID of older preference being replaced")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional contextual tags")

def record_temporal_preference_preview(args: Dict[str, Any]) -> str:
    cat = args.get("category", "general")
    stmt = args.get("statement", "")
    sup = args.get("supersedes_id")
    sup_txt = f" (superseding '{sup}')" if sup else ""
    return f"Record temporal preference in category '{cat}'{sup_txt}: '{stmt[:50]}...'"

@registry.register(
    name="record_temporal_preference",
    tier=1,
    description="Records a new user or system preference with temporal validity tracking and supersession lineage.",
    args_schema=RecordTemporalPreferenceArgs,
    preview_fn=record_temporal_preference_preview,
    can_remember_per_folder=False
)
def handle_record_temporal_preference(
    category: str,
    statement: str,
    supersedes_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    node = temporal_intent_graph.record_preference(
        category=category,
        statement=statement,
        context=context,
        supersedes_id=supersedes_id,
    )
    return {
        "intent_id": node.intent_id,
        "category": node.category,
        "statement": node.statement,
        "valid_from": node.valid_from,
        "superseded_by": node.superseded_by,
        "is_active": node.is_active,
    }


# ==========================================
# 2. Query Temporal Intent Graph (Tier 0)
# ==========================================

class QueryTemporalIntentGraphArgs(BaseModel):
    category: Optional[str] = Field(default=None, description="Filter by category")
    intent_id_lineage: Optional[str] = Field(default=None, description="Optional intent_id to trace complete lineage")

def query_temporal_intent_graph_preview(args: Dict[str, Any]) -> str:
    cat = args.get("category", "all")
    lin = args.get("intent_id_lineage")
    return f"Query temporal intent graph for category '{cat}'" + (f" and trace lineage for '{lin}'" if lin else "")

@registry.register(
    name="query_temporal_intent_graph",
    tier=0,
    description="Retrieves active preferences or walks historical version lineage across the temporal intent graph.",
    args_schema=QueryTemporalIntentGraphArgs,
    preview_fn=query_temporal_intent_graph_preview,
    can_remember_per_folder=False
)
def handle_query_temporal_intent_graph(
    category: Optional[str] = None,
    intent_id_lineage: Optional[str] = None,
) -> Dict[str, Any]:
    if intent_id_lineage:
        lineage = temporal_intent_graph.get_preference_lineage(intent_id_lineage)
        return {
            "mode": "lineage",
            "intent_id": intent_id_lineage,
            "lineage": [n.model_dump() for n in lineage],
        }

    active_nodes = temporal_intent_graph.query_active_preferences(category=category)
    conflicts = temporal_intent_graph.detect_conflicts(category=category)

    return {
        "mode": "active_preferences",
        "category": category or "all",
        "count": len(active_nodes),
        "preferences": [n.model_dump() for n in active_nodes],
        "conflicts": conflicts,
    }


# ==========================================
# 3. Explain Decision Rationale (Tier 0)
# ==========================================

class ExplainDecisionRationaleArgs(BaseModel):
    objective: str = Field(..., description="Goal or task being executed")
    chosen_plan: str = Field(..., description="The chosen strategy or execution plan")
    alternatives: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of considered alternative options")

def explain_decision_rationale_preview(args: Dict[str, Any]) -> str:
    obj = args.get("objective", "task")
    plan = args.get("chosen_plan", "chosen plan")
    return f"Synthesize counterfactual explanation for why '{plan}' was selected for '{obj[:40]}...'."

@registry.register(
    name="explain_decision_rationale",
    tier=0,
    description="Provides an evidence-based explanation of why a specific plan was chosen over candidate alternatives.",
    args_schema=ExplainDecisionRationaleArgs,
    preview_fn=explain_decision_rationale_preview,
    can_remember_per_folder=False
)
def handle_explain_decision_rationale(
    objective: str,
    chosen_plan: str,
    alternatives: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    alt_objs = [DecisionAlternative(**a) for a in alternatives] if alternatives else None
    explanation = decision_explainer.explain_decision(
        objective=objective,
        chosen_plan=chosen_plan,
        alternatives=alt_objs,
    )
    return explanation.model_dump()


# Aliases for direct programmatic access
record_temporal_preference = handle_record_temporal_preference
query_temporal_intent_graph = handle_query_temporal_intent_graph
explain_decision_rationale = handle_explain_decision_rationale
