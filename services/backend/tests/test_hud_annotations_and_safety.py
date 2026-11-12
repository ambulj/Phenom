"""
Phenom 4.0 Phase 4 Verification Suite
Comprehensive tests for:
1. AnnotationStreamer: Live element bounding-box broadcasting and auto-clear over WebSocket.
2. Tool Annotation Integration: inspect_screen and find_on_screen HUD element broadcasting.
3. Guardian Kill Switch Synchronization: Synchronous TTS speech purge, HUD clear, and confirmation abort.
4. Multimodal Safety Audit: 4-tier risk classification, preview functions, and Rule 8 payment blocks.
"""

import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from PIL import Image

from services.backend.vision.annotation_streamer import (
    AnnotationStreamer,
    HudAnnotation,
    annotation_streamer
)
from services.backend.tools.screen_vision_tools import (
    inspect_screen,
    find_on_screen,
    ask_screen_vision_cloud
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.main import on_guardian_state_change, pending_confirmations


# =====================================================================
# 1. ANNOTATION STREAMER TESTS
# =====================================================================

def test_hud_annotation_model_validation():
    anno = HudAnnotation(
        id="elem-42",
        name="Save Settings",
        control_type="Button",
        bbox=[100, 200, 80, 32],
        confidence=0.98,
        color="#0052FF"
    )
    dumped = anno.model_dump()
    assert dumped["id"] == "elem-42"
    assert dumped["name"] == "Save Settings"
    assert dumped["control_type"] == "Button"
    assert dumped["bbox"] == [100, 200, 80, 32]
    assert dumped["color"] == "#0052FF"


@pytest.mark.asyncio
async def test_annotation_streamer_broadcast_lifecycle():
    streamer = AnnotationStreamer()
    dispatched_messages = []

    async def mock_broadcaster(msg):
        dispatched_messages.append(msg)

    streamer.register_broadcaster(mock_broadcaster)

    # 1. Broadcast annotations
    annos = [
        HudAnnotation(id="1", name="OK", bbox=[10, 10, 50, 25]),
        HudAnnotation(id="2", name="Cancel", bbox=[70, 10, 60, 25], color="#CCFF00")
    ]
    await streamer.broadcast_annotations(annos, duration_ms=2500)

    assert len(dispatched_messages) == 1
    msg1 = dispatched_messages[0]
    assert msg1["type"] == "vision.annotations"
    assert len(msg1["payload"]["annotations"]) == 2
    assert msg1["payload"]["duration_ms"] == 2500

    # 2. Clear annotations
    await streamer.clear_annotations(reason="action_done")
    assert len(dispatched_messages) == 2
    msg2 = dispatched_messages[1]
    assert msg2["type"] == "vision.clear_annotations"
    assert msg2["payload"]["reason"] == "action_done"


# =====================================================================
# 2. SCREEN VISION TOOL ANNOTATION DISPATCH TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_inspect_screen_broadcasts_annotations():
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    mock_elements = [
        {"name": "File", "control_type": "MenuItem", "bbox": [10, 10, 40, 20], "x": 30, "y": 20},
        {"name": "Edit", "control_type": "MenuItem", "bbox": [55, 10, 40, 20], "x": 75, "y": 20}
    ]

    with patch("services.backend.tools.screen_vision_tools._desktop_controller.capture_screen_delta", return_value=(img, True, 0.05, 0)):
        with patch("services.backend.tools.screen_vision_tools.moondream_client.query_image", AsyncMock(return_value={"status": "success", "description": "Menu bar visible"})):
            with patch("services.backend.tools.screen_vision_tools.ocr_engine.extract_elements_from_uia", return_value=mock_elements):
                with patch.object(annotation_streamer, "broadcast_annotations", AsyncMock()) as mock_stream:
                    res = await inspect_screen(query="Inspect menu", include_elements=True)
                    assert res["status"] == "success"
                    assert res["elements_count"] == 2
                    
                    # Verify annotations were queued for HUD broadcast
                    mock_stream.assert_called_once()
                    args = mock_stream.call_args[0]
                    annos = args[0]
                    assert len(annos) == 2
                    assert annos[0].name == "File"
                    assert annos[1].name == "Edit"


@pytest.mark.asyncio
async def test_find_on_screen_broadcasts_single_target():
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    match_data = {"x": 150, "y": 300, "bbox": [130, 290, 40, 20], "method": "ui_automation"}

    with patch("services.backend.tools.screen_vision_tools._desktop_controller.capture_screen_ram", return_value=img):
        with patch("services.backend.tools.screen_vision_tools.ocr_engine.find_element_coordinates", return_value=match_data):
            with patch.object(annotation_streamer, "broadcast_annotations", AsyncMock()) as mock_stream:
                res = await find_on_screen("Submit")
                assert res["status"] == "success"
                assert res["found"] is True
                assert res["x"] == 150
                assert res["y"] == 300

                # Verify single target was queued for HUD broadcast with Acid Lime accent
                mock_stream.assert_called_once()
                args = mock_stream.call_args[0]
                anno = args[0][0]
                assert anno.name == "Submit"
                assert anno.color == "#CCFF00"


# =====================================================================
# 3. GUARDIAN KILL SWITCH SYNCHRONIZATION TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_guardian_trigger_synchronously_halts_tts_and_hud():
    t0 = time.perf_counter()
    with patch("services.backend.voice.tts.tts_engine.stop_speech") as mock_stop_speech:
        with patch("services.backend.main.broadcast_message", AsyncMock()) as mock_broadcast:
            # Add a mock pending confirmation
            mock_fut = asyncio.Future()
            pending_confirmations["test-kill-123"] = mock_fut

            # Trigger Guardian kill switch (automatically invokes registered on_guardian_state_change callback)
            guardian.trigger(reason="e2e_verification_test")

            latency_ms = (time.perf_counter() - t0) * 1000.0

            # 1. Verify latency (< 25ms SLA)
            assert latency_ms < 25.0, f"Guardian trigger took {latency_ms:.2f}ms, exceeded 25.0ms"

            # 2. Verify TTS audio playback stopped synchronously
            assert mock_stop_speech.called is True

            # 3. Verify pending confirmation was aborted
            assert mock_fut.done() is True
            assert mock_fut.result() == ("denied", False)

            # 4. Verify kill switch state
            assert guardian.is_halted is True

            # Clean up
            guardian.resume()
            assert guardian.is_halted is False


# =====================================================================
# 4. MULTIMODAL SAFETY 4-TIER RISK CLASSIFICATION AUDIT
# =====================================================================

def test_multimodal_safety_tier_classification():
    all_tools = registry.list_all()

    # Required multimodal tools
    assert "inspect_screen" in all_tools
    assert "find_on_screen" in all_tools
    assert "ask_screen_vision_cloud" in all_tools

    # 1. inspect_screen must be Tier 0 (read-only)
    assert all_tools["inspect_screen"].tier == 0

    # 2. find_on_screen must be Tier 0 (read-only)
    assert all_tools["find_on_screen"].tier == 0

    # 3. ask_screen_vision_cloud must be Tier 2 (cloud escalation with preview)
    assert all_tools["ask_screen_vision_cloud"].tier == 2
    assert all_tools["ask_screen_vision_cloud"].preview_fn is not None

    # 4. Desktop mouse / keyboard actions must be Tier 2
    for action_tool in ["mouse_click", "mouse_double_click", "type_text", "desktop_macro_execute"]:
        if action_tool in all_tools:
            assert all_tools[action_tool].tier == 2, f"{action_tool} must be Tier 2"
            assert all_tools[action_tool].preview_fn is not None, f"{action_tool} must have a preview function"

    # 5. Rule 8: Zero payment tools exist in registry
    prohibited_keywords = ["payment", "credit_card", "pay_order", "checkout_complete", "enter_otp", "submit_card"]
    for tool_name in all_tools.keys():
        for kw in prohibited_keywords:
            assert kw != tool_name, f"Prohibited tool {tool_name} found in Safety Registry!"
