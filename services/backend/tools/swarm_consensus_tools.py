"""Safety-Wrapped Swarm Consensus CRDT Tools.

Registers tools with ToolRegistry for proposing CRDT state deltas,
reconciling distributed state registers, and inspecting vector clocks (Phase 27-03 CRDT-01 / CON-04).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.swarm.crdt_consensus_engine import (
    crdt_state_register,
    CRDTDelta,
)
from services.backend.swarm.state_reconciler import state_reconciler


# ==========================================
# 1. Propose State CRDT Delta (Tier 1)
# ==========================================

class ProposeStateCRDTDeltaArgs(BaseModel):
    agent_id: str = Field(..., description="ID of the proposing specialist agent")
    key: str = Field(..., description="State key to mutate")
    value: str = Field(..., description="New value for the state key")


def propose_state_crdt_delta_preview(args: Dict[str, Any]) -> str:
    aid = args.get("agent_id", "unknown_agent")
    k = args.get("key", "unknown_key")
    v = args.get("value", "")
    return f"Propose CRDT state delta from '{aid}': [{k}] -> '{v}'."


@registry.register(
    name="propose_state_crdt_delta",
    tier=1,
    description="Proposes a state mutation stamped with the agent's vector clock using LWW conflict resolution.",
    args_schema=ProposeStateCRDTDeltaArgs,
    preview_fn=propose_state_crdt_delta_preview,
    can_remember_per_folder=False,
)
def handle_propose_state_crdt_delta(
    agent_id: str,
    key: str,
    value: str,
) -> Dict[str, Any]:
    delta = crdt_state_register.apply_delta(agent_id=agent_id, key=key, value=value)
    return {
        "status": "APPLIED",
        "delta": delta.model_dump(),
        "converged_entry": crdt_state_register.get_converged_state().get(key),
    }


# ==========================================
# 2. Reconcile Swarm Consensus (Tier 0)
# ==========================================

class ReconcileSwarmConsensusArgs(BaseModel):
    pass


def reconcile_swarm_consensus_preview(args: Dict[str, Any]) -> str:
    return "Reconcile swarm consensus state register and causality clocks."


@registry.register(
    name="reconcile_swarm_consensus",
    tier=0,
    description="Calculates and returns the deterministic converged distributed state across all keys.",
    args_schema=ReconcileSwarmConsensusArgs,
    preview_fn=reconcile_swarm_consensus_preview,
    can_remember_per_folder=False,
)
def handle_reconcile_swarm_consensus() -> Dict[str, Any]:
    state = crdt_state_register.get_converged_state()
    clocks = crdt_state_register.get_vector_clocks()
    return {
        "status": "CONVERGED",
        "key_count": len(state),
        "state": state,
        "vector_clocks": clocks,
    }


# ==========================================
# 3. Get Lamport Vector Clocks (Tier 0)
# ==========================================

class GetLamportVectorClocksArgs(BaseModel):
    pass


def get_lamport_vector_clocks_preview(args: Dict[str, Any]) -> str:
    return "Retrieve current Lamport vector clocks across all swarm agents."


@registry.register(
    name="get_lamport_vector_clocks",
    tier=0,
    description="Retrieves the current vector clock causality timestamps across all swarm worker nodes.",
    args_schema=GetLamportVectorClocksArgs,
    preview_fn=get_lamport_vector_clocks_preview,
    can_remember_per_folder=False,
)
def handle_get_lamport_vector_clocks() -> Dict[str, Any]:
    return {
        "clocks": crdt_state_register.get_vector_clocks(),
        "total_deltas": len(crdt_state_register.get_history()),
    }
