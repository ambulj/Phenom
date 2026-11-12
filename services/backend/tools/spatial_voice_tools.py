"""Safety-Wrapped Spatial-Voice Intent Fusion Tools.

Registers tools with ToolRegistry for cursor spatial context queries, deictic voice intent
resolution, and UI target beacon highlights (Phase 24-03 VOX-07 / GES-01).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.spatial.cursor_telemetry_tracker import cursor_telemetry_tracker
from services.backend.spatial.spatial_intent_resolver import spatial_intent_resolver


# ==========================================
# 1. Resolve Spatial Intent (Tier 0)
# ==========================================

class ResolveSpatialIntentArgs(BaseModel):
    spoken_command: str = Field(
        ...,
        description="Spoken command potentially containing deictic pronouns ('refactor this', 'explain here', 'benchmark this')",
    )


def resolve_spatial_intent_preview(args: Dict[str, Any]) -> str:
    cmd = args.get("spoken_command", "")
    return f"Resolve spatial-voice intent for spoken directive: '{cmd}' using cursor coordinates."


@registry.register(
    name="resolve_spatial_intent",
    tier=0,
    description="Correlates spoken deictic commands with active screen cursor coordinates to resolve target AST symbols or UI controls.",
    args_schema=ResolveSpatialIntentArgs,
    preview_fn=resolve_spatial_intent_preview,
    can_remember_per_folder=False,
)
def handle_resolve_spatial_intent(spoken_command: str) -> Dict[str, Any]:
    intent = spatial_intent_resolver.resolve_spatial_intent(spoken_command=spoken_command)
    return intent.model_dump()


# ==========================================
# 2. Get Cursor Spatial Context (Tier 0)
# ==========================================

class GetCursorSpatialContextArgs(BaseModel):
    pass


def get_cursor_spatial_context_preview(args: Dict[str, Any]) -> str:
    return "Query current screen cursor coordinates, active window bounds, and UI accessibility elements under focus."


@registry.register(
    name="get_cursor_spatial_context",
    tier=0,
    description="Queries real-time cursor screen coordinates, active window boundaries, and UI element context.",
    args_schema=GetCursorSpatialContextArgs,
    preview_fn=get_cursor_spatial_context_preview,
    can_remember_per_folder=False,
)
def handle_get_cursor_spatial_context() -> Dict[str, Any]:
    ctx = cursor_telemetry_tracker.get_cursor_context()
    return ctx.model_dump()


# ==========================================
# 3. Highlight Spatial Target (Tier 0)
# ==========================================

class HighlightSpatialTargetArgs(BaseModel):
    target_name: str = Field(..., description="Target AST symbol or UI control name to illuminate on screen")


def highlight_spatial_target_preview(args: Dict[str, Any]) -> str:
    tn = args.get("target_name", "target")
    return f"Display visual beacon and bounding box overlay for target '{tn}'."


@registry.register(
    name="highlight_spatial_target",
    tier=0,
    description="Broadcasts an on-screen beacon and bounding box highlight for a resolved spatial target.",
    args_schema=HighlightSpatialTargetArgs,
    preview_fn=highlight_spatial_target_preview,
    can_remember_per_folder=False,
)
def handle_highlight_spatial_target(target_name: str) -> Dict[str, Any]:
    return spatial_intent_resolver.highlight_target(target_name=target_name)
