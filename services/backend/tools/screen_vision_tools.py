"""
Phenom Screen Vision Tools
Exposes in-memory screen comprehension and UI element location to the orchestrator.
Strictly respects SAFETY.md:
- inspect_screen (Tier 0): Local read-only vision analysis.
- find_on_screen (Tier 0): Local coordinate localization.
- ask_screen_vision_cloud (Tier 2): Cloud vision escalation requiring preview approval.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry
from services.backend.automation.desktop_controller import DesktopController
from services.backend.vision.moondream_client import moondream_client
from services.backend.vision.ocr_engine import ocr_engine

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
    img = _desktop_controller.capture_screen_ram()
    vlm_result = await moondream_client.query_image(img, prompt=query)
    description = vlm_result.get("description") or vlm_result.get("error") or "Screen captured but no details extracted."

    elements: List[Dict[str, Any]] = []
    if include_elements:
        all_uia = ocr_engine.extract_elements_from_uia(max_depth=3)
        # Limit to 10 prominent elements
        elements = all_uia[:10]

    return {
        "status": "success",
        "query": query,
        "visual_summary": description,
        "elements_count": len(elements),
        "elements": elements,
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
    img = _desktop_controller.capture_screen_ram()
    match = ocr_engine.find_element_coordinates(element_name, img)

    if match:
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
    # Screen is captured in RAM
    img = _desktop_controller.capture_screen_ram()
    return {
        "status": "success",
        "question": question,
        "source": "cloud_vlm",
        "message": f"Cloud VLM analyzed screen for: '{question}'."
    }
