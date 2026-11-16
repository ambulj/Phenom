"""Task Auction Engine for Phenom Multi-Agent Swarm.

Phase 48-01: SWARM-02.
Calculates role fitness scores and token bids for decomposed DAG nodes,
conducting dynamic auctions and assigning execution responsibilities.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Union

from services.backend.schemas.swarm_auction import (
    AgentRole,
    AuctionResult,
    TaskBid,
)
from services.backend.swarm.agent_roles import AgentRoleRegistry

logger = logging.getLogger("phenom.swarm.auction_engine")


class TaskAuctionEngine:
    """Evaluates task fitness across roles, generates bids, and selects winners."""

    WEIGHT_AFFINITY: float = 0.55
    WEIGHT_KEYWORD: float = 0.35
    PENALTY_WORKLOAD: float = 0.10
    MIN_CONFIDENCE_THRESHOLD: float = 0.25

    def __init__(self) -> None:
        self.active_workloads: Dict[AgentRole, int] = {
            role: 0 for role in AgentRoleRegistry.get_all_roles()
        }

    def update_workload(self, role: AgentRole, delta: int) -> None:
        """Update current active task count for an agent role."""
        current = self.active_workloads.get(role, 0)
        self.active_workloads[role] = max(0, current + delta)

    def compute_fitness(
        self,
        role: AgentRole,
        tool_name: str,
        node_title: str = "",
        node_desc: str = "",
        current_load: Optional[int] = None,
    ) -> float:
        """Calculate normalized fitness score (0.0 to 1.0) for an agent role."""
        profile = AgentRoleRegistry.get_profile(role)
        load = current_load if current_load is not None else self.active_workloads.get(role, 0)

        # 1. Tool Affinity Score (0.0 - 1.0)
        affinity_score = AgentRoleRegistry.get_tool_affinity(role, tool_name)

        # 2. Keyword Semantic Matching Score (0.0 - 1.0)
        combined_text = f"{node_title} {node_desc}".lower()
        matched_tags = sum(1 for tag in profile.capability_tags if re.search(rf"\b{re.escape(tag)}\b", combined_text))
        keyword_score = min(1.0, (matched_tags / max(1, len(profile.capability_tags))) * 2.0)

        # 3. Workload Penalty (diminishes fitness for overloaded agents)
        load_penalty = min(0.3, load * 0.05)

        # Composite weighted score
        raw_score = (
            (self.WEIGHT_AFFINITY * affinity_score)
            + (self.WEIGHT_KEYWORD * keyword_score)
            - (self.PENALTY_WORKLOAD * load_penalty)
        )

        return round(max(0.0, min(1.0, raw_score)), 3)

    def generate_bids_for_node(
        self,
        node_id: str,
        tool_name: str,
        node_title: str = "",
        node_desc: str = "",
    ) -> List[TaskBid]:
        """Generate structured bids from all active agent roles."""
        bids: List[TaskBid] = []

        for role in AgentRoleRegistry.get_all_roles():
            fitness = self.compute_fitness(role, tool_name, node_title, node_desc)
            profile = AgentRoleRegistry.get_profile(role)

            # Heuristic token & time estimates based on role and fitness
            est_tokens = max(100, int(profile.max_tokens * (0.15 + (1.0 - fitness) * 0.2)))
            est_duration = max(0.5, round(2.5 - (fitness * 1.5), 2))
            confidence = round(max(0.2, min(0.99, fitness * 1.05)), 2)

            rationale = (
                f"{profile.display_name} bid with fitness={fitness:.2f} "
                f"(affinity={AgentRoleRegistry.get_tool_affinity(role, tool_name):.2f}, "
                f"workload={self.active_workloads.get(role, 0)})"
            )

            bid = TaskBid(
                agent_role=role,
                node_id=node_id,
                fitness_score=fitness,
                estimated_tokens=est_tokens,
                estimated_duration_sec=est_duration,
                confidence=confidence,
                rationale=rationale,
            )
            bids.append(bid)

        return bids

    def select_winning_bid(self, node_id: str, bids: List[TaskBid]) -> AuctionResult:
        """Select winner from bids using fitness score, tie-breaking, and fallback."""
        if not bids:
            raise ValueError(f"No bids submitted for node {node_id}")

        # Sort bids: primary = fitness_score DESC, secondary = role priority DESC
        def bid_sort_key(b: TaskBid) -> tuple:
            p = AgentRoleRegistry.get_profile(b.agent_role)
            return (b.fitness_score, p.priority, -self.active_workloads.get(b.agent_role, 0))

        sorted_bids = sorted(bids, key=bid_sort_key, reverse=True)
        top_bid = sorted_bids[0]

        # Fallback to ARCHITECT if all agents have low confidence
        if top_bid.fitness_score < self.MIN_CONFIDENCE_THRESHOLD:
            architect_bid = next(
                (b for b in bids if b.agent_role == AgentRole.ARCHITECT),
                top_bid,
            )
            top_bid = architect_bid.model_copy(
                update={
                    "rationale": (
                        f"Fallback assignment to Architect: Top fitness "
                        f"({sorted_bids[0].fitness_score:.2f}) fell below threshold "
                        f"{self.MIN_CONFIDENCE_THRESHOLD}"
                    )
                }
            )

        return AuctionResult(
            node_id=node_id,
            winning_role=top_bid.agent_role,
            winning_bid=top_bid,
            all_bids=sorted_bids,
        )

    def conduct_auction_for_task(
        self,
        node_id: str,
        tool_name: str,
        node_title: str = "",
        node_desc: str = "",
    ) -> AuctionResult:
        """Run auction for a single task node and record workload."""
        bids = self.generate_bids_for_node(node_id, tool_name, node_title, node_desc)
        result = self.select_winning_bid(node_id, bids)
        self.update_workload(result.winning_role, 1)
        return result

    def conduct_auction_for_dag(
        self,
        dag_or_nodes: Union[Any, List[Dict[str, Any]]],
    ) -> Dict[str, AuctionResult]:
        """Conduct auction for all nodes in a MissionDAG or node dictionary list."""
        results: Dict[str, AuctionResult] = {}

        # Support both MissionDAG Pydantic object and list of node dicts/objects
        nodes: List[Any] = []
        if hasattr(dag_or_nodes, "nodes"):
            nodes = dag_or_nodes.nodes
        elif isinstance(dag_or_nodes, list):
            nodes = dag_or_nodes
        else:
            raise TypeError(f"Unsupported DAG format: {type(dag_or_nodes)}")

        for node in nodes:
            if hasattr(node, "node_id"):
                node_id = node.node_id
                tool_name = getattr(node, "tool_name", "")
                title = getattr(node, "title", "")
                desc = getattr(node, "description", "")
            elif isinstance(node, dict):
                node_id = str(node.get("node_id", node.get("id", "")))
                tool_name = str(node.get("tool_name", node.get("tool", "")))
                title = str(node.get("title", ""))
                desc = str(node.get("description", ""))
            else:
                continue

            result = self.conduct_auction_for_task(node_id, tool_name, title, desc)
            results[node_id] = result

        return results
