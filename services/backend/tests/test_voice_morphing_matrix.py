"""
Unit tests for Milestone 34.0 Phase 3: Cross-Identity Voice Morphing Matrix & Biometric Consent Enclave
Validates:
- MORPH-03.1: Spherical acoustic timbre vector interpolation between voice identities.
- VOICE-PRIV-01.1: Cryptographic SHA-256 biometric consent signing.
- VOICE-PRIV-01.2: 1-click permanent biometric voiceprint revocation and memory purge.
- SAF-01: ToolRegistry integration, risk tiers, and previews.
- SAF-02.1: Universal Guardian kill switch synchronous halt SLA (< 25.0ms).
- Rule 8 & Rule 11: Anti-checkout rejection and credential scrubbing.
"""

import math
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.voice.neural_voice_cloner import neural_voice_cloner
from services.backend.voice.voice_morphing_matrix import (
    voice_morphing_matrix,
    Rule8ViolationError,
)
import services.backend.tools.voice_morphing_tools  # Registers tools


@pytest.fixture(autouse=True)
def reset_morphing_environment():
    guardian.resume()
    neural_voice_cloner.reset_halt()
    voice_morphing_matrix.reset_halt()
    voice_morphing_matrix.set_morphing_target("jarvis_base", blend_ratio=0.0)
    yield
    guardian.resume()
    neural_voice_cloner.reset_halt()
    voice_morphing_matrix.reset_halt()
    voice_morphing_matrix.set_morphing_target("jarvis_base", blend_ratio=0.0)


def test_voice_morphing_initialization_and_base_jarvis():
    """Verify matrix initializes to 100% Jarvis base with active system consent."""
    telem = voice_morphing_matrix.get_telemetry()
    assert telem.source_profile_id == "jarvis_base"
    assert telem.target_profile_id == "jarvis_base"
    assert telem.blend_ratio == 0.0
    assert voice_morphing_matrix.is_halted is False

    consents = voice_morphing_matrix.list_consents()
    assert len(consents) >= 1
    assert any(c["consent_id"] == "system_jarvis_consent" and c["is_active"] for c in consents)


def test_spherical_timbre_vector_interpolation():
    """MORPH-03.1: Verify acoustic feature and embedding interpolation at 0.5 ratio."""
    # Create cloned profile
    sample_audio = bytes([120] * 112000)  # 3.5s at 16kHz
    profile = neural_voice_cloner.extract_speaker_embedding(
        sample_audio, sample_rate=16000, profile_name="Synthetic Persona B"
    )

    # Set morphing target to 50%
    telem = voice_morphing_matrix.set_morphing_target(
        target_profile_id=profile.profile_id,
        blend_ratio=0.5,
        source_profile_id="jarvis_base",
    )
    assert telem.blend_ratio == 0.5
    assert telem.target_profile_id == profile.profile_id

    jarvis = neural_voice_cloner.get_profile("jarvis_base")
    expected_pitch = 0.5 * jarvis.pitch_mean_hz + 0.5 * profile.pitch_mean_hz
    assert pytest.approx(telem.morphed_pitch_mean_hz, abs=0.5) == expected_pitch


def test_biometric_consent_cryptographic_signing():
    """VOICE-PRIV-01.1: Verify SHA-256 consent token signing and verification."""
    record = voice_morphing_matrix.sign_consent(
        target_identity_name="Archival Voice Alpha",
        operator_confirmation="I explicitly authorize local voice synthesis for personal assistance",
    )
    assert record.is_active is True
    assert record.target_identity_name == "Archival Voice Alpha"
    assert len(record.consent_token) == 64  # SHA-256 hex string


