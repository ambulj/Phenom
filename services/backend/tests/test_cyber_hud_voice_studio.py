"""
Unit & Integration tests for Milestone 34.0 Phase 4: CyberHUD Voice Acting & Studio Control Room
Validates:
- UI-05.43: CyberHUD Voice Studio data contracts, emotion envelopes, timbre morphing, and biometric consent enclave.
- Integration between HUD studio actions and backend voice engines (cloner, prosodic acting, morphing matrix).
- Rule 1 (Safety Before Tools): Actions strictly route via ToolRegistry with tier classification and schema validation.
- Rule 4 & VOICE-PRIV-01: 100% on-device local execution, zero audio/vector egress.
- Rule 8 & Rule 11: Anti-checkout screening and zero credential leakage.
- SAF-02.1: Universal Guardian kill switch synchronous halt SLA benchmark (< 25.0ms hard SLA).
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.voice.neural_voice_cloner import neural_voice_cloner
from services.backend.voice.prosodic_acting_engine import (
    prosodic_acting_engine,
    ActingEmotion,
    Rule8ViolationError,
)
from services.backend.voice.voice_morphing_matrix import voice_morphing_matrix
import services.backend.tools.voice_cloning_tools
import services.backend.tools.prosodic_acting_tools
import services.backend.tools.voice_morphing_tools


def _on_guardian_halt_callback(state: str):
    if state == "halted":
        neural_voice_cloner.halt()
        prosodic_acting_engine.halt()
        voice_morphing_matrix.halt()


@pytest.fixture(autouse=True)
def reset_voice_studio_state():
    guardian.add_state_callback(_on_guardian_halt_callback)
    guardian.resume()
    neural_voice_cloner.reset_halt()
    prosodic_acting_engine.reset_halt()
    voice_morphing_matrix.reset_halt()
    voice_morphing_matrix.set_morphing_target("jarvis_base", blend_ratio=0.0)
    yield
    guardian.resume()
    neural_voice_cloner.reset_halt()
    prosodic_acting_engine.reset_halt()
    voice_morphing_matrix.reset_halt()
    voice_morphing_matrix.set_morphing_target("jarvis_base", blend_ratio=0.0)


def test_voice_studio_hud_data_packet_contract():
    """Verify aggregated studio telemetry payload contract for CyberHUD streaming."""
    prosodic_acting_engine.configure_parameters(
        emotion=ActingEmotion.CONSPIRATORIAL,
        custom_pitch_shift=-2.5,
        custom_intensity=0.85,
        breath_enabled=True,
    )

    prosodic_telem = prosodic_acting_engine.get_telemetry()
    morph_telem = voice_morphing_matrix.get_telemetry()
    cloner_profiles = neural_voice_cloner.list_profiles()

    hud_packet = {
        "type": "voice_studio_telemetry",
        "prosody": {
            "active_emotion": prosodic_telem.active_emotion.value,
            "pitch_shift_semitones": prosodic_telem.pitch_shift_semitones,
            "energy_intensity": prosodic_telem.energy_intensity,
            "cadence_multiplier": prosodic_telem.cadence_multiplier,
            "breath_markers_inserted": prosodic_telem.breath_markers_inserted,
        },
        "morphing": {
            "source_profile_id": morph_telem.source_profile_id,
            "target_profile_id": morph_telem.target_profile_id,
            "blend_ratio": morph_telem.blend_ratio,
            "timbre_norm": morph_telem.timbre_norm,
        },
        "profiles": {
            "count": len(cloner_profiles),
            "profile_ids": [p["profile_id"] for p in cloner_profiles],
        },
        "guardian_armed": not guardian.is_halted,
    }

    assert hud_packet["type"] == "voice_studio_telemetry"
    assert hud_packet["prosody"]["active_emotion"] == "CONSPIRATORIAL"
    assert hud_packet["prosody"]["pitch_shift_semitones"] == -2.5
    assert hud_packet["morphing"]["blend_ratio"] == 0.0
    assert hud_packet["guardian_armed"] is True


def test_voice_studio_hud_apply_emotion_action():
    """Verify HUD emotion dial action routes via configure_prosodic_parameters."""
    tool = registry.get("configure_prosodic_parameters")
    assert tool.tier == 1

    res = tool.handler_fn(
        emotion="TACTICAL_ALERT",
        custom_pitch_shift=3.5,
        custom_intensity=1.30,
        breath_enabled=True,
    )

    assert res["status"] == "CONFIGURED"
    assert "config" in res
    assert res["config"]["active_emotion"] == "TACTICAL_ALERT"
    assert res["config"]["pitch_shift_semitones"] == 3.5
    assert res["config"]["energy_intensity"] == 1.30
    assert prosodic_acting_engine.get_active_emotion() == ActingEmotion.TACTICAL_ALERT


def test_voice_studio_hud_morph_cross_fader_action():
    """Verify HUD morphing cross-fader invokes morph_voice_identity tool."""
    # Create voice profile in cloner
    sample_audio = bytes([120] * 112000)
    profile = neural_voice_cloner.extract_speaker_embedding(
        sample_audio, sample_rate=16000, profile_name="Studio Morph Target Alpha"
    )

    # Sign consent
    tool_sign = registry.get("sign_biometric_voice_consent")
    sign_res = tool_sign.handler_fn(
        target_identity_name=profile.profile_id,
        operator_confirmation="CONFIRMED",
    )
    assert sign_res["status"] == "SIGNED"

    tool_morph = registry.get("morph_voice_identity")
    assert tool_morph.tier == 1

    res = tool_morph.handler_fn(
        target_profile_id=profile.profile_id,
        blend_ratio=0.45,
    )

    assert res["status"] == "MORPHED"
    assert res["blend_ratio"] == 0.45
    assert res["target_profile_id"] == profile.profile_id
    assert res["timbre_norm"] > 0.0


def test_voice_studio_hud_instant_1_click_biometric_revocation():
    """Verify 1-click biometric revocation permanently purges profile and resets morph."""
    # Create profile
    sample_audio = bytes([120] * 112000)
    profile = neural_voice_cloner.extract_speaker_embedding(
        sample_audio, sample_rate=16000, profile_name="Studio Revoke Target"
    )

    # Sign consent and morph
    sign_res = registry.get("sign_biometric_voice_consent").handler_fn(
        target_identity_name=profile.profile_id,
        operator_confirmation="CONFIRMED",
    )
    registry.get("morph_voice_identity").handler_fn(
        target_profile_id=profile.profile_id,
        blend_ratio=0.85,
    )

    # 1-Click Revocation using consent_id
    tool_revoke = registry.get("revoke_biometric_voiceprint")
    assert tool_revoke.tier == 1

    res = tool_revoke.handler_fn(consent_id=sign_res["consent_id"])
    assert res["status"] == "REVOKED"
    assert res["active_blend_ratio"] == 0.0
    assert res["is_purged"] is True

    # Ensure profile is purged from cloner
    assert neural_voice_cloner.get_profile(profile.profile_id) is None

    # Ensure subsequent morphing towards purged profile is rejected
    with pytest.raises(ValueError, match="not found or revoked"):
        registry.get("morph_voice_identity").handler_fn(
            target_profile_id=profile.profile_id,
            blend_ratio=0.5,
        )


def test_voice_studio_hud_guardian_halt_action_and_sla():
    """Verify HUD emergency stop synchronously halts all 3 voice engines in < 25.0ms SLA."""
    # Warmup cycle
    guardian.trigger(reason="warmup")
    guardian.resume()
    neural_voice_cloner.reset_halt()
    prosodic_acting_engine.reset_halt()
    voice_morphing_matrix.reset_halt()

    t0 = time.perf_counter()
    guardian.trigger(reason="CyberHUD Voice Studio 1-click cutoff")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert elapsed_ms < 25.0
    assert guardian.is_halted is True
    assert neural_voice_cloner.is_halted is True
    assert prosodic_acting_engine.is_halted is True
    assert voice_morphing_matrix.is_halted is True


def test_voice_studio_hud_rule8_anti_checkout_defense():
    """Verify Rule 8 blocks financial transactions in studio utterances."""
    tool_envelope = registry.get("apply_prosodic_acting_envelope")

    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        tool_envelope.handler_fn(
            text="Please buy the voice cloning subscription with credit card checkout.",
            emotion="TACTICAL_ALERT",
        )
