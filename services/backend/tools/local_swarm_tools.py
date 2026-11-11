"""Autonomous Multi-Agent Local Swarm Engine Tools for Phenom (Milestone 30 Phase 2).

Registers 4 specialized local swarm orchestration tools in ToolRegistry:
1. dispatch_local_swarm_task (Tier 1)
2. query_local_swarm_status (Tier 0)
3. terminate_local_swarm_worker (Tier 1)
4. synthesize_local_swarm_results (Tier 0)
"""

import asyncio
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.swarm.swarm_coordinator import (
    swarm_coordinator,
)


# ==========================================
# 1. Dispatch Local Swarm Task (Tier 1)
# ==========================================

class DispatchLocalSwarmTaskArgs(BaseModel):
    agent_name: str = Field(
        ..., description="Target specialized subagent: 'coder', 'research', or 'executive'."
    )
    prompt: str = Field(
        ..., description="Task objective or directive for the specialized subagent to execute."
    )
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional metadata or task parameters."
    )


def preview_dispatch_local_swarm_task(args: Dict[str, Any]) -> str:
    agent = args.get("agent_name", "worker")
    prompt = args.get("prompt", "")
    snippet = (prompt[:60] + "...") if len(prompt) > 60 else prompt
    return f"Dispatch background swarm workstream to [{agent.upper()}]: '{snippet}'"


@registry.register(
    name="dispatch_local_swarm_task",
    tier=1,
    description="Dispatches an asynchronous background task to a specialized local worker (coder, research, executive) (Tier 1 action).",
    args_schema=DispatchLocalSwarmTaskArgs,
    preview_fn=preview_dispatch_local_swarm_task,
    can_remember_per_folder=False,
)
def handle_dispatch_local_swarm_task(
    agent_name: str,
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                task = executor.submit(
                    asyncio.run,
                    swarm_coordinator.dispatch_task(agent_name=agent_name, prompt=prompt, context=context)
                ).result()
        else:
            task = loop.run_until_complete(
                swarm_coordinator.dispatch_task(agent_name=agent_name, prompt=prompt, context=context)
            )
    except RuntimeError:
        task = asyncio.run(
            swarm_coordinator.dispatch_task(agent_name=agent_name, prompt=prompt, context=context)
        )

    return {
        "task_id": task.task_id,
        "agent_name": task.agent_name,
        "status": task.status,
        "result": task.result,
        "latency_ms": task.latency_ms,
        "metadata": task.metadata,
    }


# ==========================================
# 2. Query Local Swarm Status (Tier 0)
# ==========================================

class QueryLocalSwarmStatusArgs(BaseModel):
    pass


def preview_query_local_swarm_status(args: Dict[str, Any]) -> str:
    return "Query status, latency metrics, and active backlog across all local swarm workers"


@registry.register(
    name="query_local_swarm_status",
    tier=0,
    description="Returns real-time status, average latencies, and active task queues across all swarm subagents (Tier 0 read-only).",
    args_schema=QueryLocalSwarmStatusArgs,
    preview_fn=preview_query_local_swarm_status,
    can_remember_per_folder=False,
)
def handle_query_local_swarm_status() -> Dict[str, Any]:
    return swarm_coordinator.query_status()


# ==========================================
# 3. Terminate Local Swarm Worker (Tier 1)
# ==========================================

class TerminateLocalSwarmWorkerArgs(BaseModel):
    agent_name: Optional[str] = Field(
        None, description="Optional target subagent to terminate ('coder', 'research', 'executive'). If omitted, terminates all workers."
    )


def preview_terminate_local_swarm_worker(args: Dict[str, Any]) -> str:
    agent = args.get("agent_name") or "ALL WORKERS"
    return f"Terminate local swarm workstream and halt subagent: '{agent}'"


@registry.register(
    name="terminate_local_swarm_worker",
    tier=1,
    description="Halts a specific subagent worker or terminates all active swarm workers (Tier 1 state mutation).",
    args_schema=TerminateLocalSwarmWorkerArgs,
    preview_fn=preview_terminate_local_swarm_worker,
    can_remember_per_folder=False,
)
def handle_terminate_local_swarm_worker(
    agent_name: Optional[str] = None,
) -> Dict[str, Any]:
    if agent_name:
        return swarm_coordinator.terminate_worker(agent_name)
    return swarm_coordinator.terminate_all()


# ==========================================
# 4. Synthesize Local Swarm Results (Tier 0)
# ==========================================

class SynthesizeLocalSwarmResultsArgs(BaseModel):
    task_ids: List[str] = Field(
        ..., description="List of completed task IDs to synthesize into a unified report."
    )


def preview_synthesize_local_swarm_results(args: Dict[str, Any]) -> str:
    tids = args.get("task_ids", [])
    return f"Synthesize results from {len(tids)} completed swarm tasks into a unified report"


@registry.register(
    name="synthesize_local_swarm_results",
    tier=0,
    description="Combines outputs from multiple completed subagent tasks into a consolidated multi-agent report (Tier 0 read-only).",
    args_schema=SynthesizeLocalSwarmResultsArgs,
    preview_fn=preview_synthesize_local_swarm_results,
    can_remember_per_folder=False,
)
def handle_synthesize_local_swarm_results(
    task_ids: List[str],
) -> Dict[str, Any]:
    report = swarm_coordinator.synthesize_results(task_ids=task_ids)
    return {
        "report_markdown": report,
        "task_count": len(task_ids),
    }
