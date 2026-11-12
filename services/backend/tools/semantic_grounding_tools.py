"""Safety-Wrapped Semantic Grounding Tools.

Registers tools with ToolRegistry for natural language screen coordinate grounding,
visual anchor lookups, and segmented element queries (Phase 25-01 ACT-01 / VIS-04).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.grounding.visual_segmenter import visual_segmenter
from services.backend.grounding.semantic_grounding_engine import semantic_grounding_engine


# ==========================================
# 1. Ground Screen Elements (Tier 0)
# ==========================================

class GroundScreenElementsArgs(BaseModel):
    query: str = Field(..., description="Natural language element description or directive to ground (e.g. 'search bar', 'save button')")


def ground_screen_elements_preview(args: Dict[str, Any]) -> str:
    query = args.get("query", "unspecified UI query")
    return f"Ground natural language query '{query}' to target on-screen coordinates and element bounding box."


@registry.register(
    name="ground_screen_elements",
    tier=0,
    description="Matches a natural language query or spoken directive to concrete on-screen UI coordinates and bounding boxes in < 50ms.",
    args_schema=GroundScreenElementsArgs,
    preview_fn=ground_screen_elements_preview,
    can_remember_per_folder=False,
)
def handle_ground_screen_elements(query: str) -> Dict[str, Any]:
    match = semantic_grounding_engine.ground_query(query=query)
    return match.model_dump()


# ==========================================
# 2. Locate GUI Visual Anchor (Tier 0)
# ==========================================

class LocateGuiVisualAnchorArgs(BaseModel):
    anchor_name: str = Field(..., description="Semantic anchor name to locate (e.g. 'settings_gear', 'close_button', 'run_tests')")


def locate_gui_visual_anchor_preview(args: Dict[str, Any]) -> str:
    anchor = args.get("anchor_name", "unspecified anchor")
    return f"Locate visual UI anchor '{anchor}' on active desktop screen."


@registry.register(
    name="locate_gui_visual_anchor",
    tier=0,
    description="Locates a specific named visual GUI anchor or toolbar control on the active screen.",
    args_schema=LocateGuiVisualAnchorArgs,
    preview_fn=locate_gui_visual_anchor_preview,
    can_remember_per_folder=False,
)
def handle_locate_gui_visual_anchor(anchor_name: str) -> Dict[str, Any]:
    match = semantic_grounding_engine.ground_query(query=anchor_name)
    return match.model_dump()


# ==========================================
# 3. Get Visual Grounding Map (Tier 0)
# ==========================================

class GetVisualGroundingMapArgs(BaseModel):
    pass


def get_visual_grounding_map_preview(args: Dict[str, Any]) -> str:
    return "Query full visual grounding map of segmented UI elements, bounding boxes, and roles on active screen."


@registry.register(
    name="get_visual_grounding_map",
    tier=0,
    description="Returns the complete list of segmented on-screen elements, bounding boxes, and interactive roles.",
    args_schema=GetVisualGroundingMapArgs,
    preview_fn=get_visual_grounding_map_preview,
    can_remember_per_folder=False,
)
def handle_get_visual_grounding_map() -> Dict[str, Any]:
    elements = visual_segmenter.segment_screen()
    return {
        "element_count": len(elements),
        "elements": [elem.model_dump() for elem in elements],
    }
