"""
Safety & Risk Tier Verification Tests for Proactive Feedback Tools (SAF-01, SAF-02).
Verifies:
- All 5 tools registered in ToolRegistry
- Tier 0 classification for proactive_get_bus_status
- Tier 1 classification for event ingestion, audio cues, and WebRTC streaming
- Guardian kill switch lockdown fails closed with PermissionError
"""

import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.proactive_feedback_tools as tools
from services.backend.proactive.event_bus import proactive_event_bus
from services.backend.ambient.feedback_synthesizer import ambient_feedback_synthesizer
from services.backend.ambient.webrtc_mirror import local_webrtc_mirror


EXPECTED_TOOLS = {
    "proactive_get_bus_status": 0,
    "proactive_ingest_event": 1,
    "ambient_trigger_audio_cue": 1,
    "webrtc_init_mirror_session": 1,
    "webrtc_terminate_mirror": 1,
}


def test_proactive_feedback_tools_registered():
    """Verify all 5 tools exist in ToolRegistry with their required risk tiers."""
    for tool_name, expected_tier in EXPECTED_TOOLS.items():
        assert tool_name in registry._tools, f"Tool '{tool_name}' must be in ToolRegistry"
        meta = registry._tools[tool_name]
        assert meta.tier == expected_tier, (
            f"Tool '{tool_name}' must have Risk Tier {expected_tier}, but got {meta.tier}"
        )
        assert meta.args_schema is not None
        assert meta.preview_fn is not None


def test_proactive_get_bus_status_tier_0():
    """Verify Tier 0 query executes cleanly."""
    res = tools.proactive_get_bus_status()
    assert res["status"] == "success"
    assert "bus_status" in res
    assert "total_events_ingested" in res["bus_status"]


def test_proactive_tier_1_execution():
    """Verify Tier 1 tools execute when Guardian is active."""
    proactive_event_bus.reset()
    ambient_feedback_synthesizer.reset()
    local_webrtc_mirror.reset()

    # Ingest event
    ev_res = tools.proactive_ingest_event(
        event_type="BACKGROUND_MILESTONE",
        process_name="test_runner",
        window_title="Phase 3 Tests",
        details={"status": "passing"},
    )
    assert ev_res["status"] == "success"
    assert ev_res["event"]["event_type"] == "BACKGROUND_MILESTONE"

    # Play cue
    cue_res = tools.ambient_trigger_audio_cue(cue_type="SUBTLE_CHIME", spatial_pan=0.2)
    assert cue_res["status"] == "success"
    assert cue_res["audio_cue"]["spatial_pan"] == 0.2

    # WebRTC session
    rtc_res = tools.webrtc_init_mirror_session(device_id="tablet_01")
    assert rtc_res["status"] == "success"
    s_id = rtc_res["session"]["session_id"]

    term_res = tools.webrtc_terminate_mirror(session_id=s_id)
    assert term_res["status"] == "success"
    assert term_res["terminated"] is True


def test_proactive_feedback_tools_guardian_lockdown():
    """Verify all Tier 1 tools are rejected under Guardian kill switch lockdown."""
    try:
        guardian.trigger("Testing proactive tools safety lockdown")
        assert guardian.is_halted is True

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            tools.proactive_ingest_event(event_type="SYSTEM_ALERT")

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            tools.ambient_trigger_audio_cue(cue_type="SUBTLE_CHIME")

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            tools.webrtc_init_mirror_session(device_id="dev")

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            tools.webrtc_terminate_mirror(session_id="any")

    finally:
        guardian.resume()
        proactive_event_bus.reset()
        ambient_feedback_synthesizer.reset()
        local_webrtc_mirror.reset()
        assert guardian.is_halted is False
