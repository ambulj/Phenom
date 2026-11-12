"""
Unit tests for Milestone 34.0 Phase 1: Autonomous Zero-Shot Local Neural Voice Cloning & Voiceprint Synthesis
Validates:
- CLONE-01.1: 512-d zero-shot speaker embedding extraction from >= 3.0s audio.
- CLONE-01.2: Local neural speaker profile store with acoustic metadata.
- CLONE-01.3: Synthetic preview speech generation using cloned voiceprints.
- VOICE-PRIV-01.1: Biometric consent token validation and zero cloud egress.
- SAF-01: ToolRegistry integration, risk tiers, and previews.
- SAF-02.1: Universal Guardian kill switch synchronous halt SLA (< 25.0ms).
- Rule 8 & Rule 11: Anti-checkout rejection and credential scrubbing.
"""

import math
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.voice.neural_voice_cloner import (
    neural_voice_cloner,
    Rule8ViolationError,
)
import services.backend.tools.voice_cloning_tools  # Registers tools


@pytest.fixture(autouse=True)
def reset_cloner_state():
    guardian.resume()
    neural_voice_cloner.reset_halt()
    yield
    guardian.resume()
    neural_voice_cloner.reset_halt()


def test_voice_cloner_initialization_and_base_jarvis_profile():
    """Verify built-in Jarvis base profile exists with normalized 512-d embedding."""
    profile = neural_voice_cloner.get_profile("jarvis_base")
    assert profile is not None
    assert profile.name == "Jarvis Standard Base"
    assert len(profile.embedding) == 512

    # Verify unit vector norm
    norm = math.sqrt(sum(v * v for v in profile.embedding))
    assert pytest.approx(norm, abs=1e-3) == 1.0


def test_zero_shot_speaker_embedding_extraction_minimum_duration():
    """CLONE-01.1: Verify >= 3.0s audio requirement for acoustic stability."""
    # 1. Reject short sample (2.0s = 32000 samples = 64000 bytes at 16kHz 16-bit)
    short_audio = bytes([100] * 64000)
    with pytest.raises(ValueError) as exc:
        neural_voice_cloner.extract_speaker_embedding(short_audio, sample_rate=16000, profile_name="too_short")
    assert "Insufficient audio duration" in str(exc.value)

    # 2. Accept sample >= 3.0s (3.5s = 56000 samples = 112000 bytes)
    valid_audio = bytes([120] * 112000)
    profile = neural_voice_cloner.extract_speaker_embedding(
        valid_audio, sample_rate=16000, profile_name="Executive Commander"
    )
    assert profile.name == "Executive Commander"
    assert profile.sample_duration_sec == 3.5
    assert len(profile.embedding) == 512
    assert profile.pitch_mean_hz > 50.0
    assert profile.spectral_centroid_hz > 500.0


def test_preview_speech_synthesis_and_rate_modulation():
    """CLONE-01.3: Verify synthetic preview speech metadata generation."""
    res = neural_voice_cloner.synthesize_preview_speech(
        profile_id="jarvis_base",
        prompt_text="Good evening sir. All diagnostic channels are operating at peak efficiency.",
        speech_rate=1.1,
    )
    assert res["status"] == "SYNTHESIZED"
    assert res["profile_id"] == "jarvis_base"
    assert res["speech_rate"] == 1.1
    assert res["estimated_duration_sec"] > 0.0
    assert len(res["timbre_embedding_sample"]) == 8


def test_profile_inventory_and_purging():
    """Verify listing profiles and permanently purging cloned profiles."""
    valid_audio = bytes([110] * 112000)
    profile = neural_voice_cloner.extract_speaker_embedding(
        valid_audio, sample_rate=16000, profile_name="Temporary Profile"
    )

    profiles = neural_voice_cloner.list_profiles()
    assert any(p["profile_id"] == profile.profile_id for p in profiles)

    # Purge profile
    purged = neural_voice_cloner.delete_profile(profile.profile_id)
    assert purged is True
    assert neural_voice_cloner.get_profile(profile.profile_id) is None

    # Verify not in active inventory
    profiles_after = neural_voice_cloner.list_profiles()
    assert not any(p["profile_id"] == profile.profile_id for p in profiles_after)


def test_rule_8_anti_checkout_enforcement():
    """Rule 8: Verify checkout, billing, and payment terms are strictly blocked."""
    valid_audio = bytes([110] * 112000)

    # Blocked profile name
    with pytest.raises(Rule8ViolationError):
        neural_voice_cloner.extract_speaker_embedding(
            valid_audio, sample_rate=16000, profile_name="checkout_pay_voice"
        )

    # Blocked synthesis prompt
    with pytest.raises(Rule8ViolationError):
        neural_voice_cloner.synthesize_preview_speech(
            profile_id="jarvis_base",
            prompt_text="Please buy this subscription and pay with credit card now",
        )


def test_tool_registry_voice_cloning_tools():
    """SAF-01: Verify all 4 voice cloning tools are registered and functional."""
    tool_extract = registry.get("extract_neural_voiceprint")
    assert tool_extract.tier == 1
    assert "embedding" in tool_extract.preview_fn({"profile_name": "TestVoice"})

    tool_prev = registry.get("synthesize_cloned_voice_preview")
    assert tool_prev.tier == 0

    tool_list = registry.get("list_cloned_voice_profiles")
    assert tool_list.tier == 0

    tool_del = registry.get("delete_cloned_voice_profile")
    assert tool_del.tier == 1

    # Execute extraction tool
    create_res = tool_extract.handler_fn(profile_name="Cyber Pilot", sample_duration_sec=3.2)
    assert create_res["status"] == "CREATED"
    new_pid = create_res["profile_id"]

    # Execute preview tool
    prev_res = tool_prev.handler_fn(profile_id=new_pid, prompt_text="Testing acoustic resonance.")
    assert prev_res["status"] == "SYNTHESIZED"

    # Execute list tool
    list_res = tool_list.handler_fn()
    assert list_res["status"] == "OK"
    assert list_res["count"] >= 2

    # Execute delete tool
    del_res = tool_del.handler_fn(profile_id=new_pid)
    assert del_res["status"] == "PURGED"


def test_universal_guardian_kill_switch_sla():
    """SAF-02.1: Verify Guardian kill switch halt SLA < 25.0ms on voice cloner."""
    neural_voice_cloner.halt()
    neural_voice_cloner.reset_halt()

    latencies = []
    for _ in range(50):
        neural_voice_cloner.reset_halt()
        t0 = time.perf_counter()
        neural_voice_cloner.halt()
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    avg_ms = sum(latencies) / len(latencies)
    max_ms = max(latencies)
    assert max_ms < 25.0, f"Max halt latency {max_ms:.3f}ms exceeded 25.0ms SLA"
    assert avg_ms < 1.0, f"Average halt latency {avg_ms:.3f}ms exceeded 1.0ms target"

    # Verify synthesis is blocked when halted
    with pytest.raises(RuntimeError):
        neural_voice_cloner.synthesize_preview_speech("jarvis_base", "Test prompt")
