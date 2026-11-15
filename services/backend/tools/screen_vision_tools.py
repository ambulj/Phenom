"""
Phenom Screen Vision Tools
Exposes in-memory screen comprehension and UI element location to the orchestrator.
Strictly respects SAFETY.md:
- inspect_screen (Tier 0): Local read-only vision analysis.
- find_on_screen (Tier 0): Local coordinate localization.
- ask_screen_vision_cloud (Tier 2): Cloud vision escalation requiring preview approval.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry
from services.backend.safety.taint import taint_tracker
from services.backend.automation.desktop_controller import DesktopController
from services.backend.vision.privacy_masker import PrivacyScanFailureError
from services.backend.vision.moondream_client import moondream_client
from services.backend.vision.ocr_engine import ocr_engine
from services.backend.vision.multimodal_coordinator import multimodal_coordinator
from services.backend.vision.annotation_streamer import annotation_streamer, HudAnnotation

_desktop_controller = DesktopController()


class InspectScreenArgs(BaseModel):
    query: str = Field(
        default="Describe what is on the screen and highlight any open windows, dialogs, buttons, or errors.",
        description="Visual question or focus for the screen inspection"
    )
    include_elements: bool = Field(
        default=True,
        description="Whether to return a list of clickable UI elements and their coordinates"
    )


class FindOnScreenArgs(BaseModel):
    element_name: str = Field(
        description="Name, label, or text of the button, input, or control to locate on screen"
    )


class AskScreenVisionCloudArgs(BaseModel):
    question: str = Field(
        description="Question about the screen requiring high-precision cloud VLM comprehension"
    )


@registry.register(
    name="inspect_screen",
    tier=0,
    description="Captures the active screen in RAM and visually inspects it using local Moondream2 VLM. Describes visible windows, errors, and UI layout. Read-only.",
    args_schema=InspectScreenArgs,
    preview_fn=lambda a: f"Inspect active screen (Read-only): query='{a.get('query', 'General inspection')}'"
)
async def inspect_screen(query: str = "Describe what is on the screen and highlight any open windows, dialogs, buttons, or errors.", include_elements: bool = True) -> Dict[str, Any]:
    """Captures screen in RAM and performs visual analysis with local Moondream2."""
    try:
        img, has_changed, delta_score, masked_count = _desktop_controller.capture_screen_delta(apply_privacy=True)
    except PrivacyScanFailureError as pse:
        raise PermissionError(f"Screen inspection refused: Privacy scan failed ({pse}). Fail-closed policy active.")

    vlm_result = await moondream_client.query_image(img, prompt=query)
    description = vlm_result.get("description") or vlm_result.get("error") or "Screen captured but no details extracted."

    # Mark screen content as untrusted taint
    taint_tracker.mark_tainted("screen_vision", f"Screen inspection: {description[:100]}")

    elements: List[Dict[str, Any]] = []
    if include_elements:
        try:
            all_uia = ocr_engine.extract_elements_from_uia(max_depth=3)
        except PrivacyScanFailureError as pse:
            raise PermissionError(f"UI element inspection refused: Privacy scan failed ({pse}). Fail-closed policy active.")
        # Limit to 10 prominent elements
        elements = all_uia[:10]
        if elements:
            hud_annos = [
                HudAnnotation(
                    id=f"elem-{idx}",
                    name=e.get("name", "Element"),
                    control_type=e.get("control_type", "element"),
                    bbox=e.get("bbox", [e.get("x", 0) - 20, e.get("y", 0) - 10, 40, 20]),
                    confidence=0.95,
                    color="#0052FF"
                )
                for idx, e in enumerate(elements)
            ]
            asyncio.create_task(annotation_streamer.broadcast_annotations(hud_annos, duration_ms=4000))

    return {
        "status": "success",
        "query": query,
        "visual_summary": description,
        "elements_count": len(elements),
        "elements": elements,
        "has_changed": has_changed,
        "delta_score": round(delta_score, 4),
        "privacy_masked_windows": masked_count,
        "message": f"Screen inspection complete: {description}"
    }


@registry.register(
    name="find_on_screen",
    tier=0,
    description="Finds the exact (x, y) coordinates of a button, text input, or UI element on screen using Windows UI Automation and OCR. Read-only.",
    args_schema=FindOnScreenArgs,
    preview_fn=lambda a: f"Locate UI element on screen: '{a.get('element_name')}'"
)
async def find_on_screen(element_name: str) -> Dict[str, Any]:
    """Locates an element on screen and returns its center coordinates (x, y)."""
    try:
        img = _desktop_controller.capture_screen_ram(apply_privacy=True)
    except PrivacyScanFailureError as pse:
        raise PermissionError(f"Screen localization refused: Privacy scan failed ({pse}). Fail-closed policy active.")

    match = ocr_engine.find_element_coordinates(element_name, img)

    if match:
        taint_tracker.mark_tainted("screen_find", f"Located screen element: {element_name}")
        anno = HudAnnotation(
            id=f"find-{int(time.time() * 1000)}",
            name=element_name,
            control_type=match.get("method", "element"),
            bbox=match.get("bbox", [match["x"] - 20, match["y"] - 10, 40, 20]),
            confidence=1.0,
            color="#CCFF00"  # Acid Lime highlight for located target
        )
        asyncio.create_task(annotation_streamer.broadcast_annotations([anno], duration_ms=3000))

        return {
            "status": "success",
            "found": True,
            "element_name": element_name,
            "x": match["x"],
            "y": match["y"],
            "bbox": match.get("bbox", []),
            "method": match.get("method", "unknown"),
            "message": f"Found '{element_name}' at coordinates ({match['x']}, {match['y']})."
        }
    else:
        return {
            "status": "not_found",
            "found": False,
            "element_name": element_name,
            "message": f"Could not locate '{element_name}' on screen."
        }


@registry.register(
    name="ask_screen_vision_cloud",
    tier=2,
    description="Escalates screen comprehension to Cloud VLM (Nemotron / Claude) with sensitive region redaction. Requires Tier 2 user confirmation with preview.",
    args_schema=AskScreenVisionCloudArgs,
    preview_fn=lambda a: f"[Cloud Vision Preview] Send redacted screen image to cloud VLM for question: '{a.get('question')}'"
)
async def ask_screen_vision_cloud(question: str) -> Dict[str, Any]:
    """Cloud vision escalation gated strictly behind Tier 2 preview and approval."""
    try:
        res = await multimodal_coordinator.execute_screen_query(prompt=question, prefer_cloud=True)
    except PrivacyScanFailureError as pse:
        raise PermissionError(f"Cloud screen vision refused: Privacy scan failed ({pse}). Fail-closed policy active.")

    taint_tracker.mark_tainted("cloud_screen_vision", f"Cloud VLM screen inspection: {res.get('description', '')[:100]}")
    return {
        "status": res.get("status", "success"),
        "question": question,
        "source": res.get("source", "cloud_nemotron"),
        "model": res.get("model", "nemotron"),
        "description": res.get("description", ""),
        "fallback_engaged": res.get("fallback_engaged", False),
        "privacy_masked_windows": res.get("privacy_masked_windows", 0),
        "message": res.get("message", "Cloud vision analysis complete.")
    }



class SearchVisualMemoryArgs(BaseModel):
    query: str = Field(
        description="Natural language question or search query for what was seen on screen (e.g. 'error in terminal 15 mins ago', 'CUDA chart')"
    )
    limit: int = Field(
        default=5,
        description="Maximum number of historical matching text occurrences to return"
    )


@registry.register(
    name="search_visual_memory",
    tier=0,
    description="Searches continuous desktop visual memory for text, windows, or commands seen on screen with temporal natural language recall. Read-only.",
    args_schema=SearchVisualMemoryArgs,
    preview_fn=lambda a: f"Search visual memory (Read-only): query='{a.get('query')}' (limit={a.get('limit', 5)})"
)
async def search_visual_memory(query: str, limit: int = 5) -> Dict[str, Any]:
    """Queries local encrypted visual memory using hybrid temporal parsing and vector similarity."""
    from services.backend.vision.temporal_recall import temporal_recall_engine
    matches = temporal_recall_engine.recall(query=query, limit=limit)
    if matches:
        taint_tracker.mark_tainted("visual_memory", f"Visual memory recall: {query}")
    return {
        "status": "success",
        "query": query,
        "matches_count": len(matches),
        "matches": matches,
        "message": f"Found {len(matches)} matching visual memory records." if matches else "No matching visual history found."
    }
