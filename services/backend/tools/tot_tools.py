"""
Hierarchical Tree-of-Thought (ToT) Goal Engine Safety Tools (SAF-01, SAF-02).
Registers Tier 0 and Tier 1 governance tools in ToolRegistry for goal decomposition,
step execution, status inspection, dynamic branch pruning, and goal abortion.
"""

from typing import Any, Dict, Optional

from services.backend.orchestrator.dag_state import dag_state_manager
from services.backend.orchestrator.metacognition import metacognitive_reflector
from services.backend.orchestrator.tot_planner import tot_planner
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.tot import (
    GoalDAG,
    NodeStatus,
    TotAbortGoalArgs,
    TotCreateGoalDagArgs,
    TotExecuteStepArgs,
    TotGetDagStatusArgs,
    TotPruneBranchArgs,
)

# Active In-Memory Goal DAG Registry
_active_dags: Dict[str, GoalDAG] = {}


def get_active_dag(dag_id: str) -> Optional[GoalDAG]:
    """Retrieve an active GoalDAG instance by ID."""
    return _active_dags.get(dag_id)


def register_active_dag(dag: GoalDAG) -> None:
    """Register or update a GoalDAG in active memory."""
    _active_dags[dag.dag_id] = dag


def default_step_executor(node: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Default step executor for DAG nodes.
    Simulates operational execution and updates shared context safely.
    """
    if guardian.is_halted:
        raise PermissionError("Execution halted by Guardian kill switch.")

    step_output = {
        "executed_action": getattr(node, "action_type", "unknown"),
        "title": getattr(node, "title", "step"),
        "tier": getattr(node, "tier", 1),
        "status": "success",
    }
    context[f"result_{getattr(node, 'node_id', 'step')}"] = step_output
    return step_output


@registry.register(
    name="tot_create_goal_dag",
    tier=1,
    description="Decomposes a complex objective into a Hierarchical Tree-of-Thought Goal DAG with primary and contingency branches.",
    args_schema=TotCreateGoalDagArgs,
    preview_fn=lambda a: (
        f"Decompose objective into Hierarchical Tree-of-Thought Goal DAG: "
        f"'{a.get('goal_description', '')[:60]}...' (Max Contingencies: {a.get('max_contingency_branches', 2)})"
    ),
)
def tot_create_goal_dag(
    goal_description: str,
    max_contingency_branches: int = 2,
    exploration_depth: int = 3,
) -> Dict[str, Any]:
    """Create a new hierarchical Goal DAG with topological validation."""
    if guardian.is_halted:
        raise PermissionError("Execution halted by Guardian kill switch.")

    dag = tot_planner.plan_objective(
        goal_description=goal_description,
        max_contingency_branches=max_contingency_branches,
        exploration_depth=exploration_depth,
    )
    register_active_dag(dag)

    active_branch = dag.branches.get(dag.active_branch_id)
    return {
        "success": True,
        "dag_id": dag.dag_id,
        "goal_description": dag.goal_description,
        "status": dag.status,
        "active_branch_id": dag.active_branch_id,
        "active_branch_name": active_branch.name if active_branch else "",
        "total_nodes": len(dag.nodes),
        "total_branches": len(dag.branches),
        "overall_progress_pct": dag.overall_progress_pct,
    }


@registry.register(
    name="tot_execute_step",
    tier=1,
    description="Advances an active Goal DAG by executing the next ready frontier node or a specified ready node.",
    args_schema=TotExecuteStepArgs,
    preview_fn=lambda a: (
        f"Execute step for Goal DAG '{a.get('dag_id')}' (Node: {a.get('node_id') or 'next ready'})"
    ),
)
def tot_execute_step(
    dag_id: str,
    node_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute the next ready node in the active Goal DAG."""
    if guardian.is_halted:
        raise PermissionError("Execution halted by Guardian kill switch.")

    dag = get_active_dag(dag_id)
    if not dag:
        return {"success": False, "error": f"Goal DAG '{dag_id}' not found."}

    ready_nodes = tot_planner.get_ready_nodes(dag)

    target_node = None
    if node_id:
        target_node = dag.nodes.get(node_id)
        if not target_node:
            return {"success": False, "error": f"Node '{node_id}' not found in DAG."}
        if target_node not in ready_nodes:
            return {
                "success": False,
                "error": f"Node '{node_id}' is not in the ready frontier. Dependencies unsatisfied or status is not PENDING.",
            }
    else:
        if not ready_nodes:
            if dag.status == "COMPLETED":
                return {
                    "success": True,
                    "message": "All nodes in active branch have completed successfully.",
                    "status": dag.status,
                    "overall_progress_pct": dag.overall_progress_pct,
                }
            return {
                "success": False,
                "error": "No ready nodes available in the active branch frontier.",
                "status": dag.status,
            }
        target_node = ready_nodes[0]

    # Execute step with retry budget and self-healing rollback support
    res = dag_state_manager.execute_node_with_retry(
        dag=dag,
        node=target_node,
        execute_fn=default_step_executor,
    )
    register_active_dag(dag)

    return {
        **res,
        "dag_id": dag.dag_id,
        "dag_status": dag.status,
        "active_branch_id": dag.active_branch_id,
        "overall_progress_pct": dag.overall_progress_pct,
    }


@registry.register(
    name="tot_get_dag_status",
    tier=0,
    description="Returns read-only status, topological graph structure, progress %, and reflections for a Goal DAG.",
    args_schema=TotGetDagStatusArgs,
    preview_fn=lambda a: f"Inspect Goal DAG topology and execution status for '{a.get('dag_id')}' (Read-Only)",
)
def tot_get_dag_status(dag_id: str) -> Dict[str, Any]:
    """Retrieve full status, topology, and reflection history for a Goal DAG."""
    # Tier 0 read-only inspection
    dag = get_active_dag(dag_id)
    if not dag:
        return {"success": False, "error": f"Goal DAG '{dag_id}' not found."}

    ready_nodes = []
    if not tot_planner.is_halted:
        ready_nodes = [n.node_id for n in tot_planner.get_ready_nodes(dag)]

    return {
        "success": True,
        "dag_id": dag.dag_id,
        "goal_description": dag.goal_description,
        "status": dag.status,
        "active_branch_id": dag.active_branch_id,
        "overall_progress_pct": dag.overall_progress_pct,
        "ready_frontier": ready_nodes,
        "nodes": {nid: n.model_dump() for nid, n in dag.nodes.items()},
        "branches": {bid: b.model_dump() for bid, b in dag.branches.items()},
        "checkpoint_count": len(dag.checkpoints),
        "reflection_count": len(dag.reflections),
        "recent_reflections": [r.model_dump() for r in dag.reflections[-5:]],
    }


@registry.register(
    name="tot_prune_branch",
    tier=1,
    description="Prunes an unviable branch in a Goal DAG and automatically switches to the best available contingency branch.",
    args_schema=TotPruneBranchArgs,
    preview_fn=lambda a: (
        f"Prune branch '{a.get('branch_id')}' in Goal DAG '{a.get('dag_id')}' (Reason: {a.get('reason') or 'Unviable'})"
    ),
)
def tot_prune_branch(
    dag_id: str,
    branch_id: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Prune an unviable branch and switch to contingency."""
    if guardian.is_halted:
        raise PermissionError("Execution halted by Guardian kill switch.")

    dag = get_active_dag(dag_id)
    if not dag:
        return {"success": False, "error": f"Goal DAG '{dag_id}' not found."}

    switched = metacognitive_reflector.prune_branch(
        dag=dag,
        branch_id=branch_id,
        reason=reason or "Manual pruning requested via tot_prune_branch",
    )
    register_active_dag(dag)

    return {
        "success": True,
        "dag_id": dag.dag_id,
        "pruned_branch_id": branch_id,
        "switched_to_contingency": switched,
        "active_branch_id": dag.active_branch_id,
        "dag_status": dag.status,
    }


@registry.register(
    name="tot_abort_goal",
    tier=1,
    description="Aborts execution of a Goal DAG, rolls back to safe checkpoint, and halts further step progression.",
    args_schema=TotAbortGoalArgs,
    preview_fn=lambda a: (
        f"Abort execution and roll back Goal DAG '{a.get('dag_id')}' (Reason: {a.get('reason') or 'User abort'})"
    ),
)
def tot_abort_goal(
    dag_id: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Abort a Goal DAG and roll back state to safe checkpoint."""
    if guardian.is_halted:
        raise PermissionError("Execution halted by Guardian kill switch.")

    dag = get_active_dag(dag_id)
    if not dag:
        return {"success": False, "error": f"Goal DAG '{dag_id}' not found."}

    # Rollback to earliest safe checkpoint if any
    if dag.checkpoints:
        dag_state_manager.rollback_to_checkpoint(dag, checkpoint_id=dag.checkpoints[0].checkpoint_id)

    dag.status = "ABORTED"
    dag.updated_at = dag_state_manager.calculate_progress(dag)
    register_active_dag(dag)

    return {
        "success": True,
        "dag_id": dag.dag_id,
        "status": "ABORTED",
        "reason": reason or "Aborted by user or operator",
    }
