"""Self-Healing & Error Interception Tools for Phenom Autonomous Planning (Milestone 28 Phase 3).

Registers 3 planning tools in ToolRegistry:
1. intercept_and_heal_failure (Tier 1)
2. diagnose_execution_error (Tier 0)
3. get_active_healing_journal (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.planning.error_interceptor import error_interceptor
from services.backend.planning.self_healing_orchestrator import self_healing_orchestrator


# ==========================================
# 1. Intercept and Heal Failure (Tier 1)
# ==========================================

class InterceptAndHealFailureArgs(BaseModel):
    target_tree_id: str = Field(..., description="ID of the plan tree containing the failing node.")
    failing_node_id: str = Field(..., description="Node ID within the tree that experienced execution failure.")
    raw_error: str = Field(..., description="Raw exception message or stack trace symptom.")


def preview_intercept_and_heal_failure(args: Dict[str, Any]) -> str:
    tid = args.get("target_tree_id", "active_tree")
    nid = args.get("failing_node_id", "failing_node")
    err = args.get("raw_error", "Unknown error")[:35]
    return f"Diagnose error '{err}' and dynamically graft compensatory repair sub-plan under node '{nid}' in tree '{tid}'."


@registry.register(
    name="intercept_and_heal_failure",
    tier=1,
    description="Diagnoses execution failure, classifies fault taxonomy, and dynamically grafts compensatory sub-plans into the active plan tree.",
    args_schema=InterceptAndHealFailureArgs,
    preview_fn=preview_intercept_and_heal_failure,
    can_remember_per_folder=False,
)
def handle_intercept_and_heal_failure(
    target_tree_id: str,
    failing_node_id: str,
    raw_error: str,
) -> Dict[str, Any]:
    return self_healing_orchestrator.heal_failure(
        target_tree_id=target_tree_id,
        failing_node_id=failing_node_id,
        raw_error=raw_error,
    )


# ==========================================
# 2. Diagnose Execution Error (Tier 0)
# ==========================================

class DiagnoseExecutionErrorArgs(BaseModel):
    raw_error: str = Field(..., description="Raw error string or exception traceback.")
    target_tree_id: str = Field(..., description="Target plan tree ID.")
    target_node_id: str = Field(..., description="Failing node ID.")


def preview_diagnose_execution_error(args: Dict[str, Any]) -> str:
    err = args.get("raw_error", "Error")[:40]
    return f"Diagnose root cause and taxonomy classification for execution error '{err}'."


@registry.register(
    name="diagnose_execution_error",
    tier=0,
    description="Classifies a raw execution error into standard fault taxonomies (PERMISSION_DENIED, TIMEOUT_INTERRUPT, etc.) and recommends recovery strategies.",
    args_schema=DiagnoseExecutionErrorArgs,
    preview_fn=preview_diagnose_execution_error,
    can_remember_per_folder=False,
)
def handle_diagnose_execution_error(
    raw_error: str,
    target_tree_id: str,
    target_node_id: str,
) -> Dict[str, Any]:
    diagnosis = error_interceptor.diagnose_error(
        raw_error=raw_error,
        target_tree_id=target_tree_id,
        target_node_id=target_node_id,
    )
    return diagnosis.model_dump()


# ==========================================
# 3. Get Active Healing Journal (Tier 0)
# ==========================================

class GetActiveHealingJournalArgs(BaseModel):
    pass


def preview_get_active_healing_journal(args: Dict[str, Any]) -> str:
    return "Retrieve complete self-healing audit journal, diagnosed root causes, and grafted repair sub-plans."


@registry.register(
    name="get_active_healing_journal",
    tier=0,
    description="Retrieves the persistent self-healing audit journal and resolution telemetry records.",
    args_schema=GetActiveHealingJournalArgs,
    preview_fn=preview_get_active_healing_journal,
    can_remember_per_folder=False,
)
def handle_get_active_healing_journal() -> Dict[str, Any]:
    journal = self_healing_orchestrator.get_journal()
    return {
        "total_records": len(journal),
        "journal": journal,
    }
