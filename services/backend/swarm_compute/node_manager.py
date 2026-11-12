"""
Swarm Node Manager (SWM-01, SAF-01, SAF-02).
Tracks discovered peer devices, hardware metrics (VRAM, RAM, flops),
battery percentages, AC charging state, and thermal status with zero cloud relay (Rule 4).
"""

import logging
import time
from typing import Dict, List, Optional

from services.backend.schemas.swarm_compute import (
    ComputeNodeType,
    SwarmClusterState,
    SwarmNodeTelemetry,
)

logger = logging.getLogger(__name__)


class SwarmNodeManager:
    """Manages peer compute nodes in the local encrypted P2P mesh."""

    def __init__(self, host_node_id: str = "phenom-desktop-host") -> None:
        self.host_node_id = host_node_id
        self._nodes: Dict[str, SwarmNodeTelemetry] = {}
        self._halted: bool = False

        # Initialize sovereign host node (Desktop GPU)
        self._init_host_node()

    def _init_host_node(self) -> None:
        """Register local sovereign host desktop node."""
        self._nodes[self.host_node_id] = SwarmNodeTelemetry(
            node_id=self.host_node_id,
            device_name="Phenom Host Workstation (RTX GPU)",
            node_type=ComputeNodeType.DESKTOP_GPU,
            available_vram_mb=8192,
            available_ram_mb=32768,
            battery_percent=100,
            is_plugged_in=True,
            thermal_throttled=False,
            compute_flops_rating=10.0,
            is_online=True,
            last_heartbeat=time.time(),
        )

    def halt(self) -> None:
        """Synchronous halt for Guardian kill switch (< 10ms SLA)."""
        self._halted = True
        logger.info("[SwarmNodeManager] SwarmNodeManager halted synchronously by Guardian.")

    def reset(self) -> None:
        self._halted = False
        self._nodes.clear()
        self._init_host_node()

    def is_halted(self) -> bool:
        return self._halted

    def register_node(
        self,
        node_id: str,
        device_name: str,
        node_type: ComputeNodeType | str = ComputeNodeType.LAPTOP_HYBRID,
        available_vram_mb: int = 0,
        available_ram_mb: int = 4096,
        battery_percent: int = 100,
        is_plugged_in: bool = True,
        thermal_throttled: bool = False,
        compute_flops_rating: float = 1.0,
    ) -> SwarmNodeTelemetry:
        """Register or update a peer node in the cluster."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: Node registration blocked.")

        if isinstance(node_type, str):
            try:
                ntype = ComputeNodeType(node_type.upper())
            except ValueError:
                ntype = ComputeNodeType.LAPTOP_HYBRID
        else:
            ntype = node_type

        node = SwarmNodeTelemetry(
            node_id=node_id,
            device_name=device_name,
            node_type=ntype,
            available_vram_mb=max(0, available_vram_mb),
            available_ram_mb=max(0, available_ram_mb),
            battery_percent=max(0, min(100, battery_percent)),
            is_plugged_in=is_plugged_in,
            thermal_throttled=thermal_throttled,
            compute_flops_rating=max(0.1, compute_flops_rating),
            is_online=True,
            last_heartbeat=time.time(),
        )

        self._nodes[node_id] = node
        logger.info(f"[SwarmNodeManager] Registered node {node_id} ({device_name}) [{ntype.value}]")
        return node

    def record_heartbeat(self, node_id: str) -> bool:
        """Record a heartbeat timestamp for an active node."""
        if self._halted or node_id not in self._nodes:
            return False
        self._nodes[node_id].last_heartbeat = time.time()
        self._nodes[node_id].is_online = True
        return True

    def remove_node(self, node_id: str) -> bool:
        """Remove a peer node (cannot remove sovereign host node)."""
        if node_id == self.host_node_id:
            return False
        if node_id in self._nodes:
            del self._nodes[node_id]
            return True
        return False

    def mark_node_offline(self, node_id: str) -> bool:
        """Mark a node as offline (e.g. on disconnect or timeout)."""
        if node_id in self._nodes:
            self._nodes[node_id].is_online = False
            return True
        return False

    def get_node(self, node_id: str) -> Optional[SwarmNodeTelemetry]:
        return self._nodes.get(node_id)

    def list_nodes(self, online_only: bool = True) -> List[SwarmNodeTelemetry]:
        """List active cluster nodes, checking heartbeat freshness."""
        now = time.time()
        for nid, node in list(self._nodes.items()):
            if nid != self.host_node_id and (now - node.last_heartbeat) > 30.0:
                node.is_online = False

        if online_only:
            return [n for n in self._nodes.values() if n.is_online]
        return list(self._nodes.values())

    def get_cluster_state(self) -> SwarmClusterState:
        """Compute aggregated cluster health and telemetry."""
        nodes = self.list_nodes(online_only=False)
        online_nodes = [n for n in nodes if n.is_online]
        total_vram = sum(n.available_vram_mb for n in online_nodes)
        total_ram = sum(n.available_ram_mb for n in online_nodes)

        return SwarmClusterState(
            cluster_id="phenom-local-cluster",
            active_node_count=len(online_nodes),
            total_vram_mb=total_vram,
            total_ram_mb=total_ram,
            nodes=nodes,
            active_workload_count=0,
            cluster_load_factor=0.0,
            is_healthy=len(online_nodes) > 0 and not self._halted,
            last_updated=time.time(),
        )


# Global singleton instance
swarm_node_manager = SwarmNodeManager()
