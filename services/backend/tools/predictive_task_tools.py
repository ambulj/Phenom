"""Safety-Wrapped Predictive Task Anticipation & Ambient Pipelining Tools.

Registers tools with ToolRegistry for workflow action anticipation, background cache
prewarming, and action card dismissal (Phase 23-04 PRED-01 / AUT-04).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.proactive.task_anticipation_engine import task_anticipation_engine
from services.backend.proactive.cache_prewarmer import cache_prewarmer


# ==========================================
# 1. Predict Next Actions (Tier 0)
# ==========================================

class PredictNextActionsArgs(BaseModel):
    current_action: Optional[str] = Field(
        default=None,
        description="The user's current or most recent workflow action (e.g. 'git_commit', 'edit_code', 'open_project')",
    )
    threshold: Optional[float] = Field(
        default=0.40,
        description="Minimum conditional probability threshold (0.0 to 1.0) to return predictions",
    )
    limit: Optional[int] = Field(
        default=5,
        description="Maximum number of anticipated actions to return",
    )


def predict_next_actions_preview(args: Dict[str, Any]) -> str:
    ca = args.get("current_action", "unspecified")
    thresh = args.get("threshold", 0.40)
    return f"Predict next anticipated workflow actions following '{ca}' (threshold: {thresh})."


@registry.register(
    name="predict_next_actions",
    tier=0,
    description="Calculates Markov conditional transition probabilities and anticipates the user's next workflow actions.",
    args_schema=PredictNextActionsArgs,
    preview_fn=predict_next_actions_preview,
    can_remember_per_folder=False,
)
def handle_predict_next_actions(
    current_action: Optional[str] = None,
    threshold: float = 0.40,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    predictions = task_anticipation_engine.predict_next_actions(
        current_action=current_action,
        threshold=threshold,
        limit=limit,
    )
    return [p.model_dump() for p in predictions]


# ==========================================
# 2. Prewarm Workflow Cache (Tier 0)
# ==========================================

class PrewarmWorkflowCacheArgs(BaseModel):
    target_name: str = Field(..., description="Target symbol, filename, or workflow step to pre-warm")
    target_type: Optional[str] = Field(
        default="ast_symbols",
        description="Target type: 'ast_symbols', 'file_context', 'tool_schema', or 'prompt_template'",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional metadata or context tags for the pre-warm operation",
    )


def prewarm_workflow_cache_preview(args: Dict[str, Any]) -> str:
    tn = args.get("target_name", "target")
    tt = args.get("target_type", "ast_symbols")
    return f"Prewarm background cache for target '{tn}' ({tt})."


@registry.register(
    name="prewarm_workflow_cache",
    tier=0,
    description="Asynchronously pre-warms AST symbols and code contexts for anticipated workflow targets.",
    args_schema=PrewarmWorkflowCacheArgs,
    preview_fn=prewarm_workflow_cache_preview,
    can_remember_per_folder=False,
)
def handle_prewarm_workflow_cache(
    target_name: str,
    target_type: str = "ast_symbols",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entry = cache_prewarmer.prewarm_target(
        target_name=target_name,
        target_type=target_type,
        metadata=metadata or {},
    )
    return entry.model_dump()


# ==========================================
# 3. Dismiss Action Card (Tier 0)
# ==========================================

class DismissActionCardArgs(BaseModel):
    action_id: str = Field(..., description="Unique action ID or identifier of the anticipated action card to dismiss")


def dismiss_action_card_preview(args: Dict[str, Any]) -> str:
    aid = args.get("action_id", "action")
    return f"Soft-dismiss anticipated action card '{aid}' without destroying transition models."


@registry.register(
    name="dismiss_action_card",
    tier=0,
    description="Soft-dismisses an anticipated action card while preserving underlying transition weights (Rule 7 non-destructibility).",
    args_schema=DismissActionCardArgs,
    preview_fn=dismiss_action_card_preview,
    can_remember_per_folder=False,
)
def handle_dismiss_action_card(action_id: str) -> Dict[str, Any]:
    return task_anticipation_engine.dismiss_action_card(action_id=action_id)
