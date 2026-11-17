"""
Phenom Multimodal Clipboard Sentinel & Data Synthesizer Tools (Milestone 51 Phase 3).

Registers:
- inspect_active_clipboard (Tier 0)
- capture_and_classify_clipboard (Tier 0)
- sync_clipboard_to_knowledge_graph (Tier 1)
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.reflex import clipboard_sentinel


class InspectActiveClipboardArgs(BaseModel):
    limit: int = Field(default=5, ge=1, le=50, description="Max history items to return")


class CaptureAndClassifyClipboardArgs(BaseModel):
    content: str = Field(description="Raw clipboard text to sanitize and classify")
    auto_mirror_kg: bool = Field(default=False, description="Whether to automatically mirror to Knowledge Graph")


class SyncClipboardToKnowledgeGraphArgs(BaseModel):
    item_id: Optional[str] = Field(default=None, description="Specific clipboard item ID, or latest if omitted")


@registry.register(
    name="inspect_active_clipboard",
    tier=0,
    description="Inspects active sanitized clipboard history and classification metadata without exposing secrets.",
    args_schema=InspectActiveClipboardArgs,
    preview_fn=lambda a: "Inspect active sanitized desktop clipboard history"
)
def inspect_active_clipboard(limit: int = 5) -> Dict[str, Any]:
    history = clipboard_sentinel.get_history(limit=limit)
    return {
        "count": len(history),
        "items": [item.model_dump() for item in history],
        "latest": history[-1].model_dump() if history else None,
    }


@registry.register(
    name="capture_and_classify_clipboard",
    tier=0,
    description="Captures clipboard content, redacts secrets (Rules 4/11), and classifies multimodal format.",
    args_schema=CaptureAndClassifyClipboardArgs,
    preview_fn=lambda a: "Capture, sanitize, and classify desktop clipboard payload"
)
def capture_and_classify_clipboard(content: str, auto_mirror_kg: bool = False) -> Dict[str, Any]:
    item = clipboard_sentinel.process_clipboard_content(content)
    kg_result = None
    if auto_mirror_kg:
        kg_result = clipboard_sentinel.mirror_to_temporal_graph(item)

    return {
        "success": True,
        "item": item.model_dump(),
        "kg_sync": kg_result,
    }


@registry.register(
    name="sync_clipboard_to_knowledge_graph",
    tier=1,
    description="Mirrors sanitized clipboard item into the Temporal Knowledge Graph database.",
    args_schema=SyncClipboardToKnowledgeGraphArgs,
    preview_fn=lambda a: f"Mirror clipboard item '{a.get('item_id') or 'latest'}' to Temporal Knowledge Graph"
)
def sync_clipboard_to_knowledge_graph(item_id: Optional[str] = None) -> Dict[str, Any]:
    if item_id:
        target = next((i for i in clipboard_sentinel._history if i.item_id == item_id), None)
    else:
        target = clipboard_sentinel.get_latest_item()

    if not target:
        return {
            "success": False,
            "error": "No clipboard item found to mirror.",
        }

    res = clipboard_sentinel.mirror_to_temporal_graph(target)
    return res
