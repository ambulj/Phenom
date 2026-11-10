"""
Temporal Semantic Intent Memory Graph.
Maintains user preferences, architectural decisions, and operational guidelines over time
with temporal validity intervals (`valid_from`, `valid_until`), lineage tracking, and conflict detection.

Part of Phenom 22.0 Sovereign Swarm Intelligence (MEM-03.1 / MEM-03.2).
"""

import time
import uuid
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.automation.gui_controller import Rule8ViolationError

RULE_8_PAYMENT_RE = re.compile(
    r"\b(?:checkout|place\s+order|pay\s+now|buy\s+now|complete\s+purchase|complete\s+payment|payment|credit\s+card|cvv|password)\b",
    re.IGNORECASE
)


class TemporalIntentNode(BaseModel):
    intent_id: str = Field(..., description="Unique intent/preference identifier")
    category: str = Field(..., description="e.g. coding_style, toolchain, privacy, voice, scheduling")
    statement: str = Field(..., description="Human or system preference statement")
    context: Dict[str, Any] = Field(default_factory=dict, description="Metadata or context tags")
    valid_from: float = Field(default_factory=time.time, description="Unix timestamp when preference became valid")
    valid_until: Optional[float] = Field(default=None, description="Unix timestamp when superseded or expired")
    is_active: bool = Field(default=True, description="Whether preference is currently applicable")
    superseded_by: Optional[str] = Field(default=None, description="intent_id of the newer superseding preference")
    confidence: float = Field(default=1.0, description="Confidence rating between 0.0 and 1.0")


class PreferenceEdge(BaseModel):
    edge_id: str
    source_intent_id: str
    target_intent_id: str
    relation: str = Field(default="supersedes", description="supersedes, contradicts, refines, depends_on")
    created_at: float = Field(default_factory=time.time)


class TemporalIntentGraph:
    """
    In-memory graph of temporal intent nodes and preference relationships.
    Preserves historical versions when preferences evolve (Rule 7 non-destructibility).
    """

    def __init__(self):
        self._nodes: Dict[str, TemporalIntentNode] = {}
        self._edges: List[PreferenceEdge] = []

    def get_node(self, intent_id: str) -> Optional[TemporalIntentNode]:
        return self._nodes.get(intent_id)

    def record_preference(
        self,
        category: str,
        statement: str,
        context: Optional[Dict[str, Any]] = None,
        supersedes_id: Optional[str] = None,
        confidence: float = 1.0,
    ) -> TemporalIntentNode:
        """
        Records a new preference. If supersedes_id is provided, marks the previous preference
        as expired with valid_until = now and establishes a 'supersedes' edge.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Cannot record preference.")

        if RULE_8_PAYMENT_RE.search(statement):
            raise Rule8ViolationError(f"Rule 8 Violation: Cannot store payment/checkout credentials or preferences: {statement}")

        now = time.time()
        iid = f"intent_{uuid.uuid4().hex[:8]}"

        # Handle supersession of existing preference
        if supersedes_id and supersedes_id in self._nodes:
            old_node = self._nodes[supersedes_id]
            old_node.is_active = False
            old_node.valid_until = now
            old_node.superseded_by = iid

            self._edges.append(
                PreferenceEdge(
                    edge_id=f"edge_{uuid.uuid4().hex[:6]}",
                    source_intent_id=iid,
                    target_intent_id=supersedes_id,
                    relation="supersedes",
                    created_at=now,
                )
            )

        new_node = TemporalIntentNode(
            intent_id=iid,
            category=category,
            statement=statement,
            context=context or {},
            valid_from=now,
            valid_until=None,
            is_active=True,
            superseded_by=None,
            confidence=confidence,
        )
        self._nodes[iid] = new_node
        return new_node

    def query_active_preferences(
        self,
        category: Optional[str] = None,
        at_timestamp: Optional[float] = None
    ) -> List[TemporalIntentNode]:
        """
        Queries all active preferences, optionally filtered by category or at a point in historical time.
        """
        target_time = at_timestamp if at_timestamp is not None else time.time()
        results: List[TemporalIntentNode] = []

        for node in self._nodes.values():
            if category and node.category != category:
                continue
            # Point-in-time validity check: valid_from <= target_time and (valid_until is None or valid_until > target_time)
            if node.valid_from <= target_time:
                if node.valid_until is None or node.valid_until > target_time:
                    results.append(node)

        return sorted(results, key=lambda n: n.valid_from, reverse=True)

    def get_preference_lineage(self, intent_id: str) -> List[TemporalIntentNode]:
        """
        Walks the historical lineage of a preference from the earliest ancestor to the current active head.
        """
        node = self.get_node(intent_id)
        if not node:
            return []

        # Find backwards ancestors
        ancestors: List[TemporalIntentNode] = []
        curr = node
        while True:
            # Look for incoming supersedes edges where source is curr
            parent_edge = next((e for e in self._edges if e.source_intent_id == curr.intent_id and e.relation == "supersedes"), None)
            if parent_edge and parent_edge.target_intent_id in self._nodes:
                curr = self._nodes[parent_edge.target_intent_id]
                ancestors.insert(0, curr)
            else:
                break

        # Find forward descendants
        descendants: List[TemporalIntentNode] = []
        curr = node
        while curr.superseded_by and curr.superseded_by in self._nodes:
            curr = self._nodes[curr.superseded_by]
            descendants.append(curr)

        return ancestors + [node] + descendants

    def detect_conflicts(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Detects conflicting active preferences within the same category (e.g. diametrically opposing statements).
        """
        active_nodes = self.query_active_preferences(category=category)
        conflicts = []

        # Simple semantic contradiction heuristic for antonym pairs
        antonym_pairs = [
            (r"\bverbose\b", r"\bconcise\b"),
            (r"\bdark\s+mode\b", r"\blight\s+mode\b"),
            (r"\bcloud\b", r"\blocal\s+only\b"),
            (r"\balways\s+ask\b", r"\bnever\s+ask\b"),
        ]

        for i in range(len(active_nodes)):
            for j in range(i + 1, len(active_nodes)):
                n1, n2 = active_nodes[i], active_nodes[j]
                if n1.category != n2.category:
                    continue

                for pat1, pat2 in antonym_pairs:
                    m1 = re.search(pat1, n1.statement, re.IGNORECASE)
                    m2 = re.search(pat2, n2.statement, re.IGNORECASE)
                    if (m1 and m2) or (re.search(pat2, n1.statement, re.IGNORECASE) and re.search(pat1, n2.statement, re.IGNORECASE)):
                        conflicts.append({
                            "category": n1.category,
                            "intent_a": {"id": n1.intent_id, "statement": n1.statement},
                            "intent_b": {"id": n2.intent_id, "statement": n2.statement},
                            "reason": f"Opposing directives detected ({pat1} vs {pat2})"
                        })

        return conflicts


# Global singleton
temporal_intent_graph = TemporalIntentGraph()
