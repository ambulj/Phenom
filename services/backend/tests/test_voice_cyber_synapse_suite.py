"""
Unit Tests for Conversational Cyber Voice Synapse
Milestone 43.0: Project FULL-DUPLEX JARVIS (Phase 3)
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.voice.voice_cyber_synapse import (
    voice_cyber_synapse,
    CyberVoiceIntent,
    SafeModeTargetError,
)
from services.backend.voice.prosodic_acting_engine import Rule8ViolationError
from services.backend.tools.voice_synapse_tools import (
    handle_dispatch_voice_cyber_synapse,
    handle_get_voice_synapse_status,
)


@pytest.fixture(autouse=True)
def clean_guardian_and_engine():
    guardian.resume()
    yield
    guardian.resume()


def test_intent_routing_latency_sub_100ms():
    """Verifies that voice cyber intent classification and routing completes in < 100ms SLA."""
    test_cases = [
        ("Phenom scan local network 127.0.0.1", CyberVoiceIntent.RECON, "nmap_scan_stream"),
        ("Run rootkit hunter and audit syscall table", CyberVoiceIntent.ROOTKIT, "audit_kernel_rootkits"),
        ("Check threat actors and correlate dark web intelligence", CyberVoiceIntent.THREAT_INTEL, "dark_webint"),
        ("Launch 5-stage lab mission against 192.168.1.15", CyberVoiceIntent.CHRONO_CYBER, "chrono_cyber"),
        ("Sync dual-boot vault with Kali Linux", CyberVoiceIntent.SHARED_VAULT, "shared_vault"),
    ]

    for utterance, expected_intent, expected_tool_keyword in test_cases:
        t0 = time.perf_counter()
        res = voice_cyber_synapse.dispatch_voice_command(utterance)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert res["intent"] == expected_intent.value
        assert expected_tool_keyword in res["dispatched_tool"]
        assert res["routing_latency_ms"] < 100.0, f"Routing SLA violated: {res['routing_latency_ms']}ms"
        assert res["routing_sla_met"] is True
        assert elapsed_ms < 150.0


def test_safe_mode_target_boundary_enforcement():
    """Verifies that out-of-scope targets trigger SafeModeTargetError (Rule 7)."""
    synapse = voice_cyber_synapse

    # Authorized local lab targets must pass
    valid_targets = ["127.0.0.1", "192.168.1.100", "10.0.0.5", "localhost", "testlab.local"]
    for target in valid_targets:
        assert synapse.is_safe_target(target) is True
        res = synapse.dispatch_voice_command(f"Scan target {target}")
        assert res["safe_mode_enforced"] is True

    # External unauthorized targets must be hard-blocked (SafeModeTargetError)
    unauthorized_targets = ["8.8.8.8", "1.1.1.1", "victim-corp.com", "203.0.113.5"]
    for target in unauthorized_targets:
        assert synapse.is_safe_target(target) is False
        with pytest.raises(SafeModeTargetError):
            synapse.dispatch_voice_command(f"Scan unauthorized target {target}")


def test_anti_checkout_rule_8_enforcement():
    """Verifies that voice cyber requests containing checkout or payment tokens are hard-blocked."""
    checkout_phrases = [
        "Pay for cyber reconnaissance tools online",
        "Purchase premium threat actor feed using credit card",
        "Checkout this new zero-day exploit package",
    ]

    for phrase in checkout_phrases:
        with pytest.raises(Rule8ViolationError):
            voice_cyber_synapse.dispatch_voice_command(phrase)


def test_ssml_prosodic_acting_envelope_formatting():
    """Verifies that cyber voice responses include emotional SSML prosody tags."""
    res = voice_cyber_synapse.dispatch_voice_command("Phenom run rootkit hunter")

    assert "ssml_envelope" in res
    assert "<prosody" in res["ssml_envelope"]
    assert "</prosody>" in res["ssml_envelope"]
    assert res["emotion"] in ["TACTICAL_ALERT", "WARM_WIT", "EXECUTIVE_CONCISE"]


def test_voice_synapse_tools_registration_and_execution():
    """Verifies tool registration and execution in ToolRegistry."""
    assert registry.get_tier("dispatch_voice_cyber_synapse") == 1
    assert registry.get_tier("get_voice_synapse_status") == 0

    status = handle_get_voice_synapse_status()
    assert "total_dispatches" in status
    assert "safe_subnets_count" in status

    dispatch_res = handle_dispatch_voice_cyber_synapse(
        voice_command="Sync dual-boot vault partition",
        dry_run=True,
    )
    assert dispatch_res["intent"] == CyberVoiceIntent.SHARED_VAULT.value
    assert "shared_vault" in dispatch_res["dispatched_tool"]


def test_guardian_halt_blocks_voice_dispatch():
    """Verifies that when Guardian is halted, voice cyber dispatches fail closed."""
    guardian.trigger("Simulated emergency")
    assert guardian.is_halted is True

    with pytest.raises(RuntimeError, match="Guardian Kill Switch is active"):
        voice_cyber_synapse.dispatch_voice_command("Scan local network 127.0.0.1")
