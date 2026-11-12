"""Failover Arbiter for Phenom Swarm Mesh (Milestone 27 Phase 4).

Quarantines rogue or failing subagents via Guardian halt, rescues orphaned task contracts,
and reassigns work to healthy standby agents (ARB-02.1).
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.swarm.agent_mesh_coordinator import (
    agent_mesh_coordinator,
    AgentMeshCoordinator,
    Rule8ViolationError,
)
from services.backend.swarm.task_auction_engine import (
    task_auction_engine,
    TaskAuctionEngine,
)

logger = logging.getLogger("phenom.swarm.failover_arbiter")


class FailoverActionRecord(BaseModel):
    action_id: str = Field(default_factory=lambda: f"failover_{uuid.uuid4().hex[:8]}")
    faulty_agent_id: str
    reason: str
    orphaned_task_ids: List[str] = Field(default_factory=list)
    reassigned_awards: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class FailoverArbiter:
    """Manages worker quarantine, task reclamation, and failover re-auctioning."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        coordinator: Optional[AgentMeshCoordinator] = None,
        auction_engine: Optional[TaskAuctionEngine] = None,
    ) -> None:
        self._coordinator = coordinator or agent_mesh_coordinator
        self._auction_engine = auction_engine or task_auction_engine
        self._action_history: List[FailoverActionRecord] = []

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Failover arbiter halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: failover operation involving payments is strictly prohibited. Found: {text}"
            )

    def quarantine_worker(self, agent_id: str, reason: str = "Byzantine fault detected") -> FailoverActionRecord:
        """Quarantine a faulty worker: halt node, release assigned tasks."""
        self._check_guardian()
        self._validate_rule_8(agent_id)
        self._validate_rule_8(reason)

        # 1. Halt agent in mesh
        self._coordinator.halt_agent(agent_id)

        # 2. Identify orphaned tasks assigned to this agent
        orphaned: List[str] = []
        for contract in self._auction_engine.get_dag():
            if contract.assigned_agent_id == agent_id and contract.status == "AWARDED":
                contract.status = "OPEN"
                contract.assigned_agent_id = None
                contract.winning_bid = None
                orphaned.append(contract.task_id)

        record = FailoverActionRecord(
            faulty_agent_id=agent_id,
            reason=reason,
            orphaned_task_ids=orphaned,
        )
        self._action_history.append(record)
        return record

    def reassign_orphaned_tasks(self, orphaned_task_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Re-auctions open/orphaned tasks to remaining healthy workers."""
        self._check_guardian()
        tasks_to_reassign = orphaned_task_ids
        if not tasks_to_reassign:
            tasks_to_reassign = [
                c.task_id for c in self._auction_engine.get_dag() if c.status == "OPEN"
            ]

        awards: List[Dict[str, Any]] = []
        for tid in tasks_to_reassign:
            try:
                res = self._auction_engine.conduct_auction(tid)
                awards.append(res)
            except Exception as e:
                logger.warning(f"Could not reassign task {tid}: {e}")

        return awards

    def get_history(self) -> List[FailoverActionRecord]:
        """Returns failover audit history."""
        self._check_guardian()
        return list(self._action_history)


# Global singleton instance
failover_arbiter = FailoverArbiter()
