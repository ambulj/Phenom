import time
import uuid
from typing import List
from services.backend.schemas.cognitive_twin import (
    EpisodicNodeType,
    ContextualAnticipation,
)
from services.backend.cognitive_twin.graph_store import EpisodicLifeGraphStore


class ContextualAnticipationEngine:
    """
    Projective intent anticipation engine.
    Traverses neighborhood subgraphs of active context nodes and ranks next probable actions.
    """

    TOOL_MAPPINGS = {
        "coding": "workspace_search",
        "email": "email_draft",
        "calendar": "calendar_query",
        "notes": "notes_query",
        "research": "browser_research",
        "review": "code_review",
    }

    def __init__(self, store: EpisodicLifeGraphStore, min_confidence: float = 0.65):
        self._store = store
        self._min_confidence = min_confidence

    def project_anticipations(self, active_node_ids: List[str]) -> List[ContextualAnticipation]:
        anticipations: List[ContextualAnticipation] = []
        now = time.time()

        if not active_node_ids:
            # Fallback: check highest affinity nodes
            top_nodes = self._store.query_nodes(limit=3)
            active_node_ids = [n.node_id for n in top_nodes]

        seen_actions = set()

        for node_id in active_node_ids:
            neighbors = self._store.get_neighbors(node_id)
            for item in neighbors:
                nbr_node = item["node"]
                edge_weight = item["edge_weight"]

                # Calculate confidence score based on affinity weight & edge weight
                conf = min(0.99, (nbr_node.affinity_weight * 0.4 + edge_weight * 0.6) / 2.0)
                if conf < self._min_confidence:
                    continue

                action_key = f"{nbr_node.node_type.value}:{nbr_node.label}"
                if action_key in seen_actions:
                    continue
                seen_actions.add(action_key)

                # Map suggested tool
                suggested_tool = None
                for kw, tool in self.TOOL_MAPPINGS.items():
                    if kw in nbr_node.label.lower():
                        suggested_tool = tool
                        break

                anticipations.append(
                    ContextualAnticipation(
                        anticipation_id=f"ant-{uuid.uuid4().hex[:8]}",
                        suggested_action=f"Suggested next step: {nbr_node.label}",
                        target_tool=suggested_tool,
                        confidence=round(conf, 3),
                        reasoning_path=f"Active context linked via '{item['relationship']}' (weight: {edge_weight:.1f})",
                        timestamp=now,
                    )
                )

        # Sort descending by confidence
        anticipations.sort(key=lambda a: a.confidence, reverse=True)
        return anticipations[:5]
