"""Hierarchical Memory Abstractor for Phenom (Milestone 26 Phase 1).

Organizes consolidated semantic nodes into 4 hierarchical abstraction tiers:
Level 0 (Raw Traces) -> Level 1 (Micro-Heuristics) -> Level 2 (Macro-Strategies) -> Level 3 (Core Identity) (ABS-01.1).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.consolidation.memory_consolidator import (
    SemanticKnowledgeNode,
    MemoryConsolidator,
    memory_consolidator,
    Rule8ViolationError,
)

logger = logging.getLogger("phenom.consolidation.hierarchical_abstractor")


class HierarchicalMemoryGraph(BaseModel):
    total_node_count: int
    abstraction_levels: Dict[int, List[SemanticKnowledgeNode]] = Field(default_factory=dict)
    root_topics: List[str] = Field(default_factory=list)


class HierarchicalAbstractor:
    """Manages multi-tier semantic abstraction hierarchies and graph queries."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    CORE_IDENTITY_HEURISTICS: List[Dict[str, Any]] = [
        {
            "topic": "Core Principles",
            "heuristic": "Rule 1: Always wrap tool execution in Safety layer with confirmation tiers.",
            "level": 3,
        },
        {
            "topic": "Core Principles",
            "heuristic": "Rule 4: Zero cloud telemetry egress; strictly local offline computation.",
            "level": 3,
        },
        {
            "topic": "Core Principles",
            "heuristic": "Rule 7: Reversible operations, non-destructive buffers, and soft-delete.",
            "level": 3,
        },
        {
            "topic": "Core Principles",
            "heuristic": "Rule 8: Payments are impossible by construction. Zero checkout operations.",
            "level": 3,
        },
    ]

    def __init__(self, consolidator: Optional[Any] = None) -> None:
        self._consolidator = consolidator or memory_consolidator
        self._macro_strategies: List[SemanticKnowledgeNode] = []
        self._core_nodes: List[SemanticKnowledgeNode] = [
            SemanticKnowledgeNode(
                cluster_topic=item["topic"],
                distilled_heuristic=item["heuristic"],
                source_trace_ids=["core_rule"],
                confidence=1.0,
                abstraction_level=3,
            )
            for item in self.CORE_IDENTITY_HEURISTICS
        ]

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Memory abstractor halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: memory abstraction query targeting payments is strictly prohibited. Found: {text}"
            )

    def build_graph(self) -> HierarchicalMemoryGraph:
        """Construct hierarchical memory graph from active nodes."""
        self._check_guardian()

        micro_nodes = self._consolidator.get_nodes()

        # Group micro nodes into macro strategies (Level 2) if 2 or more exist for a topic
        topic_groups: Dict[str, List[SemanticKnowledgeNode]] = {}
        for n in micro_nodes:
            topic_groups.setdefault(n.cluster_topic, []).append(n)

        level_2_nodes: List[SemanticKnowledgeNode] = []
        for topic, nodes in topic_groups.items():
            if len(nodes) >= 2:
                macro_node = SemanticKnowledgeNode(
                    cluster_topic=topic,
                    distilled_heuristic=f"Macro-Strategy for {topic}: Unified patterns across {len(nodes)} micro-heuristics.",
                    source_trace_ids=[n.node_id for n in nodes],
                    confidence=0.96,
                    abstraction_level=2,
                )
                level_2_nodes.append(macro_node)

        levels: Dict[int, List[SemanticKnowledgeNode]] = {
            1: micro_nodes,
            2: level_2_nodes,
            3: self._core_nodes,
        }

        all_topics = list({n.cluster_topic for nodes in levels.values() for n in nodes})
        total_count = sum(len(nodes) for nodes in levels.values())

        return HierarchicalMemoryGraph(
            total_node_count=total_count,
            abstraction_levels=levels,
            root_topics=all_topics,
        )

    def query_graph(self, query: str, min_level: int = 1) -> List[SemanticKnowledgeNode]:
        """Search memory hierarchy by semantic keyword match and minimum abstraction level."""
        self._check_guardian()
        self._validate_rule_8(query)

        graph = self.build_graph()
        q_tokens = set(re.findall(r"\w+", query.lower()))

        matched: List[SemanticKnowledgeNode] = []
        for lvl, nodes in graph.abstraction_levels.items():
            if lvl >= min_level:
                for node in nodes:
                    content = f"{node.cluster_topic} {node.distilled_heuristic}".lower()
                    node_tokens = set(re.findall(r"\w+", content))
                    if q_tokens.intersection(node_tokens) or any(t in content for t in q_tokens if len(t) > 3):
                        matched.append(node)

        return matched


# Singleton instance
hierarchical_abstractor = HierarchicalAbstractor()
