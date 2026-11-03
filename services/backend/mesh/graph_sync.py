"""
Bi-Directional GraphRAG Delta Synchronizer for Phenom P2P Mesh
Synchronizes personal knowledge graph nodes, notes, and edges across
local desktop and companion nodes using Last-Write-Wins (LWW) conflict resolution.
Operates strictly over local Wi-Fi with zero cloud relay.
"""

import hashlib
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from services.backend.schemas.mesh import GraphSyncDelta
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.mesh.graph_sync")


class MeshGraphSynchronizer:
    """
    Bi-directional GraphRAG delta synchronizer.
    Resolves concurrent multi-device edits with Last-Write-Wins (LWW) semantics.
    """

    def __init__(self, node_id: str = "phenom-desktop-host"):
        self.node_id = node_id
        # In-memory graph delta store: uri -> node dict (includes content, mtime, checksum)
        self._nodes: Dict[str, Dict[str, Any]] = {}
        # In-memory edge store: edge_id -> edge dict
        self._edges: Dict[str, Dict[str, Any]] = {}

    def record_node(self, uri: str, title: str, content: str, domain: str = "vault", timestamp: Optional[float] = None) -> Dict[str, Any]:
        """Record or update a local graph node."""
        if guardian.is_halted:
            raise PermissionError("Graph operation rejected: Guardian Kill Switch is engaged.")

        ts = timestamp or time.time()
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        node_record = {
            "uri": uri,
            "title": title,
            "content": content,
            "domain": domain,
            "checksum": checksum,
            "updated_at": ts
        }
        self._nodes[uri] = node_record
        return node_record

    def record_edge(self, source_uri: str, target_uri: str, relation: str, timestamp: Optional[float] = None) -> Dict[str, Any]:
        """Record or update a graph edge."""
        if guardian.is_halted:
            raise PermissionError("Graph operation rejected: Guardian Kill Switch is engaged.")

        ts = timestamp or time.time()
        edge_id = f"{source_uri}->{relation}->{target_uri}"
        edge_record = {
            "edge_id": edge_id,
            "source_uri": source_uri,
            "target_uri": target_uri,
            "relation": relation,
            "updated_at": ts
        }
        self._edges[edge_id] = edge_record
        return edge_record

    def generate_outbound_deltas(self, since_timestamp: float = 0.0) -> GraphSyncDelta:
        """
        Generate delta package containing nodes and edges modified since specified timestamp.
        """
        if guardian.is_halted:
            raise PermissionError("Graph sync rejected: Guardian Kill Switch is engaged.")

        changed_nodes: List[Dict[str, Any]] = []
        for n in self._nodes.values():
            if n["updated_at"] >= since_timestamp:
                changed_nodes.append(n)

        changed_edges: List[Dict[str, Any]] = []
        for e in self._edges.values():
            if e["updated_at"] >= since_timestamp:
                changed_edges.append(e)

        return GraphSyncDelta(
            sync_id=str(uuid.uuid4()),
            origin_node_id=self.node_id,
            timestamp=time.time(),
            node_deltas=changed_nodes,
            edge_deltas=changed_edges
        )

    def apply_inbound_deltas(self, delta: GraphSyncDelta) -> Dict[str, int]:
        """
        Apply incoming delta package from a companion or peer node.
        Applies Last-Write-Wins (LWW) conflict resolution:
        If incoming updated_at > existing updated_at, update is applied; otherwise skipped.
        """
        if guardian.is_halted:
            raise PermissionError("Graph delta application rejected: Guardian Kill Switch is engaged.")

        nodes_updated = 0
        nodes_skipped = 0
        edges_updated = 0
        edges_skipped = 0

        # Apply node deltas
        for node in delta.node_deltas:
            uri = node.get("uri")
            if not uri:
                continue

            incoming_ts = float(node.get("updated_at", 0.0))
            existing = self._nodes.get(uri)

            if existing is None or incoming_ts > float(existing.get("updated_at", 0.0)):
                self._nodes[uri] = dict(node)
                nodes_updated += 1
            else:
                nodes_skipped += 1

        # Apply edge deltas
        for edge in delta.edge_deltas:
            edge_id = edge.get("edge_id")
            if not edge_id:
                edge_id = f"{edge.get('source_uri')}->{edge.get('relation')}->{edge.get('target_uri')}"

            incoming_ts = float(edge.get("updated_at", 0.0))
            existing_edge = self._edges.get(edge_id)

            if existing_edge is None or incoming_ts > float(existing_edge.get("updated_at", 0.0)):
                self._edges[edge_id] = dict(edge)
                edges_updated += 1
            else:
                edges_skipped += 1

        logger.info(
            f"Applied GraphRAG delta {delta.sync_id}: "
            f"{nodes_updated} nodes updated, {nodes_skipped} skipped; "
            f"{edges_updated} edges updated, {edges_skipped} skipped."
        )

        return {
            "nodes_updated": nodes_updated,
            "nodes_skipped": nodes_skipped,
            "edges_updated": edges_updated,
            "edges_skipped": edges_skipped
        }

    def get_node(self, uri: str) -> Optional[Dict[str, Any]]:
        """Retrieve node by URI."""
        return self._nodes.get(uri)
