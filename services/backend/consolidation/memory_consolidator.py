"""Memory Consolidator for Phenom (Milestone 26 Phase 1).

Consolidates episodic session traces into enduring semantic knowledge nodes with
exponential importance decay and reversible soft-pruning (MEM-06.1, MEM-06.2).
"""

from __future__ import annotations

import logging
import math
import re
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.consolidation.memory_consolidator")


class Rule8ViolationError(Exception):
    """Raised when an episodic memory trace or consolidation targets checkout, payment, or financial data."""
    pass


class EpisodicTrace(BaseModel):
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:8]}")
    session_id: str
    timestamp: float = Field(default_factory=time.time)
    interaction_type: str  # QUERY, CODE_EDIT, TOOL_CALL, USER_CORRECTION
    content: str
    importance_score: float = 0.5  # 0.0 to 1.0
    access_count: int = 1
    is_consolidated: bool = False
    is_pruned: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticKnowledgeNode(BaseModel):
    node_id: str = Field(default_factory=lambda: f"node_{uuid.uuid4().hex[:8]}")
    cluster_topic: str
    distilled_heuristic: str
    source_trace_ids: List[str]
    confidence: float = 0.90
    created_at: float = Field(default_factory=time.time)
    importance_decay_rate: float = 0.05
    abstraction_level: int = 1  # 0=Raw, 1=Micro, 2=Macro, 3=Core
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryConsolidator:
    """Consolidates high-frequency episodic traces into abstract semantic knowledge."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._traces: List[EpisodicTrace] = []
        self._consolidated_nodes: List[SemanticKnowledgeNode] = []
        self._pruned_traces: List[EpisodicTrace] = []

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Memory consolidation halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: memory trace involving payments or checkout is strictly prohibited. Found: {text}"
            )

    def record_trace(
        self,
        session_id: str,
        interaction_type: str,
        content: str,
        importance_score: float = 0.5,
    ) -> EpisodicTrace:
        """Record an episodic memory trace with Rule 8 screening."""
        self._check_guardian()
        self._validate_rule_8(content)

        trace = EpisodicTrace(
            session_id=session_id,
            interaction_type=interaction_type.upper(),
            content=content,
            importance_score=max(0.0, min(1.0, importance_score)),
        )
        self._traces.append(trace)
        return trace

    def compute_decayed_importance(self, trace: EpisodicTrace, current_time: Optional[float] = None) -> float:
        """Compute exponential time decay with access count reinforcement.

        Formula: I(t) = I_0 * exp(-lambda * delta_t) * (1 + 0.1 * min(access_count, 10))
        """
        now = current_time or time.time()
        delta_hours = max(0.0, (now - trace.timestamp) / 3600.0)
        decay_rate = 0.05  # half-life ~ 14 hours
        base_decay = trace.importance_score * math.exp(-decay_rate * delta_hours)
        reinforcement = 1.0 + 0.10 * min(trace.access_count, 10)
        return round(min(1.0, base_decay * reinforcement), 4)

    def consolidate(self) -> List[SemanticKnowledgeNode]:
        """Perform consolidation pass over unconsolidated episodic traces."""
        self._check_guardian()

        unconsolidated = [t for t in self._traces if not t.is_consolidated and not t.is_pruned]
        if not unconsolidated:
            return self._consolidated_nodes

        # Group traces by topic or keywords
        clusters: Dict[str, List[EpisodicTrace]] = {}
        for t in unconsolidated:
            topic = "General Knowledge"
            content_lower = t.content.lower()
            if any(k in content_lower for k in ["python", "ast", "code", "syntax"]):
                topic = "Python & AST Conventions"
            elif any(k in content_lower for k in ["react", "vite", "hud", "ui", "typescript"]):
                topic = "Frontend Architecture"
            elif any(k in content_lower for k in ["safety", "rule", "guardian", "tier"]):
                topic = "Safety Invariants"

            clusters.setdefault(topic, []).append(t)

        new_nodes: List[SemanticKnowledgeNode] = []
        for topic, trace_group in clusters.items():
            trace_ids = [t.trace_id for t in trace_group]
            combined_content = "; ".join([t.content for t in trace_group[:3]])
            heuristic = f"Heuristic derived from {len(trace_group)} traces on {topic}: {combined_content[:80]}..."
            self._validate_rule_8(heuristic)

            node = SemanticKnowledgeNode(
                cluster_topic=topic,
                distilled_heuristic=heuristic,
                source_trace_ids=trace_ids,
                confidence=min(0.98, 0.80 + 0.04 * len(trace_group)),
                abstraction_level=1,
            )
            new_nodes.append(node)
            self._consolidated_nodes.append(node)

            for t in trace_group:
                t.is_consolidated = True

        return new_nodes

    def soft_prune_decayed(self, decay_threshold: float = 0.20, current_time: Optional[float] = None) -> List[str]:
        """Soft-prune decayed traces below importance threshold (Rule 7 non-destructibility)."""
        self._check_guardian()

        pruned_ids: List[str] = []
        now = current_time or time.time()

        for t in self._traces:
            if not t.is_pruned:
                effective_score = self.compute_decayed_importance(t, current_time=now)
                if effective_score < decay_threshold:
                    t.is_pruned = True
                    self._pruned_traces.append(t)
                    pruned_ids.append(t.trace_id)

        return pruned_ids

    def get_traces(self, include_pruned: bool = False) -> List[EpisodicTrace]:
        """Query stored episodic memory traces."""
        self._check_guardian()
        if include_pruned:
            return list(self._traces)
        return [t for t in self._traces if not t.is_pruned]

    def get_nodes(self) -> List[SemanticKnowledgeNode]:
        """Query consolidated semantic knowledge nodes."""
        self._check_guardian()
        return list(self._consolidated_nodes)


# Singleton instance
memory_consolidator = MemoryConsolidator()
