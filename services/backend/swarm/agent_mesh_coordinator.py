"""Agent Mesh Coordinator for Phenom Swarm Mesh (Milestone 27 Phase 1).

Coordinates an in-memory, peer-to-peer specialist subagent mesh with typed asynchronous
local message queues, zero cloud egress (Rule 4), and Guardian halt SLA compliance (MSH-01.1, MSH-01.2).
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.swarm.subagent_registry import (
    SpecialistCapabilityProfile,
    get_specialist_profile,
    SPECIALIST_PROFILES,
)

logger = logging.getLogger("phenom.swarm.mesh_coordinator")


class Rule8ViolationError(Exception):
    """Raised when swarm message or agent directive contains payment/checkout keywords."""
    pass


class MeshMessage(BaseModel):
    msg_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    sender_id: str
    recipient_id: str  # agent_id or 'BROADCAST'
    message_type: str  # QUERY, DIRECTIVE, STATE_UPDATE, BID, HEARTBEAT
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class MeshSubagent(BaseModel):
    agent_id: str
    specialization: str
    status: str = "IDLE"  # IDLE, BUSY, HALTED
    profile: SpecialistCapabilityProfile
    mailbox: List[MeshMessage] = Field(default_factory=list)
    sent_count: int = 0
    received_count: int = 0
    spawned_at: float = Field(default_factory=time.time)


class AgentMeshCoordinator:
    """Manages spawning, routing, and lifecycle of local specialist subagents."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._agents: Dict[str, MeshSubagent] = {}
        self._message_history: List[MeshMessage] = []
        self._init_default_mesh()

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Agent mesh coordinator halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: swarm operations involving payments are strictly prohibited. Found: {text}"
            )

    def _init_default_mesh(self) -> None:
        """Spawn initial core specialist team."""
        for spec in ["CodeArchitect", "SecurityAuditor", "TestOrchestrator", "KnowledgeResearcher"]:
            self.spawn_agent(specialization=spec, custom_id=f"agent_{spec.lower()}")

    def spawn_agent(self, specialization: str, custom_id: Optional[str] = None) -> MeshSubagent:
        """Spawns an isolated specialist subagent node in the local mesh."""
        self._check_guardian()
        self._validate_rule_8(specialization)

        profile = get_specialist_profile(specialization)
        if not profile:
            raise ValueError(f"Unknown specialization: '{specialization}'. Allowed: {list(SPECIALIST_PROFILES.keys())}")

        aid = custom_id or f"agent_{specialization.lower()}_{uuid.uuid4().hex[:4]}"
        agent = MeshSubagent(
            agent_id=aid,
            specialization=specialization,
            status="IDLE",
            profile=profile,
        )
        self._agents[aid] = agent
        return agent

    def get_agent(self, agent_id: str) -> Optional[MeshSubagent]:
        """Look up agent by ID."""
        self._check_guardian()
        return self._agents.get(agent_id)

    def list_agents(self) -> List[MeshSubagent]:
        """List all registered mesh agents."""
        self._check_guardian()
        return list(self._agents.values())

    def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: str,
        payload: Dict[str, Any],
    ) -> MeshMessage:
        """Route an in-memory asynchronous message to a specific agent or broadcast."""
        self._check_guardian()
        self._validate_rule_8(sender_id)
        self._validate_rule_8(recipient_id)
        self._validate_rule_8(message_type)
        for k, v in payload.items():
            if isinstance(v, str):
                self._validate_rule_8(v)

        msg = MeshMessage(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=message_type.upper(),
            payload=payload,
        )

        if recipient_id == "BROADCAST":
            for aid, agent in self._agents.items():
                if aid != sender_id and agent.status != "HALTED":
                    agent.mailbox.append(msg)
                    agent.received_count += 1
        else:
            if recipient_id not in self._agents:
                raise ValueError(f"Recipient agent '{recipient_id}' not found in mesh.")
            target = self._agents[recipient_id]
            if target.status == "HALTED":
                raise RuntimeError(f"Cannot deliver message: Recipient agent '{recipient_id}' is HALTED.")
            target.mailbox.append(msg)
            target.received_count += 1

        if sender_id in self._agents:
            self._agents[sender_id].sent_count += 1

        self._message_history.append(msg)
        return msg

    def halt_agent(self, agent_id: str) -> bool:
        """Halt a specific agent node."""
        self._check_guardian()
        if agent_id in self._agents:
            self._agents[agent_id].status = "HALTED"
            return True
        return False

    def get_topology(self) -> Dict[str, Any]:
        """Inspect current mesh network topology and message counts."""
        self._check_guardian()
        agents_data = []
        for a in self._agents.values():
            agents_data.append({
                "agent_id": a.agent_id,
                "specialization": a.specialization,
                "status": a.status,
                "mailbox_size": len(a.mailbox),
                "sent_count": a.sent_count,
                "received_count": a.received_count,
                "skill_vector": a.profile.skill_vector,
            })
        return {
            "total_agents": len(self._agents),
            "total_messages_routed": len(self._message_history),
            "agents": agents_data,
        }


# Global singleton instance
agent_mesh_coordinator = AgentMeshCoordinator()
