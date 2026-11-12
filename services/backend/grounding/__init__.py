"""Phenom Grounding Subsystem (Milestone 25 Phase 1).

Real-Time Multi-Modal GUI Semantic Grounding & Visual Element Segmentation (ACT-01, VIS-04).
"""

from services.backend.grounding.visual_segmenter import (
    UIElementBoundingBox,
    SegmentedUIElement,
    VisualSegmenter,
    visual_segmenter,
)
from services.backend.grounding.semantic_grounding_engine import (
    SemanticGroundingMatch,
    SemanticGroundingEngine,
    semantic_grounding_engine,
)

__all__ = [
    "UIElementBoundingBox",
    "SegmentedUIElement",
    "VisualSegmenter",
    "visual_segmenter",
    "SemanticGroundingMatch",
    "SemanticGroundingEngine",
    "semantic_grounding_engine",
]
