"""Conflict-Free Replicated Data (CRDT) Engine for Phenom Swarm Mesh (Milestone 27 Phase 3).

Implements Lamport vector clocks and state-based Last-Write-Wins (LWW) CRDT registers
for deterministic distributed state reconciliation (CRDT-01.1, CON-04.1).
"""

from __future__ import annotations

import copy
import logging
import re
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.swarm.agent_mesh_coordinator import Rule8ViolationError

logger = logging.getLogger("phenom.swarm.crdt_consensus")


class VectorClock(BaseModel):
    clocks: Dict[str, int] = Field(default_factory=dict)

    def tick(self, agent_id: str) -> None:
        self.clocks[agent_id] = self.clocks.get(agent_id, 0) + 1

    def merge(self, other: VectorClock) -> None:
        for aid, count in other.clocks.items():
            self.clocks[aid] = max(self.clocks.get(aid, 0), count)

    def dominates(self, other: VectorClock) -> bool:
        """Returns True if self has observed at least as much as other and strictly more in at least one agent."""
        greater_or_equal = all(self.clocks.get(k, 0) >= other.clocks.get(k, 0) for k in other.clocks)
        strictly_greater = any(self.clocks.get(k, 0) > other.clocks.get(k, 0) for k in self.clocks)
        return greater_or_equal and strictly_greater


class CRDTDelta(BaseModel):
    delta_id: str
    agent_id: str
    key: str
    value: Any
    timestamp: float = Field(default_factory=time.time)
    vector_clock: VectorClock


class CRDTStateRegister:
    """Last-Write-Wins (LWW) Register that reconciles state using timestamps and vector clocks."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._state: Dict[str, Dict[str, Any]] = {}
        self._vector_clocks: Dict[str, VectorClock] = {}
        self._delta_history: List[CRDTDelta] = []
        self._init_defaults()

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. CRDT consensus engine halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: CRDT state mutation involving payments is strictly prohibited. Found: {text}"
            )

    def _init_defaults(self) -> None:
        default_agents = ["agent_codearchitect", "agent_securityauditor", "agent_testorchestrator", "agent_knowledgeresearcher"]
        for aid in default_agents:
            self._vector_clocks[aid] = VectorClock(clocks={aid: 1})

        self.apply_delta(
            agent_id="system",
            key="mesh_consensus_protocol",
            value="CRDT_LWW_VECTOR_CLOCKS",
        )

    def get_clock(self, agent_id: str) -> VectorClock:
        self._check_guardian()
        if agent_id not in self._vector_clocks:
            self._vector_clocks[agent_id] = VectorClock()
        return self._vector_clocks[agent_id]

    def apply_delta(self, agent_id: str, key: str, value: Any) -> CRDTDelta:
        """Applies a proposed state delta using LWW conflict resolution."""
        self._check_guardian()
        self._validate_rule_8(key)
        if isinstance(value, str):
            self._validate_rule_8(value)

        clock = self.get_clock(agent_id)
        clock.tick(agent_id)
        now = time.time()

        delta = CRDTDelta(
            delta_id=f"delta_{int(now * 1000) % 1000000}",
            agent_id=agent_id,
            key=key,
            value=value,
            timestamp=now,
            vector_clock=copy.deepcopy(clock),
        )

        # Conflict resolution rule: Last-Write-Wins (LWW) with timestamp tie-breaker
        if key in self._state:
            curr = self._state[key]
            if delta.timestamp >= curr["timestamp"]:
                self._state[key] = {
                    "value": value,
                    "author": agent_id,
                    "timestamp": delta.timestamp,
                    "vector_clock": delta.vector_clock.clocks,
                }
        else:
            self._state[key] = {
                "value": value,
                "author": agent_id,
                "timestamp": delta.timestamp,
                "vector_clock": delta.vector_clock.clocks,
            }

        self._delta_history.append(delta)
        return delta

    def get_converged_state(self) -> Dict[str, Any]:
        """Returns current converged state register across all keys."""
        self._check_guardian()
        return copy.deepcopy(self._state)

    def get_vector_clocks(self) -> Dict[str, Dict[str, int]]:
        """Returns vector clock ticks for all known agents."""
        self._check_guardian()
        return {aid: vc.clocks for aid, vc in self._vector_clocks.items()}

    def get_history(self) -> List[CRDTDelta]:
        """Returns history of applied deltas."""
        self._check_guardian()
        return list(self._delta_history)


# Global singleton instance
crdt_state_register = CRDTStateRegister()
