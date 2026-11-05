"""
Phenom Context Fusion Tools (CTX-01, SAF-01)
Registers tools in ToolRegistry for querying active workspace context,
inspecting multi-application categories, and clearing in-RAM context buffers.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.ambient.context_fusion import context_fusion
from services.backend.ambient.multi_app_tracker import multi_app_tracker


# =========================================================================
# Pydantic Argument Schemas
# =========================================================================

class GetActiveWorkspaceContextArgs(BaseModel):
    pass


class InspectApplicationContextArgs(BaseModel):
    category: Optional[str] = Field(
        default=None,
        description="Filter by app domain: 'ide', 'browser', 'terminal', 'notes', 'communication', or leave empty for all."
    )


class ClearWorkspaceContextArgs(BaseModel):
    pass


# =========================================================================
# Tool Implementations & Registrations
# =========================================================================

@registry.register(
    name="get_active_workspace_context",
    tier=0,
    description="Returns active foreground window, recent sanitized workspace context stream, and open application categories.",
    args_schema=GetActiveWorkspaceContextArgs,
    preview_fn=lambda a: "Inspect active multi-application workspace context"
)
async def get_active_workspace_context() -> Dict[str, Any]:
    """Retrieves current workspace context snapshot."""
    context_fusion.update_context()
    return {
        "status": "success",
        "snapshot": context_fusion.get_context_snapshot()
    }


@registry.register(
    name="inspect_application_context",
    tier=0,
    description="Lists currently running desktop applications grouped by domain (ide, browser, terminal, notes, communication).",
    args_schema=InspectApplicationContextArgs,
    preview_fn=lambda a: f"Inspect desktop applications for domain '{a.get('category', 'all')}'"
)
async def inspect_application_context(category: Optional[str] = None) -> Dict[str, Any]:
    """Inspects running desktop applications, optionally filtered by category."""
    windows = multi_app_tracker.enumerate_active_windows()
    if category:
        cat_lower = category.lower().strip()
        filtered = [w.model_dump() for w in windows if w.category == cat_lower]
    else:
        filtered = [w.model_dump() for w in windows]

    return {
        "status": "success",
        "filter_category": category or "all",
        "total_windows": len(filtered),
        "windows": filtered
    }


@registry.register(
    name="clear_workspace_context",
    tier=1,
    description="Flushes the in-RAM workspace context ring buffer.",
    args_schema=ClearWorkspaceContextArgs,
    preview_fn=lambda a: "Flush active in-RAM workspace context ring buffer"
)
async def clear_workspace_context() -> Dict[str, Any]:
    """Flushes in-RAM context ring buffer."""
    res = context_fusion.clear_context()
    return res
