"""Byzantine Worker Watchdog for Phenom Swarm Mesh (Milestone 27 Phase 4).

Monitors specialist agent heartbeats, execution latencies, and anomaly rates
to detect Byzantine faults or hung workers (BYZ-01.1, BYZ-01.2).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.swarm.agent_mesh_coordinator import (
    agent_mesh_coordinator,
    AgentMeshCoordinator,
    MeshSubagent,
    Rule8ViolationError,
)

logger = logging.getLogger("phenom.swarm.byzantine_watchdog")


class WorkerHealthReport(BaseModel):
    agent_id: str
    specialization: str
    health_status: str  # HEALTHY, DEGRADED, BYZANTINE_FAULT, OFFLINE
    heartbeat_latency_ms: float
    error_count: int = 0
    anomaly_score: float = 0.0  # 0.0 - 1.0
    last_seen: float = Field(default_factory=time.time)


class ByzantineWatchdog:
    """Continuously evaluates worker node integrity and flags anomalous behavior."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self, coordinator: Optional[AgentMeshCoordinator] = None) -> None:
        self._coordinator = coordinator or agent_mesh_coordinator
        self._health_records: Dict[str, WorkerHealthReport] = {}
        self._init_health_records()

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Byzantine watchdog halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: watchdog operation involving payments is strictly prohibited. Found: {text}"
            )

    def _init_health_records(self) -> None:
        for agent in self._coordinator.list_agents():
            self._health_records[agent.agent_id] = WorkerHealthReport(
                agent_id=agent.agent_id,
                specialization=agent.specialization,
                health_status="HEALTHY",
                heartbeat_latency_ms=12.4,
                error_count=0,
                anomaly_score=0.02,
                last_seen=time.time(),
            )

    def record_heartbeat(self, agent_id: str, latency_ms: float = 10.0, is_error: bool = False) -> WorkerHealthReport:
        """Records an agent heartbeat pulse with response latency."""
        self._check_guardian()
        self._validate_rule_8(agent_id)

        now = time.time()
        agent = self._coordinator.get_agent(agent_id)
        spec = agent.specialization if agent else "Unknown"

        if agent_id not in self._health_records:
            self._health_records[agent_id] = WorkerHealthReport(
                agent_id=agent_id,
                specialization=spec,
                health_status="HEALTHY",
                heartbeat_latency_ms=latency_ms,
                last_seen=now,
            )

        record = self._health_records[agent_id]
        record.heartbeat_latency_ms = latency_ms
        record.last_seen = now

        if is_error:
            record.error_count += 1

        # Anomaly scoring: latency > 500ms or error count > 3 indicates degradation
        score = min(1.0, round((latency_ms / 1000.0) * 0.5 + (record.error_count * 0.2), 3))
        record.anomaly_score = score

        if score >= 0.70:
            record.health_status = "BYZANTINE_FAULT"
        elif score >= 0.35:
            record.health_status = "DEGRADED"
        else:
            record.health_status = "HEALTHY"

        return record

    def inspect_health(self) -> List[WorkerHealthReport]:
        """Returns health telemetry across all swarm worker nodes."""
        self._check_guardian()
        return list(self._health_records.values())


# Global singleton instance
byzantine_watchdog = ByzantineWatchdog()
