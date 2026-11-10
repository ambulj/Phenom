"""
Safety-Wrapped Swarm Task Orchestrator Tools.
Registers tools with ToolRegistry for DAG decomposition, wave-based parallel subagent
execution, state telemetry, and emergency aborts (Phase 22-01 SWM-01 / AUT-03).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.swarm.dag_orchestrator import dag_orchestrator, DAGNode
from services.backend.swarm.subagent_pool import subagent_pool


# ==========================================
# 1. Create Swarm Task DAG (Tier 0)
# ==========================================

class CreateSwarmTaskDAGArgs(BaseModel):
    goal: str = Field(..., description="High-level objective to decompose into topological task DAG")
    custom_nodes: Optional[List[Dict[str, Any]]] = Field(default=None, description="Explicit list of custom DAGNode dictionaries if not using auto-decomposition")

def create_swarm_task_dag_preview(args: Dict[str, Any]) -> str:
    g = args.get("goal", "task")
    return f"Decompose objective '{g[:45]}...' into topologically sorted swarm DAG with execution waves."

@registry.register(
    name="create_swarm_task_dag",
    tier=0,
    description="Decomposes a complex objective into dependency-aware topological execution waves for isolated subagents.",
    args_schema=CreateSwarmTaskDAGArgs,
    preview_fn=create_swarm_task_dag_preview,
    can_remember_per_folder=False
)
def handle_create_swarm_task_dag(
    goal: str,
    custom_nodes: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    if custom_nodes:
        nodes = [DAGNode(**n) for n in custom_nodes]
        dag = dag_orchestrator.create_dag(goal=goal, nodes_list=nodes)
    else:
        dag = dag_orchestrator.decompose_goal_into_dag(goal=goal)

    return {
        "dag_id": dag.dag_id,
        "goal": dag.goal,
        "total_nodes": len(dag.nodes),
        "total_waves": len(dag.waves),
        "waves": dag.waves,
        "status": dag.status,
    }


# ==========================================
# 2. Execute Swarm DAG Wave (Tier 1)
# ==========================================

class ExecuteSwarmDAGWaveArgs(BaseModel):
    dag_id: str = Field(..., description="Swarm DAG run identifier")
    wave_index: Optional[int] = Field(default=None, description="Wave index to execute. Defaults to current wave.")

def execute_swarm_dag_wave_preview(args: Dict[str, Any]) -> str:
    d_id = args.get("dag_id", "dag")
    w = args.get("wave_index", "current")
    return f"Execute wave {w} of swarm task DAG '{d_id}' with parallel subagent workers."

@registry.register(
    name="execute_swarm_dag_wave",
    tier=1,
    description="Executes a wave of independent DAG nodes in parallel using isolated subagents with automatic retry.",
    args_schema=ExecuteSwarmDAGWaveArgs,
    preview_fn=execute_swarm_dag_wave_preview,
    can_remember_per_folder=False
)
async def handle_execute_swarm_dag_wave(
    dag_id: str,
    wave_index: Optional[int] = None
) -> Dict[str, Any]:
    return await dag_orchestrator.execute_wave(dag_id=dag_id, wave_index=wave_index)


# ==========================================
# 3. Get Swarm DAG Status (Tier 0)
# ==========================================

class GetSwarmDAGStatusArgs(BaseModel):
    dag_id: str = Field(..., description="Swarm DAG run identifier")

def get_swarm_dag_status_preview(args: Dict[str, Any]) -> str:
    d_id = args.get("dag_id", "dag")
    return f"Inspect live execution progress, node states, and subagent pool for DAG '{d_id}'."

@registry.register(
    name="get_swarm_dag_status",
    tier=0,
    description="Returns live DAG node states, current execution wave index, and subagent pool telemetry.",
    args_schema=GetSwarmDAGStatusArgs,
    preview_fn=get_swarm_dag_status_preview,
    can_remember_per_folder=False
)
def handle_get_swarm_dag_status(dag_id: str) -> Dict[str, Any]:
    dag = dag_orchestrator.get_dag(dag_id)
    if not dag:
        return {"error": f"DAG '{dag_id}' not found"}

    nodes_summary = {
        nid: {"name": n.name, "role": n.role, "status": n.status, "duration_ms": n.duration_ms}
        for nid, n in dag.nodes.items()
    }

    return {
        "dag_id": dag.dag_id,
        "goal": dag.goal,
        "status": dag.status,
        "current_wave": dag.current_wave_index,
        "total_waves": len(dag.waves),
        "waves": dag.waves,
        "nodes": nodes_summary,
        "workers_pool": subagent_pool.get_pool_status(),
        "total_duration_ms": dag.total_duration_ms,
    }


# ==========================================
# 4. Abort Swarm Execution (Tier 0)
# ==========================================

class AbortSwarmExecutionArgs(BaseModel):
    dag_id: str = Field(..., description="Swarm DAG run identifier to abort")

def abort_swarm_execution_preview(args: Dict[str, Any]) -> str:
    d_id = args.get("dag_id", "dag")
    return f"Immediately abort in-flight swarm DAG '{d_id}' and cancel pending subagents."

@registry.register(
    name="abort_swarm_execution",
    tier=0,
    description="Emergency cancellation of active swarm DAG and subagent tasks.",
    args_schema=AbortSwarmExecutionArgs,
    preview_fn=abort_swarm_execution_preview,
    can_remember_per_folder=False
)
def handle_abort_swarm_execution(dag_id: str) -> Dict[str, Any]:
    success = dag_orchestrator.abort_dag(dag_id)
    return {"dag_id": dag_id, "aborted": success}


# Aliases for direct programmatic access
create_swarm_task_dag = handle_create_swarm_task_dag
execute_swarm_dag_wave = handle_execute_swarm_dag_wave
get_swarm_dag_status = handle_get_swarm_dag_status
abort_swarm_execution = handle_abort_swarm_execution

