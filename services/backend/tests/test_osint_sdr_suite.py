"""
Unit Tests for Phenom OSINT, SDR Radio Interceptor & Binary Triage Suite.
Validates:
1. Passive DNS enumeration and attack surface graph generation
2. Certificate Transparency log parsing
3. SDR ADS-B aircraft telemetry tracking & Guardian halt
4. Sub-GHz RF environmental sensor decoding
5. Binary Shannon entropy analysis & packed detection
6. Safety Registry verification for all 5 new tools
"""

import os
import tempfile
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.osint_engine import OSINTDiscoveryEngine
from services.backend.cyber.sdr_interceptor import SDRTelemetryReceiver
from services.backend.cyber.binary_triage import BinaryTriageAnalyzer
import services.backend.tools.osint_sdr_tools as osint_tools


def test_osint_dns_enumeration():
    engine = OSINTDiscoveryEngine()
    guardian.resume()

    res = engine.enumerate_dns("localhost")
    assert res["domain"] == "localhost"
    assert "A" in res["records"]
    assert "127.0.0.1" in res["records"]["A"] or len(res["records"]["A"]) > 0


def test_attack_surface_graph_generation():
    engine = OSINTDiscoveryEngine()
    guardian.resume()

    graph_res = engine.build_attack_surface_graph("example.com")
    assert graph_res["domain"] == "example.com"
    assert len(graph_res["subdomains_found"]) > 0
    assert len(graph_res["graph"]["nodes"]) >= 2
    assert "# Attack Surface Report: example.com" in graph_res["obsidian_report"]


def test_sdr_adsb_tracking_and_guardian():
    receiver = SDRTelemetryReceiver()
    guardian.resume()

    det = receiver.detect_sdr_hardware()
    assert "supported_bands" in det
    assert "1090 MHz (ADS-B)" in det["supported_bands"]

    adsb_res = receiver.start_adsb_tracking(duration_seconds=2)
    assert adsb_res["frequency_mhz"] == 1090.0
    assert adsb_res["aircraft_tracked"] >= 1
    assert "airspace_radar" in adsb_res

    # Test Guardian kill-switch
    guardian.trigger("Emergency RF halt")
    with pytest.raises(PermissionError):
        receiver.start_adsb_tracking()

    guardian.resume()


def test_sdr_rf_sensor_decoder():
    receiver = SDRTelemetryReceiver()
    guardian.resume()

    sensor_res = receiver.decode_rf_sensor_stream(433.92)
    assert sensor_res["frequency_mhz"] == 433.92
    assert len(sensor_res["decoded_sensors"]) >= 1
    assert sensor_res["status"] == "Frames demodulated cleanly"


def test_binary_entropy_triage():
    analyzer = BinaryTriageAnalyzer()

    # Plaintext low entropy
    low_entropy = analyzer.calculate_entropy(b"A" * 1000)
    assert low_entropy == 0.0

    # High entropy pseudorandom bytes
    import os
    random_bytes = os.urandom(2048)
    high_entropy = analyzer.calculate_entropy(random_bytes)
    assert high_entropy > 7.5

    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(b"MZ\x90\x00" + b"Normal native PE binary payload string content " * 20)
        tmp_name = f.name

    try:
        triage = analyzer.triage_binary(tmp_name)
        assert triage["format"] == "PE32/PE64 (Windows)"
        assert triage["is_likely_packed"] is False
        assert triage["defensive_verdict"] == "CLEAN_NATIVE"
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def test_osint_sdr_tools_registry():
    expected = [
        ("gather_domain_osint", 0),
        ("generate_attack_surface_graph", 0),
        ("start_adsb_flight_tracker", 0),
        ("decode_rf_sensor_stream", 0),
        ("triage_binary_sections", 0),
    ]
    for tool_name, exp_tier in expected:
        meta = registry.get(tool_name)
        assert meta is not None, f"Tool {tool_name} must be registered"
        assert meta.tier == exp_tier
