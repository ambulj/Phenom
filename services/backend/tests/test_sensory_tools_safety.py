"""
Unit Test Suite for Sensory & P2P Media Drop Safety Registry Governance (SAF-01)
Validates tool registration, risk tiers, argument models, and preview generator strings.
"""

import os
import pytest
from services.backend.safety.registry import registry
from services.backend.schemas.sensory import (
    CameraGetFrameArgs,
    CameraAnalyzeArgs,
    MediaDropSendFileArgs,
    MediaDropGetHistoryArgs,
)
import services.backend.tools.sensory_tools  # Ensure registration


def test_sensory_tools_registered_in_tool_registry():
    """SAF-01: Verify all 4 sensory and media drop tools are properly registered."""
    tool_defs = registry.list_all()
    expected = [
        "camera_get_companion_frame",
        "camera_analyze_object_or_ocr",
        "media_drop_send_file",
        "media_drop_get_history",
    ]
    for name in expected:
        assert name in tool_defs, f"Tool '{name}' missing from ToolRegistry"


def test_sensory_tools_tier_classification():
    """SAF-01: Verify strict tier assignments (Tier 0 read-only, Tier 1 reversible)."""
    assert registry.get_tier("camera_get_companion_frame") == 0
    assert registry.get_tier("camera_analyze_object_or_ocr") == 0
    assert registry.get_tier("media_drop_get_history") == 0
    assert registry.get_tier("media_drop_send_file") == 1


def test_sensory_tools_previews():
    """SAF-01: Verify preview generation functions for user transparency."""
    # Camera get frame preview
    tool_get_frame = registry.get("camera_get_companion_frame")
    assert tool_get_frame is not None
    frame_preview = tool_get_frame.generate_preview({"node_id": "phone-123"})
    assert "phone-123" in frame_preview
    assert "Read-Only" in frame_preview

    # Camera analyze preview
    tool_analyze = registry.get("camera_analyze_object_or_ocr")
    assert tool_analyze is not None
    analyze_preview = tool_analyze.generate_preview({"task_type": "ocr"})
    assert "ocr" in analyze_preview
    assert "Read-Only" in analyze_preview

    # Media drop send preview
    tool_send = registry.get("media_drop_send_file")
    assert tool_send is not None
    mock_path = "C:/Docs/Quarterly_Plan.pdf"
    drop_preview = tool_send.generate_preview(
        {"file_path": mock_path, "target_node_id": "tablet-456", "destination": "vault"}
    )
    assert "Quarterly_Plan.pdf" in drop_preview or "C:/Docs/Quarterly_Plan.pdf" in drop_preview
    assert "tablet-456" in drop_preview
    assert "vault" in drop_preview

    # Media drop history preview
    tool_hist = registry.get("media_drop_get_history")
    assert tool_hist is not None
    history_preview = tool_hist.generate_preview({"limit": 10})
    assert "Read-Only" in history_preview


@pytest.mark.asyncio
async def test_tool_execution_direct_via_registry(tmp_path):
    """SAF-01: Verify execution of registered sensory tools through registry lookup."""
    # 1. Camera get frame when empty
    tool_frame = registry.get("camera_get_companion_frame")
    assert tool_frame is not None
    args_frame = tool_frame.args_schema(node_id="test-device")
    res = await tool_frame.handler_fn(args_frame)
    assert res["status"] in ("success", "no_frame")

    # 2. Media drop history query
    tool_hist = registry.get("media_drop_get_history")
    assert tool_hist is not None
    args_hist = tool_hist.args_schema(limit=5)
    hist_res = await tool_hist.handler_fn(args_hist)
    assert hist_res["status"] == "success"
    assert "transfers" in hist_res
    assert isinstance(hist_res["transfers"], list)

    # 3. Media drop send file
    sample_file = tmp_path / "Briefing.md"
    sample_file.write_text("# Test Briefing", encoding="utf-8")
    tool_send = registry.get("media_drop_send_file")
    assert tool_send is not None
    args_send = tool_send.args_schema(
        file_path=str(sample_file),
        target_node_id="companion-dev",
        destination="vault",
    )
    send_res = await tool_send.handler_fn(args_send)
    assert send_res["status"] == "initiated"
    assert "transfer" in send_res
    assert send_res["transfer"]["filename"] == "Briefing.md"
