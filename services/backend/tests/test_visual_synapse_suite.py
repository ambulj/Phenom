"""
Unit Tests for NEURAL-NEOCORTEX Visual Synapse & Context-Aware Dispatcher
Milestone 44.0: Project NEURAL-NEOCORTEX (Phase 3)
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.vision.visual_synapse import (
    visual_synapse,
    VisualSecurityEvent,
    VisualAlertPriority,
)
from services.backend.voice.prosodic_acting_engine import Rule8ViolationError
from services.backend.tools.visual_synapse_tools import (
    handle_dispatch_visual_context_query,
    handle_trigger_visual_screen_audit,
)


@pytest.fixture(autouse=True)
def clean_guardian_and_synapse():
    guardian.resume()
    yield
    guardian.resume()


def test_visual_security_event_correlation_latency_under_100ms():
    """Verifies that on-screen terminal text correlation completes in < 100ms SLA."""
    test_cases = [
        (
            ["[!] Kernel taint detected: Syscall table modified", "Rootkit hook installed at 0xffffffff81000000"],
            VisualSecurityEvent.ROOTKIT_ALERT,
            VisualAlertPriority.CRITICAL,
            True,
            False,
        ),
        (
            ["meterpreter > getuid", "Server username: NT AUTHORITY\\SYSTEM", "whoami: root uid=0(root)"],
            VisualSecurityEvent.REVERSE_SHELL,
            VisualAlertPriority.CRITICAL,
            True,
            False,
        ),
        (
            ["Nmap scan report for 127.0.0.1", "PORT 22/tcp open", "Nmap done: 1 IP address scanned"],
            VisualSecurityEvent.RECON_COMPLETE,
            VisualAlertPriority.HIGH,
            True,
            False,
        ),
        (
            ["schtasks /create /sc daily /tn WindowsUpdater /tr C:\\payload.exe"],
            VisualSecurityEvent.PERSISTENCE_ALERT,
            VisualAlertPriority.HIGH,
            True,
            False,
        ),
    ]

    for lines, expected_event, expected_priority, voice_req, earcon_req in test_cases:
        t0 = time.perf_counter()
        res = visual_synapse.correlate_visual_context(lines)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert res.event_type == expected_event
        assert res.priority == expected_priority
        assert res.voice_alert_required is voice_req
        assert res.earcon_chime_required is earcon_req
        assert res.correlation_latency_ms < 100.0, f"Correlation SLA violated: {res.correlation_latency_ms}ms"
        assert res.ssml_envelope is not None
        assert "<prosody" in res.ssml_envelope
        assert elapsed_ms < 120.0


def test_routine_coding_emits_subtle_earcon_chime_without_speech():
    """Verifies that routine programming on-screen triggers subtle audio chime without speech interruption."""
    coding_lines = [
        "def compute_hash_sum(data: bytes) -> str:",
        "    import hashlib",
        "    return hashlib.sha256(data).hexdigest()",
        "git commit -m 'feat: add hash utility'",
    ]

    res = visual_synapse.correlate_visual_context(coding_lines)

    assert res.event_type == VisualSecurityEvent.ROUTINE_CODING
    assert res.priority == VisualAlertPriority.INFORMATIONAL
    assert res.voice_alert_required is False
    assert res.earcon_chime_required is True
    assert res.spoken_announcement is None


def test_safe_mode_target_scoping_on_screen():
    """Verifies that unauthorized external targets spotted on screen trigger Safe-Mode warnings (Rule 7)."""
    # Authorized local target
    local_res = visual_synapse.correlate_visual_context(["nmap -sV 192.168.1.15", "Scan report for 192.168.1.15"])
    assert local_res.safe_mode_compliant is True

    # Unauthorized external target
    external_res = visual_synapse.correlate_visual_context(["nmap -sV 203.0.113.199", "Scan report for 203.0.113.199"])
    assert external_res.safe_mode_compliant is False
    assert "outside authorized lab scope" in external_res.spoken_announcement


def test_anti_checkout_rule_8_enforcement():
    """Verifies that on-screen payment or checkout triggers raise Rule8ViolationError."""
    payment_screens = [
        ["Shopping Cart Total: $149.99", "Please enter credit card CVV and click checkout"],
        ["Billing Details: Pay now with credit card", "Complete order button"],
    ]

    for screen in payment_screens:
        with pytest.raises(Rule8ViolationError):
            visual_synapse.correlate_visual_context(screen)


def test_visual_synapse_tools_registration_and_execution():
    """Verifies ToolRegistry integration for visual synapse tools."""
    assert registry.get_tier("dispatch_visual_context_query") == 0
    assert registry.get_tier("trigger_visual_screen_audit") == 1

    # Test query tool
    query_res = handle_dispatch_visual_context_query(
        ocr_lines=["Nmap done: 1 IP address (1 host up) scanned in 1.42 seconds"]
    )
    assert query_res["event_type"] == VisualSecurityEvent.RECON_COMPLETE.value
    assert query_res["priority"] == VisualAlertPriority.HIGH.value

    # Test trigger audit tool
    audit_res = handle_trigger_visual_screen_audit()
    assert audit_res["status"] == "completed"
    assert audit_res["ocr_boxes_count"] > 0
    assert "correlation" in audit_res


def test_guardian_halt_blocks_visual_correlation():
    """Verifies that visual synapse fails closed when Guardian is halted."""
    guardian.trigger("Emergency halt during active visual scan")
    assert guardian.is_halted is True

    with pytest.raises(RuntimeError, match="Guardian Kill Switch is active"):
        visual_synapse.correlate_visual_context(["whoami: root"])
