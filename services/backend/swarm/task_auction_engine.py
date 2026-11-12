"""Task Auction Engine for Phenom Swarm Mesh (Milestone 27 Phase 2).

Deconstructs directives into dependency DAG task contracts, solicits worker capability bids,
and awards subtasks to the optimal specialist subagent (AUC-01.1, AUC-01.2).
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
from services.backend.swarm.capability_bidder import (
    capability_bidder,
    WorkerBid,
)

logger = logging.getLogger("phenom.swarm.auction_engine")


class TaskContract(BaseModel):
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    title: str
    required_skills: Dict[str, float] = Field(default_factory=dict)
    prerequisites: List[str] = Field(default_factory=list)
    status: str = "OPEN"  # OPEN, AUCTIONING, AWARDED, COMPLETED
    assigned_agent_id: Optional[str] = None
    winning_bid: Optional[WorkerBid] = None
    all_bids: List[WorkerBid] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)


class TaskAuctionEngine:
    """Manages the lifecycle of task contracts, DAG dependency checking, and auction awards."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self, coordinator: Optional[AgentMeshCoordinator] = None) -> None:
        self._coordinator = coordinator or agent_mesh_coordinator
        self._contracts: Dict[str, TaskContract] = {}
        self._init_default_contracts()

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Task auction engine halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: task auction involving payments is strictly prohibited. Found: {text}"
            )

    def _init_default_contracts(self) -> None:
        """Seed initial pipeline DAG for verification."""
        t1 = self.create_contract(
            title="Consolidate Project Knowledge Context",
            required_skills={"memory_query": 0.8, "synthesis": 0.7},
            prerequisites=[],
            custom_id="task_001",
        )
        t2 = self.create_contract(
            title="Synthesize Core Feature Implementation",
            required_skills={"code_synthesis": 0.85, "ast_manipulation": 0.8},
            prerequisites=[t1.task_id],
            custom_id="task_002",
        )
        self.create_contract(
            title="Verify Guardian SLA & Test Coverage",
            required_skills={"testing": 0.9, "sla_benchmark": 0.85},
            prerequisites=[t2.task_id],
            custom_id="task_003",
        )

    def create_contract(
        self,
        title: str,
        required_skills: Dict[str, float],
        prerequisites: Optional[List[str]] = None,
        custom_id: Optional[str] = None,
    ) -> TaskContract:
        """Creates a new task contract in the DAG."""
        self._check_guardian()
        self._validate_rule_8(title)
        for skill in required_skills.keys():
            self._validate_rule_8(skill)

        cid = custom_id or f"task_{uuid.uuid4().hex[:8]}"
        contract = TaskContract(
            task_id=cid,
            title=title,
            required_skills=required_skills,
            prerequisites=prerequisites or [],
            status="OPEN",
        )
        self._contracts[cid] = contract
        return contract

    def decompose_objective(self, objective: str) -> List[TaskContract]:
        """Deconstructs high-level user objective into a 3-stage dependency DAG."""
        self._check_guardian()
        self._validate_rule_8(objective)

        c1 = self.create_contract(
            title=f"Research & Audit Requirements for '{objective[:30]}'",
            required_skills={"security_audit": 0.8, "memory_query": 0.6},
            prerequisites=[],
        )
        c2 = self.create_contract(
            title=f"Synthesize Architecture & Logic for '{objective[:30]}'",
            required_skills={"code_synthesis": 0.9, "ast_manipulation": 0.85},
            prerequisites=[c1.task_id],
        )
        c3 = self.create_contract(
            title=f"Execute Chaos & Concurrency Verification for '{objective[:30]}'",
            required_skills={"testing": 0.92, "chaos_battery": 0.85},
            prerequisites=[c2.task_id],
        )
        return [c1, c2, c3]

    def conduct_auction(self, task_id: str) -> Dict[str, Any]:
        """Solicits bids from all registered agents and awards contract to the highest bidder."""
        self._check_guardian()
        if task_id not in self._contracts:
            raise ValueError(f"Task contract '{task_id}' not found.")

        contract = self._contracts[task_id]
        agents = self._coordinator.list_agents()

        bids: List[WorkerBid] = []
        for agent in agents:
            bid = capability_bidder.calculate_bid(agent, task_id, contract.required_skills)
            if bid:
                bids.append(bid)

        if not bids:
            raise RuntimeError(f"No available agents capable of bidding on task '{task_id}'.")

        # Rank bids primarily by suitability score (desc), secondarily by estimated latency (asc)
        sorted_bids = sorted(bids, key=lambda b: (b.suitability_score, -b.estimated_latency_ms), reverse=True)
        winner = sorted_bids[0]

        contract.all_bids = sorted_bids
        contract.winning_bid = winner
        contract.assigned_agent_id = winner.agent_id
        contract.status = "AWARDED"

        # Notify the assigned agent via mesh coordinator
        self._coordinator.send_message(
            sender_id="system_auction_engine",
            recipient_id=winner.agent_id,
            message_type="DIRECTIVE",
            payload={"task_id": task_id, "title": contract.title, "action": "EXECUTE_CONTRACT"},
        )

        return {
            "task_id": task_id,
            "title": contract.title,
            "status": "AWARDED",
            "winning_agent_id": winner.agent_id,
            "winning_specialization": winner.specialization,
            "suitability_score": winner.suitability_score,
            "estimated_latency_ms": winner.estimated_latency_ms,
            "total_bids_received": len(bids),
        }

    def get_dag(self) -> List[TaskContract]:
        """Returns all task contracts in the DAG."""
        self._check_guardian()
        return list(self._contracts.values())

    def mark_completed(self, task_id: str) -> bool:
        """Mark a contract as completed."""
        self._check_guardian()
        if task_id in self._contracts:
            self._contracts[task_id].status = "COMPLETED"
            return True
        return False


# Global singleton instance
task_auction_engine = TaskAuctionEngine()
