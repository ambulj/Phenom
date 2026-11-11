"""Safety-Wrapped Swarm Watchdog & Arbiter Tools.

Registers tools with ToolRegistry for inspecting worker node health,
arbitrating Byzantine faults with quarantine, and reassigning orphaned contracts (Phase 27-04 BYZ-01 / ARB-02).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.swarm.byzantine_watchdog import byzantine_watchdog
from services.backend.swarm.failover_arbiter import failover_arbiter


# ==========================================
# 1. Inspect Swarm Health (Tier 0)
# ==========================================

class InspectSwarmHealthArgs(BaseModel):
    pass


def inspect_swarm_health_preview(args: Dict[str, Any]) -> str:
    return "Inspect swarm worker node health metrics, heartbeat latencies, and anomaly scores."


@registry.register(
    name="inspect_swarm_health",
    tier=0,
    description="Inspects real-time heartbeat latencies, error counts, and anomaly scores across all swarm workers.",
    args_schema=InspectSwarmHealthArgs,
    preview_fn=inspect_swarm_health_preview,
    can_remember_per_folder=False,
)
def handle_inspect_swarm_health() -> Dict[str, Any]:
    records = byzantine_watchdog.inspect_health()
    return {
        "worker_count": len(records),
        "health_reports": [r.model_dump() for r in records],
    }


# ==========================================
# 2. Arbitrate Byzantine Fault (Tier 1)
# ==========================================

class ArbitrateByzantineFaultArgs(BaseModel):
    agent_id: str = Field(..., description="ID of the anomalous or rogue agent to quarantine")
    reason: str = Field("Byzantine fault detected", description="Reason for triggering node quarantine")


def arbitrate_byzantine_fault_preview(args: Dict[str, Any]) -> str:
    aid = args.get("agent_id", "unknown_agent")
    return f"Quarantine worker node '{aid}' and trigger isolation failover."


@registry.register(
    name="arbitrate_byzantine_fault",
    tier=1,
    description="Quarantines a faulty or erratic worker node, halts it via Guardian isolation, and reclaims assigned tasks.",
    args_schema=ArbitrateByzantineFaultArgs,
    preview_fn=arbitrate_byzantine_fault_preview,
    can_remember_per_folder=False,
)
def handle_arbitrate_byzantine_fault(
    agent_id: str,
    reason: str = "Byzantine fault detected",
) -> Dict[str, Any]:
    action = failover_arbiter.quarantine_worker(agent_id=agent_id, reason=reason)
    return {
        "status": "QUARANTINED",
        "action": action.model_dump(),
    }


# ==========================================
# 3. Reassign Orphaned Tasks (Tier 1)
# ==========================================

class ReassignOrphanedTasksArgs(BaseModel):
    task_ids: Optional[List[str]] = Field(None, description="Optional specific orphaned task IDs to re-auction")


def reassign_orphaned_tasks_preview(args: Dict[str, Any]) -> str:
    tids = args.get("task_ids")
    suffix = f" ({len(tids)} tasks)" if tids else " (all open/orphaned)"
    return f"Reassign and re-auction orphaned swarm task contracts{suffix}."


@registry.register(
    name="reassign_orphaned_tasks",
    tier=1,
    description="Re-auctions open or orphaned task contracts to remaining healthy worker nodes.",
    args_schema=ReassignOrphanedTasksArgs,
    preview_fn=reassign_orphaned_tasks_preview,
    can_remember_per_folder=False,
)
def handle_reassign_orphaned_tasks(
    task_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    awards = failover_arbiter.reassign_orphaned_tasks(orphaned_task_ids=task_ids)
    return {
        "status": "REASSIGNMENT_COMPLETE",
        "reassigned_count": len(awards),
        "awards": awards,
    }
