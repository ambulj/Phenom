"""Capability Bidder for Phenom Swarm Mesh (Milestone 27 Phase 2).

Computes worker suitability scores, hardware capacity bids, and auction rankings
based on specialist skill vectors and active queue depth (BID-02.1).
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.swarm.agent_mesh_coordinator import (
    MeshSubagent,
    AgentMeshCoordinator,
    agent_mesh_coordinator,
)

logger = logging.getLogger("phenom.swarm.capability_bidder")


class WorkerBid(BaseModel):
    bid_id: str = Field(default_factory=lambda: f"bid_{uuid.uuid4().hex[:8]}")
    agent_id: str
    specialization: str
    task_id: str
    suitability_score: float  # 0.0 - 1.0
    estimated_latency_ms: float
    confidence: float
    timestamp: float = Field(default_factory=time.time)


class CapabilityBidder:
    """Calculates capability match and formulates bids for specialist agents."""

    @staticmethod
    def calculate_bid(agent: MeshSubagent, task_id: str, required_skills: Dict[str, float]) -> Optional[WorkerBid]:
        """Calculates a bid for a given task based on skill vector dot product and mailbox load."""
        if agent.status == "HALTED":
            return None

        skills = agent.profile.skill_vector
        total_weight = 0.0
        match_score = 0.0

        for req_skill, min_weight in required_skills.items():
            total_weight += min_weight
            agent_weight = skills.get(req_skill, 0.1)
            # Match is ratio of agent capability to requirement
            match_score += min(1.0, agent_weight / max(0.01, min_weight)) * min_weight

        if total_weight > 0:
            raw_suitability = match_score / total_weight
        else:
            raw_suitability = 0.5

        # Penalize for queue depth (each pending message adds latency and reduces suitability)
        load_penalty = min(0.3, len(agent.mailbox) * 0.05)
        suitability = max(0.05, min(1.0, round(raw_suitability - load_penalty, 3)))

        # Estimate execution latency based on suitability and load
        base_latency = 15.0 + (1.0 - suitability) * 40.0
        estimated_latency = round(base_latency + len(agent.mailbox) * 10.0, 1)

        return WorkerBid(
            agent_id=agent.agent_id,
            specialization=agent.specialization,
            task_id=task_id,
            suitability_score=suitability,
            estimated_latency_ms=estimated_latency,
            confidence=round(suitability * 0.95, 2),
        )


# Global singleton instance
capability_bidder = CapabilityBidder()
