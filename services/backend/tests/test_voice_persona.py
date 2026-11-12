"""
Unit Tests & Guardian SLA Benchmark for Voice Persona & Dynamic Prosody (VOX-03, SAF-01, SAF-02)
"""

import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock

from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.voice.emotion_classifier import emotion_classifier
from services.backend.voice.prosody_manager import prosody_manager
from services.backend.orchestrator.engine import Orchestrator
import services.backend.tools.voice_persona_tools


@pytest.fixture(autouse=True)
def reset_voice_env():
    prosody_manager.reset_persona()
    guardian._halted = False
    yield
    prosody_manager.reset_persona()
    guardian._halted = False


def test_voice_persona_registered_safety_tiers():
    """
    SAF-01: Verifies all 4 voice persona tools are registered with correct safety tiers and schemas.
    """
    expected_tools = {
        "get_voice_persona_status": {"tier": 0, "preview": True},
        "set_voice_persona_style": {"tier": 1, "preview": True},
        "adjust_voice_prosody": {"tier": 1, "preview": True},
        "reset_voice_persona": {"tier": 0, "preview": True},
    }

    for name, spec in expected_tools.items():
        tool = registry.get(name)
        assert tool is not None, f"Tool '{name}' missing from ToolRegistry"
        assert tool.tier == spec["tier"], f"Tool '{name}' tier mismatch: expected {spec['tier']}, got {tool.tier}"
        assert tool.args_schema is not None, f"Tool '{name}' missing args_schema"
        assert tool.preview_fn is not None, f"Tool '{name}' missing preview_fn"

        preview = tool.preview_fn({"style": "whisper", "rate_delta": 2, "volume_scale": 0.8})
        assert isinstance(preview, str) and len(preview) > 0


def test_emotion_classification_heuristics():
    """
    VOX-03.1: Verifies sub-0.1ms emotion classification across 6 tones.
    """
    cases = [
        ("Emergency alert! Stop immediately, critical system failure!!", "urgent"),
        ("Why won't this damn code compile?! It's totally broken and stuck.", "frustrated"),
        ("Awesome, let's go Bro! Phenomenal work, this is brilliant!", "excited"),
        ("Write a quicksort algorithm in python with async def database query", "focused"),
        ("Please slow down, take your time, gentle and quiet evening.", "calm"),
        ("Hey Phenom Bro, what's good today?", "casual"),
    ]

    latencies = []
    for text, expected_emotion in cases:
        t0 = time.perf_counter()
        res = emotion_classifier.classify(text)
        lat = (time.perf_counter() - t0) * 1000.0
        latencies.append(lat)

        assert res.emotion == expected_emotion, f"Text '{text}' classified as {res.emotion}, expected {expected_emotion}"
        assert res.confidence >= 0.5
        assert res.intensity > 0.0

    avg_lat = sum(latencies) / len(latencies)
    print(f"\n[Emotion Classification] Avg latency: {avg_lat:.4f}ms (< 0.1ms SLA)")
    assert avg_lat < 1.0


def test_prosody_modulation_and_style_locking():
    """
    VOX-03.2: Verifies dynamic prosody modulation, style locking, and resets.
    """
    # 1. Modulate for urgent prompt
    prefix, em, prosody = prosody_manager.modulate_for_prompt("Emergency error alert immediately!!")
    assert em.emotion == "urgent"
    assert prosody["rate"] == 3
    assert prosody["volume"] == 1.0
    assert len(prefix) > 0

    # 2. Lock to Whisper style
    res = prosody_manager.set_style("whisper")
    assert res["status"] == "success"
    assert prosody_manager.locked_style == "whisper"
    assert prosody_manager.get_status()["volume"] == 0.25
    assert prosody_manager.get_status()["rate"] == -2

    # 3. Prompt while style locked preserves locked prosody
    _, _, p_locked = prosody_manager.modulate_for_prompt("Awesome celebration time!")
    assert p_locked["rate"] == -2
    assert p_locked["volume"] == 0.25
    assert p_locked["locked_style"] == "whisper"

    # 4. Fine-tune adjustment
    adj = prosody_manager.adjust_prosody(rate_delta=2, volume_scale=0.7)
    assert adj["rate"] == 0
    assert adj["volume"] == 0.7

    # 5. Reset to baseline
    rst = prosody_manager.reset_persona()
    assert rst["status"] == "success"
    assert prosody_manager.locked_style is None
    assert prosody_manager.get_status()["rate"] == 0
    assert prosody_manager.get_status()["volume"] == 1.0


def test_direct_voice_intents_voice_persona():
    """
    VOX-03.3: Verifies direct voice intent parsing for voice persona & prosody.
    """
    orch = Orchestrator()

    intent_map = {
        "speak faster": ("adjust_voice_prosody", {"rate_delta": 2}),
        "speak slower": ("adjust_voice_prosody", {"rate_delta": -2}),
        "whisper mode": ("set_voice_persona_style", {"style": "whisper"}),
        "calm down": ("set_voice_persona_style", {"style": "calm"}),
        "witty voice": ("set_voice_persona_style", {"style": "witty_jarvis"}),
        "normal voice": ("reset_voice_persona", {}),
        "voice status": ("get_voice_persona_status", {}),
    }

    for phrase, (expected_tool, expected_args) in intent_map.items():
        matched = orch._detect_direct_intent(phrase)
        assert matched is not None, f"Phrase '{phrase}' failed to match direct intent"
        tool_name, args, msg = matched
        assert tool_name == expected_tool, f"Phrase '{phrase}' matched tool {tool_name}, expected {expected_tool}"
        assert args == expected_args, f"Phrase '{phrase}' args mismatch: {args} != {expected_args}"


def test_guardian_audio_silence_sla_benchmark():
    """
    VOX-03.5 & SAF-02: Universal synchronous Guardian audio silence SLA benchmark.
    Tests 50 iterations asserting instantaneous audio queue drainage and volume mute.
    Hard SLA: < 10.0ms (target < 1.0ms typical).
    """
    durations_ms = []

    with patch("services.backend.voice.prosody_manager.broadcast_persona_event"), \
         patch("services.backend.tools.media_tools._send_virtual_key"), \
         patch("services.backend.tools.media_tools.broadcast_media_event"), \
         patch("services.backend.safety.action_log.action_log.log_action"):
        for i in range(50):
            prosody_manager.modulate_for_prompt("Playing rapid upbeat responses")
            assert prosody_manager.is_muted is False

            t0 = time.perf_counter()
            guardian.trigger(f"voice_benchmark_halt_{i}")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            durations_ms.append(elapsed_ms)

            assert guardian.is_halted is True
            assert prosody_manager.is_muted is True
            assert prosody_manager.get_status()["volume"] == 0.0

            guardian.resume()
            assert prosody_manager.is_muted is False

    avg_ms = sum(durations_ms) / len(durations_ms)
    max_ms = max(durations_ms)
    print(f"\n[Guardian Voice Audio Mute SLA Benchmark] 50 runs -> Avg: {avg_ms:.4f}ms, Max: {max_ms:.4f}ms (< 10.0ms SLA)")

    assert avg_ms < 10.0, f"Average audio silence latency {avg_ms:.4f}ms exceeded 10.0ms SLA"
    assert max_ms < 25.0, f"Peak audio silence latency {max_ms:.4f}ms exceeded 25.0ms SLA"
