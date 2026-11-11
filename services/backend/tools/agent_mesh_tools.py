"""Safety-Wrapped Agent Mesh Tools.

Registers tools with ToolRegistry for spawning specialist subagents,
routing in-memory inter-agent messages, and querying swarm mesh topology (Phase 27-01 MSH-01 / AGT-04).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.swarm.agent_mesh_coordinator import (
    agent_mesh_coordinator,
    MeshSubagent,
    MeshMessage,
)


# ==========================================
# 1. Spawn Mesh Subagent (Tier 1)
# ==========================================

class SpawnMeshSubagentArgs(BaseModel):
    specialization: str = Field(..., description="Specialist persona: CodeArchitect, SecurityAuditor, TestOrchestrator, KnowledgeResearcher")
    custom_id: Optional[str] = Field(None, description="Optional custom identifier for the subagent")


def spawn_mesh_subagent_preview(args: Dict[str, Any]) -> str:
    spec = args.get("specialization", "GenericSpecialist")
    cid = args.get("custom_id")
    suffix = f" (id: {cid})" if cid else ""
    return f"Spawn specialist subagent [{spec}]{suffix} in local swarm mesh."


@registry.register(
    name="spawn_mesh_subagent",
    tier=1,
    description="Spawns an isolated specialist subagent node in the local swarm mesh network.",
    args_schema=SpawnMeshSubagentArgs,
    preview_fn=spawn_mesh_subagent_preview,
    can_remember_per_folder=False,
)
def handle_spawn_mesh_subagent(
    specialization: str,
    custom_id: Optional[str] = None,
) -> Dict[str, Any]:
    agent = agent_mesh_coordinator.spawn_agent(specialization=specialization, custom_id=custom_id)
    return {
        "status": "SPAWNED",
        "agent": agent.model_dump(),
    }


# ==========================================
# 2. Send Agent Mesh Message (Tier 0)
# ==========================================

class SendAgentMeshMessageArgs(BaseModel):
    sender_id: str = Field(..., description="ID of the sending agent")
    recipient_id: str = Field(..., description="ID of the receiving agent or 'BROADCAST'")
    message_type: str = Field(..., description="Message classification: QUERY, DIRECTIVE, STATE_UPDATE, BID, HEARTBEAT")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Typed payload dictionary")


def send_agent_mesh_message_preview(args: Dict[str, Any]) -> str:
    mtype = args.get("message_type", "MESSAGE")
    snd = args.get("sender_id", "unknown_sender")
    rec = args.get("recipient_id", "unknown_recipient")
    return f"Send swarm message ({mtype}) from '{snd}' to '{rec}'."


@registry.register(
    name="send_agent_mesh_message",
    tier=0,
    description="Routes an in-memory asynchronous message between mesh subagents with zero cloud egress.",
    args_schema=SendAgentMeshMessageArgs,
    preview_fn=send_agent_mesh_message_preview,
    can_remember_per_folder=False,
)
def handle_send_agent_mesh_message(
    sender_id: str,
    recipient_id: str,
    message_type: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    msg = agent_mesh_coordinator.send_message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        message_type=message_type,
        payload=payload or {},
    )
    return {
        "status": "DELIVERED",
        "message": msg.model_dump(),
    }


# ==========================================
# 3. Get Agent Mesh Topology (Tier 0)
# ==========================================

class GetAgentMeshTopologyArgs(BaseModel):
    pass


def get_agent_mesh_topology_preview(args: Dict[str, Any]) -> str:
    return "Retrieve local swarm agent mesh topology and message throughput."


@registry.register(
    name="get_agent_mesh_topology",
    tier=0,
    description="Retrieves the current local swarm mesh topology, active agent states, and message counters.",
    args_schema=GetAgentMeshTopologyArgs,
    preview_fn=get_agent_mesh_topology_preview,
    can_remember_per_folder=False,
)
def handle_get_agent_mesh_topology() -> Dict[str, Any]:
    return agent_mesh_coordinator.get_topology()
