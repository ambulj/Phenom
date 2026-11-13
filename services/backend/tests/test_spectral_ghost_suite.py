"""
Unit tests for Milestone 41 Phase 2: SPECTRAL-NEXUS & GHOST-PROTOCOL
Validates:
1. FFT signal waterfall calculation & bin frequencies.
2. 802.11 Wi-Fi & BLE device cataloging.
3. Over-the-air threat detection (Evil-Twin APs & Deauth bursts).
4. NTAPI syscall prologue hook auditing.
5. Cross-platform Linux kernel rootkit detection.
6. Unified rootkit composite threat scoring.
7. Universal Guardian kill switch (<25ms SLA) enforcement.
8. ToolRegistry registration for all 5 tools.
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.spectral_nexus import spectral_nexus
from services.backend.cyber.ghost_protocol import ghost_protocol


@pytest.fixture(autouse=True)
def ensure_guardian_active():
    guardian.resume()
    yield
    guardian.resume()


def test_fft_waterfall_generation():
    waterfall = spectral_nexus.generate_fft_waterfall(center_freq_mhz=2437.0, sample_rate_mhz=20.0, bins=32)
    assert waterfall["center_freq_mhz"] == 2437.0
    assert waterfall["sample_rate_mhz"] == 20.0
    assert waterfall["bins"] == 32
    assert len(waterfall["data_points"]) == 32
    # Verify each bin has frequency and dBm amplitude
    for dp in waterfall["data_points"]:
        assert "freq_mhz" in dp
        assert "amplitude_dbm" in dp
        assert dp["amplitude_dbm"] <= 0.0  # RF signal power in dBm is negative


def test_airwaves_scan():
    report = spectral_nexus.scan_airwaves()
    assert report["wifi_networks_count"] >= 2
    assert report["ble_devices_count"] >= 1
    # Check WPA3 AP is present
    has_wpa3 = any(net["security"] == "WPA3-SAE" for net in report["wifi_networks"])
    assert has_wpa3 is True


def test_over_the_air_threat_detection():
    threats = spectral_nexus.detect_over_the_air_threats()
    assert threats["threat_score"] > 50
    assert len(threats["evil_twins_detected"]) >= 1
    assert len(threats["deauth_bursts_detected"]) >= 1
    evil_twin = threats["evil_twins_detected"][0]
    assert evil_twin["threat_type"] == "EVIL_TWIN_ROGUE_AP"
    assert evil_twin["severity"] == "CRITICAL"


def test_ntapi_inline_hook_audit():
    res = ghost_protocol.audit_ntapi_inline_hooks()
    assert res["scanned_functions_count"] >= 6
    assert "integrity_state" in res
    assert res["findings"][0]["module"] == "ntdll.dll"


def test_linux_kernel_rootkit_audit():
    res = ghost_protocol.audit_linux_kernel_rootkits()
    assert "hidden_modules_count" in res
    assert "active_kprobes_count" in res
    assert "threat_score" in res


def test_unified_rootkit_scan():
    unified = ghost_protocol.run_unified_rootkit_scan()
    assert "composite_threat_score" in unified
    assert "duration_ms" in unified
    assert unified["verdict"] in ["BENIGN", "SUSPICIOUS"]


def test_guardian_kill_switch_sla():
    guardian.trigger("Emergency drill")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError):
        spectral_nexus.generate_fft_waterfall()
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Guardian SLA violation: {latency_ms:.3f}ms >= 25.0ms"

    t0 = time.perf_counter()
    with pytest.raises(PermissionError):
        ghost_protocol.run_unified_rootkit_scan()
    latency_ms2 = (time.perf_counter() - t0) * 1000.0

    assert latency_ms2 < 25.0, f"Guardian SLA violation: {latency_ms2:.3f}ms >= 25.0ms"


def test_spectral_ghost_tools_registered():
    import services.backend.tools.spectral_ghost_tools

    expected = [
        "scan_spectral_airwaves",
        "detect_wifi_deauth_attacks",
        "generate_sdr_waterfall",
        "audit_kernel_rootkits",
        "inspect_syscall_hooks"
    ]
    for t_name in expected:
        tool = registry.get(t_name)
        assert tool is not None, f"Tool '{t_name}' must be registered"
        assert tool.tier == 0
