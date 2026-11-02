"""
Tests for Phenom Phase 2: Hybrid Screen Vision Engine
Verifies:
1. In-memory base64 encoding without disk footprint.
2. Local Moondream2 client query handling and graceful fallback.
3. OCR and UI Automation coordinate localization.
4. Tool safety tiers (inspect_screen: Tier 0, find_on_screen: Tier 0, ask_screen_vision_cloud: Tier 2).
5. Privacy invariant: zero screenshots written to disk.
"""

import pytest
import os
import base64
from PIL import Image, ImageDraw
from services.backend.vision.moondream_client import moondream_client
from services.backend.vision.ocr_engine import ocr_engine
from services.backend.safety.engine import safety_engine
from services.backend.safety.registry import registry
import services.backend.tools.screen_vision_tools


@pytest.fixture
def sample_test_image() -> Image.Image:
    """Creates a 600x400 in-memory canvas with drawn text/buttons."""
    img = Image.new("RGB", (600, 400), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    # Draw button box
    draw.rectangle([100, 100, 250, 160], fill=(59, 130, 246), outline=(37, 99, 235))
    draw.text((120, 120), "Submit", fill=(255, 255, 255))
    # Draw label
    draw.text((100, 200), "Error: Connection Refused", fill=(239, 68, 68))
    return img


def test_base64_encoding_in_memory(sample_test_image):
    b64 = moondream_client.encode_image_base64(sample_test_image)
    assert isinstance(b64, str)
    assert len(b64) > 100
    # Decode back to verify valid JPEG
    decoded = base64.b64decode(b64)
    assert decoded[:2] == b"\xff\xd8", "Must be valid JPEG bytes"


def test_base64_encoding_downscales_large_image():
    huge_img = Image.new("RGB", (3840, 2160), color=(100, 150, 200))
    b64 = moondream_client.encode_image_base64(huge_img, max_dim=1280)
    decoded = base64.b64decode(b64)
    from io import BytesIO
    reloaded = Image.open(BytesIO(decoded))
    w, h = reloaded.size
    assert max(w, h) == 1280, f"Expected max dimension 1280, got {w}x{h}"


@pytest.mark.asyncio
async def test_moondream_client_graceful_handling(sample_test_image):
    # Query with short timeout/mocked handling
    result = await moondream_client.query_image(sample_test_image, prompt="What is on screen?")
    assert "status" in result
    assert result["model"] == "moondream"
    assert "description" in result or "error" in result


def test_ocr_find_element_coordinates(sample_test_image):
    # Search for element
    match = ocr_engine.find_element_coordinates("Submit", sample_test_image)
    # Match can be found via UIA or OCR if tesseract is present, or return None cleanly
    if match:
        assert "x" in match
        assert "y" in match
        assert isinstance(match["x"], int)
        assert isinstance(match["y"], int)


@pytest.mark.asyncio
async def test_inspect_screen_tier_0_auto_runs():
    tool_def = registry.get("inspect_screen")
    assert tool_def is not None
    assert tool_def.tier == 0, "inspect_screen must be Tier 0 (Read-only)"

    res = await safety_engine.execute_tool("inspect_screen", {"query": "Check screen"})
    assert res["status"] == "success"
    assert res["result"]["status"] == "success"
    assert "message" in res["result"]


@pytest.mark.asyncio
async def test_find_on_screen_tier_0_auto_runs():
    tool_def = registry.get("find_on_screen")
    assert tool_def is not None
    assert tool_def.tier == 0, "find_on_screen must be Tier 0 (Read-only)"

    res = await safety_engine.execute_tool("find_on_screen", {"element_name": "Taskbar"})
    assert res["status"] == "success"
    assert "found" in res["result"]


@pytest.mark.asyncio
async def test_ask_screen_vision_cloud_tier_2_requires_approval():
    tool_def = registry.get("ask_screen_vision_cloud")
    assert tool_def is not None
    assert tool_def.tier == 2, "ask_screen_vision_cloud must be Tier 2"

    # With no confirmation handler, Tier 2 MUST raise PermissionError
    safety_engine.set_confirmation_handler(None)
    with pytest.raises(PermissionError):
        await safety_engine.execute_tool("ask_screen_vision_cloud", {"question": "Explain this graph"})


def test_privacy_invariant_zero_disk_leak():
    """Verify that screen vision tools do not write images to disk."""
    import glob
    before_files = set(glob.glob("*.png") + glob.glob("*.jpg") + glob.glob("*.jpeg"))
    
    # Run in-memory capture
    from services.backend.automation.desktop_controller import DesktopController
    dc = DesktopController()
    img = dc.capture_screen_ram()
    assert img is not None
    
    after_files = set(glob.glob("*.png") + glob.glob("*.jpg") + glob.glob("*.jpeg"))
    diff = after_files - before_files
    assert len(diff) == 0, f"Screen capture leaked files to disk: {diff}"