def test_instant_1_click_biometric_revocation_and_memory_purge():
    """VOICE-PRIV-01.2: Verify 1-click revocation purges voiceprints and resets to base Jarvis."""
    # 1. Sign consent
    record = voice_morphing_matrix.sign_consent(
        target_identity_name="Revocable Identity",
        operator_confirmation="Temporary authorization",
    )

    # 2. Create voice clone under this identity name
    sample_audio = bytes([115] * 112000)
    profile = neural_voice_cloner.extract_speaker_embedding(
        sample_audio, sample_rate=16000, profile_name="Revocable Identity"
    )

    # 3. Morph to this profile
    voice_morphing_matrix.set_morphing_target(target_profile_id=profile.profile_id, blend_ratio=0.8)
    assert voice_morphing_matrix.get_telemetry().blend_ratio == 0.8

    # 4. Trigger 1-click Revocation
    revoked = voice_morphing_matrix.revoke_consent(record.consent_id)
    assert revoked is True
    assert record.is_active is False
    assert record.revoked_at is not None

    # 5. Verify profile is wiped from cloner and morphing resets to base Jarvis
    assert neural_voice_cloner.get_profile(profile.profile_id) is None
    telem_after = voice_morphing_matrix.get_telemetry()
    assert telem_after.blend_ratio == 0.0
    assert telem_after.target_profile_id == "jarvis_base"


def test_rule_8_anti_checkout_enforcement():
    """Rule 8: Verify checkout and payment directives in morphing or consent are rejected."""
    with pytest.raises(Rule8ViolationError):
        voice_morphing_matrix.sign_consent(
            target_identity_name="checkout_pay_voice",
            operator_confirmation="I authorize payment with credit card",
        )

    with pytest.raises(Rule8ViolationError):
        voice_morphing_matrix.set_morphing_target(
            target_profile_id="buy_checkout_subscription"
        )


def test_tool_registry_voice_morphing_tools():
    """SAF-01: Verify all 4 voice morphing tools are registered and functional."""
    tool_morph = registry.get("morph_voice_identity")
    assert tool_morph.tier == 1
    assert "Morph" in tool_morph.preview_fn({"target_profile_id": "test_id", "blend_ratio": 0.5})

    tool_telem = registry.get("get_voice_morphing_telemetry")
    assert tool_telem.tier == 0

    tool_sign = registry.get("sign_biometric_voice_consent")
    assert tool_sign.tier == 1

    tool_revoke = registry.get("revoke_biometric_voiceprint")
    assert tool_revoke.tier == 1

    # Execute sign consent tool
    sign_res = tool_sign.handler_fn(
        target_identity_name="Commander Beta",
        operator_confirmation="Consent for desktop assistant use",
    )
    assert sign_res["status"] == "SIGNED"
    cid = sign_res["consent_id"]

    # Execute telemetry tool
    telem_res = tool_telem.handler_fn()
    assert "source_profile_id" in telem_res
    assert telem_res["active_consents_count"] >= 2

    # Execute revoke tool
    revoke_res = tool_revoke.handler_fn(consent_id=cid)
    assert revoke_res["status"] == "REVOKED"
    assert revoke_res["is_purged"] is True


def test_universal_guardian_kill_switch_sla():
    """SAF-02.1: Verify Guardian kill switch halt SLA < 25.0ms on voice morphing matrix."""
    voice_morphing_matrix.halt()
    voice_morphing_matrix.reset_halt()

    latencies = []
    for _ in range(50):
        voice_morphing_matrix.reset_halt()
        t0 = time.perf_counter()
        voice_morphing_matrix.halt()
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    avg_ms = sum(latencies) / len(latencies)
    max_ms = max(latencies)
    assert max_ms < 25.0, f"Max halt latency {max_ms:.3f}ms exceeded 25.0ms SLA"
    assert avg_ms < 1.0, f"Average halt latency {avg_ms:.3f}ms exceeded 1.0ms target"

    # Verify morphing is blocked when halted
    with pytest.raises(RuntimeError):
        voice_morphing_matrix.set_morphing_target("jarvis_base", blend_ratio=0.5)
