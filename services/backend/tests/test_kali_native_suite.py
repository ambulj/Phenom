"""
Unit tests for Milestone 41 Phase 1: Deep Native Kali Toolchain Suite
Validates:
1. Safe-Mode target boundary enforcement (RFC1918 allowed, public IPs blocked).
2. Metasploit RPC client execution and safe simulation.
3. Nmap XML streaming orchestrator and XML element parser.
4. TShark packet dissection and Rule 11 credential redaction.
5. Aircrack-ng wireless CSV parsing and deauth anomaly detection.
6. Universal Guardian kill switch (<25ms SLA) enforcement.
7. ToolRegistry registration and risk tiers.
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.kali_native_suite import (
    KaliNativeSuite,
    SafeModeTargetError,
    kali_suite
)


@pytest.fixture(autouse=True)
def ensure_guardian_active():
    guardian.resume()
    yield
    guardian.resume()


def test_safe_mode_target_validation():
    suite = KaliNativeSuite()
    # Safe targets
    assert suite.is_safe_target("127.0.0.1") is True
    assert suite.is_safe_target("localhost") is True
    assert suite.is_safe_target("::1") is True
    assert suite.is_safe_target("192.168.1.100") is True
    assert suite.is_safe_target("10.10.10.5") is True
    assert suite.is_safe_target("172.16.5.20") is True
    assert suite.is_safe_target("testlab.local") is True

    # Unsafe public targets
    assert suite.is_safe_target("8.8.8.8") is False
    assert suite.is_safe_target("1.1.1.1") is False
    assert suite.is_safe_target("example.com") is False
    assert suite.is_safe_target("https://target.com/login") is False


def test_metasploit_rpc_adapter_and_safe_mode():
    suite = KaliNativeSuite()
    # Out of scope host should raise SafeModeTargetError
    with pytest.raises(SafeModeTargetError):
        suite.query_metasploit_rpc("core.version", rpc_host="198.51.100.1")

    # Safe host should return structured response (either connected or simulated)
    resp = suite.query_metasploit_rpc("core.version", rpc_host="127.0.0.1")
    assert resp["status"] in ["connected", "emulated"]
    assert "version" in resp["result"] or "status" in resp["result"]


def test_nmap_xml_stream_parsing():
    suite = KaliNativeSuite()
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap">
<host>
    <status state="up"/>
    <address addr="127.0.0.1" addrtype="ipv4"/>
    <ports>
        <port protocol="tcp" portid="443">
            <state state="open"/>
            <service name="https" product="OpenSSL" version="3.0"/>
            <script id="ssl-cert" output="CommonName: Phenom Local Node"/>
        </port>
    </ports>
</host>
</nmaprun>
"""
    parsed = suite.parse_nmap_xml(xml_data)
    assert parsed["scanner"] == "nmap"
    assert parsed["host_count"] == 1
    host = parsed["hosts"][0]
    assert host["status"] == "up"
    assert host["addresses"]["ipv4"] == "127.0.0.1"
    assert len(host["ports"]) == 1
    port = host["ports"][0]
    assert port["port"] == 443
    assert port["service"]["product"] == "OpenSSL"
    assert port["scripts"][0]["id"] == "ssl-cert"


def test_tshark_capture_and_credential_redaction():
    suite = KaliNativeSuite()
    raw_output = "1\t1700000000.1\t192.168.1.10\t192.168.1.20\tHTTP\t120\tPOST /login HTTP/1.1 password=supersecretpass&user=admin Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\n"
    packets = suite._parse_tshark_fields(raw_output)
    assert len(packets) == 1
    pkt = packets[0]
    assert pkt["frame"] == 1
    assert "supersecretpass" not in pkt["info"]
    assert "password=[REDACTED]" in pkt["info"]
    assert "Bearer [REDACTED]" in pkt["info"]


def test_aircrack_csv_parsing_and_deauth():
    suite = KaliNativeSuite()
    csv_sample = """BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key
AA:BB:CC:DD:EE:FF, 2026-11-13 10:00:00, 2026-11-13 10:05:00, 1, 54, WPA2, CCMP, PSK, -35, 50, 10, 0.0.0.0, 10, TARGET-LAB, 

Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs
00:11:22:33:44:55, 2026-11-13 10:01:00, 2026-11-13 10:05:00, -40, 850, AA:BB:CC:DD:EE:FF, TARGET-LAB
"""
    result = suite.parse_airodump_csv(csv_sample)
    assert len(result["access_points"]) == 1
    assert result["access_points"][0]["essid"] == "TARGET-LAB"
    assert len(result["connected_clients"]) == 1
    assert result["detected_deauth_anomalies"] >= 1
    assert result["is_airspace_under_attack"] is True


def test_guardian_kill_switch_sla():
    suite = KaliNativeSuite()
    guardian.trigger("Emergency drill")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError):
        suite.execute_nmap_stream("127.0.0.1")
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Guardian SLA violation: {latency_ms:.3f}ms >= 25.0ms"


def test_kali_native_tools_registered():
    import services.backend.tools.kali_native_tools

    expected_tools = [
        "execute_native_nmap_stream",
        "query_metasploit_rpc",
        "stream_tshark_capture",
        "audit_aircrack_monitors"
    ]
    for t_name in expected_tools:
        tool = registry.get(t_name)
        assert tool is not None, f"Tool '{t_name}' must be registered"
        assert tool.tier in [0, 1], f"Tool '{t_name}' must be Tier 0 or 1"
