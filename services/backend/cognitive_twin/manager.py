from typing import Dict, Any, List, Optional
from services.backend.schemas.cognitive_twin import (
    EpisodicNodeType,
    EpisodicNode,
    ContextualAnticipation,
    CognitiveTwinState,
)
from services.backend.cognitive_twin.graph_store import EpisodicLifeGraphStore
from services.backend.cognitive_twin.anticipation_engine import ContextualAnticipationEngine


class CognitiveTwinManager:
    """
    Coordinates autobiographical episodic life-graph synthesis,
    proactive anticipation projections, and Guardian emergency lockdowns.
    """

    def __init__(self, db_path: str = ":memory:"):
        self._store = EpisodicLifeGraphStore(db_path=db_path)
        self._anticipation_engine = ContextualAnticipationEngine(self._store)
        self._active_node_ids: List[str] = []
        self._is_locked: bool = False

    @property
    def is_locked(self) -> bool:
        return self._is_locked

    def ingest_episode(
        self,
        activity_label: str,
        node_type: EpisodicNodeType = EpisodicNodeType.ACTIVITY,
        related_labels: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> EpisodicNode:
        if self._is_locked:
            raise PermissionError("Cognitive Twin is locked under Guardian halt. Ingest blocked.")

        primary_node = self._store.upsert_node(
            label=activity_label,
            node_type=node_type,
            attributes=attributes,
        )

        # Update active context
        if primary_node.node_id not in self._active_node_ids:
            self._active_node_ids.append(primary_node.node_id)
            if len(self._active_node_ids) > 10:
                self._active_node_ids.pop(0)

        # Link related entities
        if related_labels:
            for rel in related_labels:
                target_node = self._store.upsert_node(
                    label=rel,
                    node_type=EpisodicNodeType.TOPIC if "topic" in rel.lower() else EpisodicNodeType.CONTEXT,
                )
                self._store.add_edge(
                    source_id=primary_node.node_id,
                    target_id=target_node.node_id,
                    relationship="associated_context",
                )

        return primary_node

    def query_graph(
        self,
        node_type: Optional[EpisodicNodeType] = None,
        label_query: Optional[str] = None,
        limit: int = 20,
    ) -> List[EpisodicNode]:
        if self._is_locked:
            raise PermissionError("Cognitive Twin is locked under Guardian halt.")
        return self._store.query_nodes(node_type=node_type, label_query=label_query, limit=limit)

    def prune_graph(self, min_affinity_weight: float = 0.10) -> int:
        if self._is_locked:
            raise PermissionError("Cognitive Twin is locked under Guardian halt.")
        return self._store.prune_low_affinity(min_affinity=min_affinity_weight)

    def get_anticipations(self) -> List[ContextualAnticipation]:
        if self._is_locked:
            return []
        return self._anticipation_engine.project_anticipations(self._active_node_ids)

    def get_status(self, include_anticipations: bool = True) -> CognitiveTwinState:
        counts = self._store.counts()
        anticipations = self.get_anticipations() if include_anticipations else []
        return CognitiveTwinState(
            total_nodes=counts["nodes"],
            total_edges=counts["edges"],
            active_context_nodes=list(self._active_node_ids),
            anticipations=anticipations,
            is_locked=self._is_locked,
        )

    def halt(self) -> None:
        """
        Synchronous Guardian halt (< 10ms SLA).
        Locks the cognitive graph and flushes volatile memory caches.
        """
        self._is_locked = True
        self._active_node_ids.clear()

    def reset(self) -> None:
        """Resets the lock state following Guardian resume."""
        self._is_locked = False
        self._active_node_ids.clear()
