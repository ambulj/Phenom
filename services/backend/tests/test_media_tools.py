import time
import pytest
from unittest.mock import patch, MagicMock
from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.tools.media_tools import (
    play_media,
    pause_media,
    resume_media,
    next_track,
    set_volume,
    get_playback_status,
    control_media,
    _current_media_state
)
from services.backend.orchestrator.engine import orchestrator

# -------------------------------------------------------------
# 1. Safety Tiers & Tool Registry Verification (MED-01, SAF-01)
# -------------------------------------------------------------
def test_media_tools_registered_safety_tiers():
    play_tool = registry.get("play_media")
    assert play_tool is not None
    assert play_tool.tier == 1, "play_media must be Tier 1 with confirmation preview"

    for t0_name in ("pause_media", "resume_media", "next_track", "set_volume", "get_playback_status", "control_media"):
        tool = registry.get(t0_name)
        assert tool is not None, f"Tool '{t0_name}' must be registered"
        assert tool.tier == 0, f"Transient transport tool '{t0_name}' must be Tier 0 to avoid voice confirmation deadlock"

# -------------------------------------------------------------
# 2. Tool Execution & State Transitions
# -------------------------------------------------------------
def test_play_media_execution():
    with patch("services.backend.tools.media_tools.broadcast_media_event") as mock_broadcast:
        res = play_media(query="baarishein", platform="youtube")
        assert res["status"] == "success"
        assert res["query"] == "baarishein"
        assert res["platform"] == "youtube"
        assert _current_media_state["state"] == "playing"
        assert _current_media_state["query"] == "baarishein"
        mock_broadcast.assert_called_once()
        args = mock_broadcast.call_args[0]
        assert args[0] == "MEDIA_PLAY"
        assert args[1]["query"] == "baarishein"

def test_play_media_spotify():
    with patch("services.backend.tools.media_tools.broadcast_media_event") as mock_broadcast:
        res = play_media(query="interstellar theme", platform="spotify")
        assert res["status"] == "success"
        assert res["platform"] == "spotify"
        assert _current_media_state["platform"] == "spotify"
        mock_broadcast.assert_called_once()
        args = mock_broadcast.call_args[0]
        assert args[0] == "MEDIA_PLAY"
        assert args[1]["platform"] == "spotify"

def test_play_media_empty_query():
    res = play_media(query="   ")
    assert res["status"] == "error"

def test_pause_and_resume_media():
    with patch("services.backend.tools.media_tools.broadcast_media_event") as mock_broadcast, \
         patch("services.backend.tools.media_tools._send_virtual_key") as mock_vk:
        res_pause = pause_media()
        assert res_pause["status"] == "success"
        assert _current_media_state["state"] == "paused"
        mock_broadcast.assert_called_with("MEDIA_PAUSE", {})
        mock_vk.assert_called_once()

        mock_broadcast.reset_mock()
        mock_vk.reset_mock()

        res_resume = resume_media()
        assert res_resume["status"] == "success"
        assert _current_media_state["state"] == "playing"
        mock_broadcast.assert_called_with("MEDIA_RESUME", {})
        mock_vk.assert_called_once()

def test_next_track():
    with patch("services.backend.tools.media_tools.broadcast_media_event") as mock_broadcast, \
         patch("services.backend.tools.media_tools._send_virtual_key") as mock_vk:
        res = next_track()
        assert res["status"] == "success"
        mock_broadcast.assert_called_with("MEDIA_NEXT", {})
        mock_vk.assert_called_once()

def test_set_volume_bounds():
    with patch("services.backend.tools.media_tools.broadcast_media_event") as mock_broadcast:
        res = set_volume(level=65)
        assert res["status"] == "success"
        assert res["level"] == 65
        assert _current_media_state["volume"] == 65
        mock_broadcast.assert_called_with("MEDIA_VOLUME", {"volume": 65})

        # Test upper clamp
        res_high = set_volume(level=150)
        assert res_high["level"] == 100
        assert _current_media_state["volume"] == 100

        # Test lower clamp
        res_low = set_volume(level=-20)
        assert res_low["level"] == 0
        assert _current_media_state["volume"] == 0

def test_get_playback_status():
    res = get_playback_status()
    assert res["status"] == "success"
    assert "playback" in res
    assert "state" in res["playback"]
    assert "volume" in res["playback"]

def test_control_media_backward_compatibility():
    with patch("services.backend.tools.media_tools.pause_media") as mock_p, \
         patch("services.backend.tools.media_tools.resume_media") as mock_r, \
         patch("services.backend.tools.media_tools.next_track") as mock_n:
        control_media("pause")
        mock_p.assert_called_once()

        control_media("resume")
        mock_r.assert_called_once()

        control_media("next")
        mock_n.assert_called_once()

# -------------------------------------------------------------
# 3. Direct Intent Interception Verification (MED-01)
# -------------------------------------------------------------
def test_direct_media_intents():
    # Play intents
    res_yt = orchestrator._detect_direct_intent("play baarishein on yt")
    assert res_yt is not None
    assert res_yt[0] == "play_media"
    assert res_yt[1]["query"] == "baarishein"
    assert res_yt[1]["platform"] == "youtube"

    res_sp = orchestrator._detect_direct_intent("play lofi beats on spotify")
    assert res_sp is not None
    assert res_sp[0] == "play_media"
    assert res_sp[1]["query"] == "lofi beats"
    assert res_sp[1]["platform"] == "spotify"

    # Transport controls
    res_pause = orchestrator._detect_direct_intent("pause music")
    assert res_pause is not None
    assert res_pause[0] == "pause_media"

    res_resume = orchestrator._detect_direct_intent("resume music")
    assert res_resume is not None
    assert res_resume[0] == "resume_media"

    res_next = orchestrator._detect_direct_intent("next song")
    assert res_next is not None
    assert res_next[0] == "next_track"

    # Volume intent
    res_vol = orchestrator._detect_direct_intent("volume 75")
    assert res_vol is not None
    assert res_vol[0] == "set_volume"
    assert res_vol[1]["level"] == 75

# -------------------------------------------------------------
# 4. Guardian Audio Mute SLA Benchmark (< 10ms SLA, SAF-02)
# -------------------------------------------------------------
def test_guardian_audio_mute_sla_benchmark():
    """
    Asserts that triggering the Guardian kill switch synchronously mutes audio
    and updates media state well under the 10.0ms SLA (< 1.0ms typical).
    """
    from services.backend.tools.media_tools import _on_guardian_media_halt

    durations = []
    with patch("services.backend.tools.media_tools._send_virtual_key"), \
         patch("services.backend.tools.media_tools.broadcast_media_event"):
        for _ in range(50):
            t0 = time.perf_counter()
            _on_guardian_media_halt("test_killswitch_sla")
            t_elapsed_ms = (time.perf_counter() - t0) * 1000.0
            durations.append(t_elapsed_ms)

    avg_ms = sum(durations) / len(durations)
    max_ms = max(durations)
    print(f"\n[Guardian Audio Mute SLA] 50 runs: avg = {avg_ms:.4f}ms, max = {max_ms:.4f}ms")

    assert max_ms < 10.0, f"Guardian audio silence response max exceeded 10ms SLA: {max_ms:.4f}ms"
    assert _current_media_state["muted"] is True
    assert _current_media_state["state"] == "paused"
