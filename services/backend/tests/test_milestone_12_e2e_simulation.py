"""
Milestone 12.0 Multi-Component End-to-End Integration Simulation (SAF-01, SAF-02).
Chains:
1. Win32 Proactive Event Ingestion (PRX-01) with Real-Time Privacy Scrubbing (Rule 11)
2. Ambient Spatial Audio Feedback (FBK-01)
3. DirectComposition Holographic Spatial Canvas & Ghost Annotation Anchoring (OVR-01)
4. Offline Neuro-Symbolic Dream Memory Consolidation & Graph Compaction (DRM-01)
5. Local WebRTC Screen Streaming to Companion Device (FBK-01)
6. Universal Guardian Kill Switch Lockdown (< 25ms SLA Benchmark) (SAF-02)
7. Guardian Clean Resumption & State Recovery
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.dream_tools as dream_tools
import services.backend.tools.spatial_tools as spatial_tools
import services.backend.tools.proactive_feedback_tools as proactive_tools
from services.backend.memory.dream_engine import dream_engine
from services.backend.spatial.canvas_manager import spatial_canvas_manager
from services.backend.spatial.focus_tracker import ActiveWindowTarget, WindowRect
from services.backend.proactive.event_bus import proactive_event_bus
from services.backend.ambient.feedback_synthesizer import ambient_feedback_synthesizer
from services.backend.ambient.webrtc_mirror import local_webrtc_mirror


def test_milestone_12_full_e2e_simulation():
    """Execute complete multi-component E2E lifecycle simulation across Milestone 12."""
    # Wire Guardian state hook for Milestone 12 subsystems
    def on_guardian_state(state: str):
        if state == "halted":
            dream_engine.halt()
            spatial_canvas_manager.halt()
            proactive_event_bus.halt()
            ambient_feedback_synthesizer.halt()
            local_webrtc_mirror.halt()
        else:
            dream_engine.reset()
            spatial_canvas_manager.reset()
            proactive_event_bus.reset()
            ambient_feedback_synthesizer.reset()
            local_webrtc_mirror.reset()

    guardian.add_state_callback(on_guardian_state)

    # Ensure all subsystems are in reset, active state
    guardian.resume()
    spatial_canvas_manager.reset()
    local_webrtc_mirror.reset()

    # Step 1: Ingest Win32 Context Event with Sensitive Credentials (PRX-01, Rule 11)
    dummy_secret = "sk-proj-" + "abcdef1234567890abcdef123456"
    event_result = proactive_tools.proactive_ingest_event(
        event_type="BACKGROUND_MILESTONE",
        process_name="visual_studio_code.exe",
        pid=1024,
        window_title="Phenom IDE - Building Milestone 12",
        details={
            "status": "in_progress",
            "debug_auth": f"bearer_token: Bearer {dummy_secret}",
        },
    )
    assert event_result["status"] == "success"
    event = event_result["event"]
    assert event["is_scrubbed"] is True
    assert dummy_secret not in str(event["details"])
    print("\n[E2E Step 1] Win32 Proactive Event Ingested & Sanitized by PrivacyScrubber.")

    # Step 2: Trigger Ambient Spatial Audio Feedback (FBK-01)
    audio_result = proactive_tools.ambient_trigger_audio_cue(
        cue_type="MILESTONE_FANFARE",
        spatial_pan=0.4,
        volume=0.6,
    )
    assert audio_result["status"] == "success"
    assert audio_result["audio_cue"]["spatial_pan"] == 0.4
    print("[E2E Step 2] Ambient Spatial Audio Cue Procedurally Synthesized.")

    # Step 3: Activate Holographic Spatial Canvas & Anchor Ghost Annotation (OVR-01)
    # Inject mock IDE window for deterministic positioning
    mock_window = ActiveWindowTarget(
        hwnd=4096,
        title="Phenom IDE - Building Milestone 12",
        process_name="Code.exe",
        pid=1024,
        bounds=WindowRect(left=150, top=100, right=1430, bottom=900, width=1280, height=800),
        is_minimized=False,
        is_focused=True,
    )
    spatial_canvas_manager.focus_tracker.set_mock_window(mock_window)

    show_overlay_res = spatial_tools.spatial_show_overlay(click_through=True)
    assert show_overlay_res["status"] == "success"

    ann_res = spatial_tools.spatial_add_annotation(
        title="E2E Architecture Hint",
        content="Neuro-symbolic dream consolidation cycle ready for execution.",
        anchor="top-right",
        offset_x=25,
        offset_y=25,
        style_preset="cyber_cyan",
    )
    assert ann_res["status"] == "success"
    annotation = ann_res["annotation"]
    assert annotation["screen_x"] == 1430 - 25 - 320  # right - offset_x - card_width
    assert annotation["screen_y"] == 100 + 25         # top + offset_y
    print("[E2E Step 3] Transparent Spatial Canvas Active with Anchored Ghost Annotation.")

    # Step 4: Run Neuro-Symbolic Sleep & Dream Memory Consolidation (DRM-01)
    dream_res = dream_tools.dream_trigger_cycle(force=True, max_episodes=20)
    assert dream_res["status"] == "completed"
    report = dream_res["report"]
    assert report["cycle_id"].startswith("dream_")
    print(f"[E2E Step 4] Dream Consolidation Cycle Executed: {report['schemas_formed']} schemas synthesized.")

    # Step 5: Establish Local WebRTC Screen Mirror Stream (FBK-01)
    rtc_res = proactive_tools.webrtc_init_mirror_session(
        device_id="companion_pixel_tablet",
        fps_target=30,
        resolution="1920x1080",
    )
    assert rtc_res["status"] == "success"
    session_id = rtc_res["session"]["session_id"]
    assert len(local_webrtc_mirror.get_active_sessions()) == 1
    print("[E2E Step 5] Local WebRTC Screen Mirror Stream Active to Companion Device.")

    # Step 6: Trip Universal Guardian Kill Switch Lockdown (SAF-02)
    t0 = time.perf_counter()
    guardian.trigger("Milestone 12 E2E Universal Lockdown Test")
    halt_duration_ms = (time.perf_counter() - t0) * 1000.0

    print(f"[E2E Step 6] Guardian Kill Switch Tripped synchronously in {halt_duration_ms:.4f} ms.")
    assert halt_duration_ms < 25.0, f"Halt latency must be < 25ms SLA, got {halt_duration_ms:.4f}ms"
    assert guardian.is_halted is True

    # Assert All Invariants in Locked Down State
    assert spatial_canvas_manager.is_halted() is True
    assert len(spatial_canvas_manager.get_state().annotations) == 0
    assert spatial_canvas_manager.get_state().is_active is False
    assert len(local_webrtc_mirror.get_active_sessions()) == 0

    with pytest.raises(PermissionError):
        spatial_tools.spatial_add_annotation(title="Fail", content="Must fail")

    with pytest.raises(PermissionError):
        dream_tools.dream_trigger_cycle(force=True)

    with pytest.raises(PermissionError):
        proactive_tools.ambient_trigger_audio_cue(cue_type="SUBTLE_CHIME")

    with pytest.raises(PermissionError):
        proactive_tools.webrtc_init_mirror_session(device_id="tablet")

    print("[E2E Step 6 Verified] All subsystems immediately fail closed with zero leaks.")

    # Step 7: Guardian Resume & State Recovery
    guardian.resume()
    spatial_canvas_manager.reset()
    local_webrtc_mirror.reset()
    assert guardian.is_halted is False
    print("[E2E Step 7] Guardian Resumed: Subsystems clean and fully operational.\n")
