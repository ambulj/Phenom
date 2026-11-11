"""Safety-Wrapped Task Auction Tools.

Registers tools with ToolRegistry for conducting task auctions,
evaluating worker capability bids, and querying swarm task DAGs (Phase 27-02 AUC-01 / BID-02).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.swarm.task_auction_engine import (
    task_auction_engine,
    TaskContract,
)
from services.backend.swarm.capability_bidder import (
    capability_bidder,
    WorkerBid,
)
from services.backend.swarm.agent_mesh_coordinator import agent_mesh_coordinator


# ==========================================
# 1. Auction Task to Swarm (Tier 1)
# ==========================================

class AuctionTaskToSwarmArgs(BaseModel):
    task_id: str = Field(..., description="ID of the task contract to auction")


def auction_task_to_swarm_preview(args: Dict[str, Any]) -> str:
    tid = args.get("task_id", "unknown_task")
    return f"Auction task contract '{tid}' to swarm specialist workers."


@registry.register(
    name="auction_task_to_swarm",
    tier=1,
    description="Conducts a capability-based bidding auction for a task contract and awards it to the optimal subagent.",
    args_schema=AuctionTaskToSwarmArgs,
    preview_fn=auction_task_to_swarm_preview,
    can_remember_per_folder=False,
)
def handle_auction_task_to_swarm(task_id: str) -> Dict[str, Any]:
    result = task_auction_engine.conduct_auction(task_id=task_id)
    return {
        "status": "AUCTION_COMPLETE",
        "result": result,
    }


# ==========================================
# 2. Evaluate Worker Bids (Tier 0)
# ==========================================

class EvaluateWorkerBidsArgs(BaseModel):
    task_id: str = Field(..., description="ID of the task contract to evaluate bids for")


def evaluate_worker_bids_preview(args: Dict[str, Any]) -> str:
    tid = args.get("task_id", "unknown_task")
    return f"Evaluate specialist worker capability bids for task contract '{tid}'."


@registry.register(
    name="evaluate_worker_bids",
    tier=0,
    description="Calculates suitability scores and latency estimates for all active workers for a task contract.",
    args_schema=EvaluateWorkerBidsArgs,
    preview_fn=evaluate_worker_bids_preview,
    can_remember_per_folder=False,
)
def handle_evaluate_worker_bids(task_id: str) -> Dict[str, Any]:
    contracts = {c.task_id: c for c in task_auction_engine.get_dag()}
    if task_id not in contracts:
        raise ValueError(f"Task contract '{task_id}' not found.")

    contract = contracts[task_id]
    agents = agent_mesh_coordinator.list_agents()
    bids: List[WorkerBid] = []
    for agent in agents:
        bid = capability_bidder.calculate_bid(agent, task_id, contract.required_skills)
        if bid:
            bids.append(bid)

    sorted_bids = sorted(bids, key=lambda b: (b.suitability_score, -b.estimated_latency_ms), reverse=True)
    return {
        "task_id": task_id,
        "required_skills": contract.required_skills,
        "bid_count": len(sorted_bids),
        "bids": [b.model_dump() for b in sorted_bids],
    }


# ==========================================
# 3. Get Swarm Task DAG (Tier 0)
# ==========================================

class GetSwarmTaskDAGArgs(BaseModel):
    pass


def get_swarm_task_dag_preview(args: Dict[str, Any]) -> str:
    return "Retrieve swarm task DAG contracts and assignment statuses."


@registry.register(
    name="get_swarm_task_dag",
    tier=0,
    description="Retrieves the full task DAG structure, prerequisite links, and execution states.",
    args_schema=GetSwarmTaskDAGArgs,
    preview_fn=get_swarm_task_dag_preview,
    can_remember_per_folder=False,
)
def handle_get_swarm_task_dag() -> Dict[str, Any]:
    contracts = task_auction_engine.get_dag()
    return {
        "contract_count": len(contracts),
        "tasks": [c.model_dump() for c in contracts],
    }
