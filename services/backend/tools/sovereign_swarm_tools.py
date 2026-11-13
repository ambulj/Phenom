"""
Phenom 5-Agent Sovereign Tactical Swarm Tool Suite
Registers:
1. dispatch_sovereign_swarm (Tier 1) - Dispatches 5 autonomous agents in parallel to execute cross-platform missions
2. get_swarm_status (Tier 0) - Retrieves live status of all 5 agents, hybrid routing, and active platform
3. post_swarm_message (Tier 0) - Posts an inter-agent task brief or status report to the shared board
4. get_swarm_message_board (Tier 0) - Retrieves recent chronological swarm board messages
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.orchestrator.sovereign_swarm import sovereign_swarm


# 1. Dispatch Sovereign Swarm
class DispatchSwarmArgs(BaseModel):
    mission_name: str = Field(..., description="Name or objective of the multi-agent tactical mission")
    target_scope: Optional[str] = Field(default="127.0.0.1", description="Target IP or local subnet scope")


def dispatch_swarm_preview(args: Dict[str, Any]) -> str:
    return f"Dispatch 5-Agent Sovereign Swarm for mission '{args.get('mission_name')}' across scope {args.get('target_scope', '127.0.0.1')}"


@registry.register(
    name="dispatch_sovereign_swarm",
    tier=1,
    description="Dispatches all 5 autonomous swarm agents (Vanguard, Sentinel, Specter, Synapse, Prime) simultaneously across Windows 11 / Kali Linux.",
    args_schema=DispatchSwarmArgs,
    preview_fn=dispatch_swarm_preview,
    can_remember_per_folder=False
)
def dispatch_sovereign_swarm(mission_name: str, target_scope: str = "127.0.0.1") -> Dict[str, Any]:
    return sovereign_swarm.dispatch_swarm_mission(mission_name=mission_name, target_scope=target_scope)


# 2. Get Swarm Status
class SwarmStatusArgs(BaseModel):
    pass


@registry.register(
    name="get_swarm_status",
    tier=0,
    description="Queries the real-time status, active platform, roster capabilities, and hybrid local/cloud routing of the 5-agent sovereign swarm.",
    args_schema=SwarmStatusArgs,
    preview_fn=lambda a: "Inspect 5-agent sovereign tactical swarm status and hybrid routing",
    can_remember_per_folder=False
)
def get_swarm_status() -> Dict[str, Any]:
    return sovereign_swarm.get_swarm_status()


# 3. Post Swarm Message
class PostSwarmMessageArgs(BaseModel):
    sender: str = Field(..., description="Name of the sending agent (e.g. 'Prime', 'Vanguard')")
    recipient: str = Field(..., description="Recipient agent name or 'ALL'")
    message: str = Field(..., description="Message content or task assignment brief")
    message_type: Optional[str] = Field(default="TASK_BRIEF", description="Type of message ('TASK_BRIEF', 'STATUS_REPORT')")


@registry.register(
    name="post_swarm_message",
    tier=0,
    description="Posts an inter-agent task brief, telemetry finding, or status report to the shared swarm message board.",
    args_schema=PostSwarmMessageArgs,
    preview_fn=lambda a: f"Post swarm message from {a.get('sender')} to {a.get('recipient')}",
    can_remember_per_folder=False
)
def post_swarm_message(sender: str, recipient: str, message: str, message_type: str = "TASK_BRIEF") -> Dict[str, Any]:
    return sovereign_swarm.post_message(sender=sender, recipient=recipient, message=message, message_type=message_type)


# 4. Get Swarm Message Board
class GetSwarmBoardArgs(BaseModel):
    limit: Optional[int] = Field(default=50, description="Maximum number of recent messages to retrieve")


@registry.register(
    name="get_swarm_message_board",
    tier=0,
    description="Retrieves the chronological audit log of all inter-agent messages and task briefs from the shared swarm board.",
    args_schema=GetSwarmBoardArgs,
    preview_fn=lambda a: f"Retrieve recent swarm message board entries (limit {a.get('limit', 50)})",
    can_remember_per_folder=False
)
def get_swarm_message_board(limit: int = 50) -> List[Dict[str, Any]]:
    return sovereign_swarm.get_message_board(limit=limit)
