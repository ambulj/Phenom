"""Phenom Memory Consolidation Subsystem (Milestone 26 Phase 1).

Episodic Long-Horizon Memory Consolidation & Hierarchical Abstraction (MEM-06, ABS-01).
"""

from services.backend.consolidation.memory_consolidator import (
    EpisodicTrace,
    SemanticKnowledgeNode,
    MemoryConsolidator,
    memory_consolidator,
)
from services.backend.consolidation.hierarchical_abstractor import (
    HierarchicalMemoryGraph,
    HierarchicalAbstractor,
    hierarchical_abstractor,
)

__all__ = [
    "EpisodicTrace",
    "SemanticKnowledgeNode",
    "MemoryConsolidator",
    "memory_consolidator",
    "HierarchicalMemoryGraph",
    "HierarchicalAbstractor",
    "hierarchical_abstractor",
]
