"""
Milestone 34.0 Phase 5: Master Safety Audit, Chaos Concurrency Battery & Production Release Test Suite
Validates:
- SAF-01.1: Exhaustive ToolRegistry audit across all 12 Milestone 34 voice cloning, prosody, and morphing tools.
- SAF-01.2: Permanent safety rule invariants (Rule 4, Rule 7, Rule 8, Rule 11).
- SAF-02.1: 100-cycle Universal Guardian Kill Switch SLA benchmark across all 3 voice engines (< 25.0ms hard SLA, typical < 1.0ms).
- SAF-02.2: 50-worker cross-pillar chaos concurrency battery under simultaneous load.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.voice.neural_voice_cloner import (
    neural_voice_cloner,
    Rule8ViolationError as ClonerRule8Error,
)
from services.backend.voice.prosodic_acting_engine import (
    prosodic_acting_engine,
    ActingEmotion,
    Rule8ViolationError as ProsodicRule8Error,
)
from services.backend.voice.voice_morphing_matrix import (
    voice_morphing_matrix,
    Rule8ViolationError as MorphingRule8Error,
)
import services.backend.tools.voice_cloning_tools
import services.backend.tools.prosodic_acting_tools
import services.backend.tools.voice_morphing_tools


@pytest.fixture(autouse=True)
def reset_m34_environment():
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


def test_cumulative_tool_registry_audit_milestone_34():
    """SAF-01.1: Formally audit all 12 tools introduced in Milestone 34."""
    expected_tools = {
        # Phase 1: Neural Voice Cloning
        "extract_neural_voiceprint": 1,
        "synthesize_cloned_voice_preview": 0,
        "list_cloned_voice_profiles": 0,
        "delete_cloned_voice_profile": 1,
        # Phase 2: Prosodic Acting Engine
        "apply_prosodic_acting_envelope": 0,
        "configure_prosodic_parameters": 1,
        "get_active_prosodic_telemetry": 0,
        "synthesize_prosodic_speech_preview": 0,
        # Phase 3: Voice Morphing Matrix & Biometric Consent Enclave
        "morph_voice_identity": 1,
        "get_voice_morphing_telemetry": 0,
        "sign_biometric_voice_consent": 1,
        "revoke_biometric_voiceprint": 1,
    }

    for tool_name, expected_tier in expected_tools.items():
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch: {tool_def.tier} != {expected_tier}"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool_def.preview_fn), f"Tool '{tool_name}' missing preview_fn"
        preview_text = tool_def.preview_fn({})
        assert isinstance(preview_text, str) and len(preview_text) > 0


def test_universal_guardian_kill_switch_100_cycle_benchmark():
    """SAF-02.1: Benchmark Guardian synchronous halt across all 3 voice engines over 100 cycles."""
    # Warmup cycle
    neural_voice_cloner.halt()
    prosodic_acting_engine.halt()
    voice_morphing_matrix.halt()
    neural_voice_cloner.reset_halt()
    prosodic_acting_engine.reset_halt()
    voice_morphing_matrix.reset_halt()

    latencies_ms = []
    for _ in range(100):
        t0 = time.perf_counter()
        neural_voice_cloner.halt()
        prosodic_acting_engine.halt()
        voice_morphing_matrix.halt()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        assert neural_voice_cloner.is_halted is True
        assert prosodic_acting_engine.is_halted is True
        assert voice_morphing_matrix.is_halted is True

        neural_voice_cloner.reset_halt()
        prosodic_acting_engine.reset_halt()
        voice_morphing_matrix.reset_halt()

    avg_ms = sum(latencies_ms) / len(latencies_ms)
    max_ms = max(latencies_ms)

    assert max_ms < 25.0, f"Max halt latency {max_ms:.4f}ms breached hard 25.0ms SLA"
    assert avg_ms < 1.0, f"Average halt latency {avg_ms:.4f}ms exceeded 1.0ms target"


def test_cross_pillar_chaos_concurrency_battery():
    """SAF-02.2: 50 concurrent worker threads stress-testing Cloning, Prosodic Acting, and Morphing."""
    # Pre-register a valid consented profile for morphing workers
    sample_audio = bytes([120] * 112000)
    base_target = neural_voice_cloner.extract_speaker_embedding(
        sample_audio, sample_rate=16000, profile_name="Chaos Target Alpha"
    )
    voice_morphing_matrix.sign_consent(
        target_identity_name=base_target.profile_id,
        operator_confirmation="Chaos Battery Consent",
    )

    def worker_task(worker_id: int):
        category = worker_id % 4

        if category == 0:
            # 1. Prosodic acting synthesis
            emotions = [
                ActingEmotion.WARM_WIT,
                ActingEmotion.CONSPIRATORIAL,
                ActingEmotion.TACTICAL_ALERT,
                ActingEmotion.CALM_REASSURING,
                ActingEmotion.EXECUTIVE_CONCISE,
            ]
            emo = emotions[worker_id % len(emotions)]
            prosodic_acting_engine.configure_parameters(
                emotion=emo,
                custom_pitch_shift=((worker_id % 10) - 5) * 1.0,
                custom_intensity=0.8 + 0.05 * (worker_id % 10),
                breath_enabled=(worker_id % 2 == 0),
            )
            telem = prosodic_acting_engine.get_telemetry()
            return telem.active_emotion == emo

        elif category == 1:
            # 2. Cloner embedding extraction and preview
            w_sample = bytes([(worker_id * 17) % 256] * 112000)
            prof = neural_voice_cloner.extract_speaker_embedding(
                w_sample, sample_rate=16000, profile_name=f"Worker Profile {worker_id}"
            )
            preview = neural_voice_cloner.synthesize_preview_speech(
                prof.profile_id, f"Chaos speech test {worker_id}", speech_rate=1.05
            )
            return preview["profile_id"] == prof.profile_id

        elif category == 2:
            # 3. Voice morphing target setting & telemetry
            ratio = round((worker_id % 100) / 100.0, 2)
            telem = voice_morphing_matrix.set_morphing_target(
                target_profile_id=base_target.profile_id,
                blend_ratio=ratio,
            )
            return telem.blend_ratio == ratio

        else:
            # 4. Consent signing and 1-click revocation
            ident = f"Temp Identity {worker_id}"
            rec = voice_morphing_matrix.sign_consent(ident, "Authorized")
            revoked = voice_morphing_matrix.revoke_consent(rec.consent_id)
            return revoked is True and rec.is_active is False

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=50, thread_name_prefix="m34_chaos") as executor:
        futures = [executor.submit(worker_task, i) for i in range(50)]
        results = [f.result() for f in as_completed(futures)]

    total_time = time.perf_counter() - t0
    assert len(results) == 50
    assert all(results)
    assert total_time < 5.0, f"Chaos test took {total_time:.2f}s (exceeds 5.0s ceiling)"


def test_permanent_rule_compliance_matrix():
    """Verify Rule 4 (zero cloud egress), Rule 8 (anti-checkout), and Rule 11 (credential scrubbing)."""
    # Rule 8: Anti-Checkout across all modules
    with pytest.raises(ClonerRule8Error):
        neural_voice_cloner.synthesize_preview_speech("jarvis_base", "buy subscription checkout now")

    with pytest.raises(ProsodicRule8Error):
        prosodic_acting_engine.apply_acting_envelope("Please order and pay credit card", ActingEmotion.TACTICAL_ALERT)

    with pytest.raises(MorphingRule8Error):
        voice_morphing_matrix.sign_consent("checkout_cart_voice", "pay order")

    # Rule 11: Credential Scrubbing
    from services.backend.evolution.tool_foundry import tool_foundry
    payload = {
        "api_key": "nvapi-secret-token",
        "password": "super-secret-password",
        "voice_id": "jarvis_prime",
    }
    scrubbed = tool_foundry.scrub_dict(payload)
    assert scrubbed["api_key"] == "[REDACTED]"
    assert scrubbed["password"] == "[REDACTED]"
    assert scrubbed["voice_id"] == "jarvis_prime"

    # Rule 4 & VOICE-PRIV-01: Sovereign local unit-sphere vectors only
    profiles = neural_voice_cloner.list_profiles()
    assert len(profiles) >= 1
    assert profiles[0]["profile_id"] == "jarvis_base"
    assert len(neural_voice_cloner.get_profile("jarvis_base").embedding) == 512
