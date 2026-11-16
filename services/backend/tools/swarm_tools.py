"""Swarm Tools Registration (Phase 48-01, SWARM-01, SWARM-02).

Registers multi-agent task auction dispatching, swarm roster inspection,
and competitive agent bid queries into Phenom's Safety ToolRegistry.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.schemas.swarm_auction import AgentRole
from services.backend.swarm.agent_roles import AgentRoleRegistry
from services.backend.swarm.auction_engine import TaskAuctionEngine
from services.backend.swarm.scheduler import SwarmScheduler

# Singleton instances for tools
auction_engine = TaskAuctionEngine()
swarm_scheduler = SwarmScheduler()


# ============================================================================
# 1. dispatch_swarm_auction (Tier 1)
# ============================================================================

class DispatchSwarmAuctionArgs(BaseModel):
    tasks: List[Dict[str, Any]] = Field(
        ...,
        description="List of task/node dictionaries containing node_id, tool_name, title, and description",
    )


def dispatch_swarm_auction_preview(args: Dict[str, Any]) -> str:
    tasks = args.get("tasks", [])
    count = len(tasks)
    return f"Dispatch {count} DAG task(s) to Multi-Agent Auction Engine for role fitness bidding."


@registry.register(
    name="dispatch_swarm_auction",
    tier=1,
    description="Conducts competitive auction on DAG tasks across Architect, Coder, Auditor, and Scout roles.",
    args_schema=DispatchSwarmAuctionArgs,
    preview_fn=dispatch_swarm_auction_preview,
    can_remember_per_folder=False,
)
def handle_dispatch_swarm_auction(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    auction_results = auction_engine.conduct_auction_for_dag(tasks)
    serialized = {
        node_id: res.model_dump()
        for node_id, res in auction_results.items()
    }
    return {
        "auction_count": len(serialized),
        "assignments": {
            node_id: res["winning_role"] for node_id, res in serialized.items()
        },
        "details": serialized,
    }


# ============================================================================
# 2. get_swarm_roster_status (Tier 0 - Read Only)
# ============================================================================

class GetSwarmRosterStatusArgs(BaseModel):
    pass


def get_swarm_roster_status_preview(args: Dict[str, Any]) -> str:
    return "Query active swarm agent roles, capability profiles, workloads, and GPU VRAM metrics."


@registry.register(
    name="get_swarm_roster_status",
    tier=0,
    description="Returns current swarm roster profiles, active task workloads, and real-time VRAM telemetry.",
    args_schema=GetSwarmRosterStatusArgs,
    preview_fn=get_swarm_roster_status_preview,
)
def handle_get_swarm_roster_status() -> Dict[str, Any]:
    profiles = [p.model_dump() for p in AgentRoleRegistry.list_profiles()]
    vram = swarm_scheduler.get_vram_metrics().model_dump()
    workloads = {
        role.value: auction_engine.active_workloads.get(role, 0)
        for role in AgentRoleRegistry.get_all_roles()
    }
    return {
        "agent_count": len(profiles),
        "profiles": profiles,
        "workloads": workloads,
        "vram_metrics": vram,
    }


# ============================================================================
# 3. query_agent_bids (Tier 0 - Read Only)
# ============================================================================

class QueryAgentBidsArgs(BaseModel):
    node_id: str = Field(..., description="Unique ID of the task or DAG node")
    tool_name: str = Field(..., description="Target tool name to evaluate")
    title: Optional[str] = Field(default="", description="Optional title of the task")
    description: Optional[str] = Field(default="", description="Optional description of the task")


def query_agent_bids_preview(args: Dict[str, Any]) -> str:
    node_id = args.get("node_id", "")
    tool = args.get("tool_name", "")
    return f"Simulate multi-agent bidding for node '{node_id}' with tool '{tool}'."


@registry.register(
    name="query_agent_bids",
    tier=0,
    description="Calculates and returns individual bids from all 4 agent roles for a specific task.",
    args_schema=QueryAgentBidsArgs,
    preview_fn=query_agent_bids_preview,
)
def handle_query_agent_bids(
    node_id: str,
    tool_name: str,
    title: Optional[str] = "",
    description: Optional[str] = "",
) -> Dict[str, Any]:
    bids = auction_engine.generate_bids_for_node(
        node_id=node_id,
        tool_name=tool_name,
        node_title=title or "",
        node_desc=description or "",
    )
    winner = auction_engine.select_winning_bid(node_id, bids)
    return {
        "node_id": node_id,
        "tool_name": tool_name,
        "winning_role": winner.winning_role.value,
        "bids": [b.model_dump() for b in bids],
    }
