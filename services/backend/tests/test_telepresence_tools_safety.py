"""
Tests for Omni-Modal Telepresence Tool Safety Governance (SAF-01, SAF-02).
Verifies ToolRegistry registration, preview outputs, and Guardian kill switch lockdown.
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.telepresence import SensorState
from services.backend.telepresence import streaming_av_pipeline
import services.backend.tools.telepresence_tools as tp_tools


def test_telepresence_tools_registered_in_registry():
    expected_tools = {
        "telepresence_get_status": 0,
        "telepresence_set_microphone": 1,
        "telepresence_set_camera": 1,
        "telepresence_ingest_frame": 1,
    }

    for tool_name, expected_tier in expected_tools.items():
        assert tool_name in registry._tools, f"Tool {tool_name} not registered in ToolRegistry"
        assert registry._tools[tool_name].tier == expected_tier, (
            f"Tool {tool_name} has tier {registry._tools[tool_name].tier}, expected {expected_tier}"
        )


def test_telepresence_tier_0_queries_execute():
    res = tp_tools.telepresence_get_status()
    assert res["status"] == "success"
    assert "telepresence_state" in res


def test_telepresence_tier_1_controls_with_preview():
    # Verify preview functions
    mic_tool = registry._tools["telepresence_set_microphone"]
    mic_preview = mic_tool.preview_fn({"state": "ACTIVE", "gain": 1.2})
    assert "Set microphone hardware state to ACTIVE" in mic_preview
    assert "1.2x" in mic_preview

    cam_tool = registry._tools["telepresence_set_camera"]
    cam_preview = cam_tool.preview_fn({"state": "SHUTTERED", "resolution": "1920x1080"})
    assert "Set camera privacy shutter to SHUTTERED" in cam_preview
    assert "1920x1080" in cam_preview

    frame_tool = registry._tools["telepresence_ingest_frame"]
    frame_preview = frame_tool.preview_fn({"audio_rms": 0.42, "speech_probability": 0.88, "landmarks": [(0.1, 0.2)]})
    assert "Audio RMS: 0.42" in frame_preview
    assert "Rule 4" in frame_preview

    # Execute Tier 1 calls
    mic_res = tp_tools.telepresence_set_microphone(state=SensorState.ACTIVE, gain=1.2)
    assert mic_res["status"] == "success"
    assert mic_res["new_state"]["microphone_state"] == "ACTIVE"

    cam_res = tp_tools.telepresence_set_camera(state=SensorState.ACTIVE, resolution="1920x1080")
    assert cam_res["status"] == "success"
    assert cam_res["new_state"]["camera_state"] == "ACTIVE"

    frame_res = tp_tools.telepresence_ingest_frame(
        audio_rms=0.25,
        speech_probability=0.75,
        timestamp=time.time(),
        landmarks=[(0.5, 0.5)],
    )
    assert frame_res["status"] == "success"


def test_telepresence_tools_fail_closed_under_guardian_halt():
    try:
        guardian.trigger("Telepresence Safety Test Halt")

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            tp_tools.telepresence_set_microphone(state=SensorState.ACTIVE)

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            tp_tools.telepresence_set_camera(state=SensorState.ACTIVE)

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            tp_tools.telepresence_ingest_frame(
                audio_rms=0.5,
                speech_probability=0.9,
                timestamp=time.time(),
            )
    finally:
        guardian.resume()
        streaming_av_pipeline.resume()
