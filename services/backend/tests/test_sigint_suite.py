"""
Unit Tests for Phenom Multi-Band Radio SIGINT Suite.
Validates:
1. ACARS 131.55 MHz VHF aircraft text messaging decoder
2. APRS 144.39 MHz amateur packet radio & weather station decoder
3. ADS-B Emergency Squawk (7700, 7600, 7500) tactical alarm evaluator
4. Guardian kill-switch SLA
5. Safety Registry metadata and risk tiers
"""

import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.multiband_sigint import MultiBandSIGINTReceiver
import services.backend.tools.sigint_tools as sig_tools


def test_decode_acars_messages():
    receiver = MultiBandSIGINTReceiver()
    guardian.resume()

    res = receiver.decode_acars_stream(center_freq_mhz=131.55)
    assert res["status"] == "success"
    assert res["protocol"] == "ACARS (131.55 MHz VHF)"
    assert res["messages_decoded"] >= 2

    msg = res["messages"][0]
    assert "AI-102" in msg["flight_number"]
    assert "ETA_UPDATE" in msg["label"]
    assert "ALT 32000" in msg["text"]


def test_decode_aprs_packet_stream():
    receiver = MultiBandSIGINTReceiver()
    guardian.resume()

    res = receiver.decode_aprs_packet_stream(center_freq_mhz=144.39)
    assert res["status"] == "success"
    assert res["protocol"] == "APRS AX.25 (144.39 MHz)"
    assert res["packets_decoded"] >= 2

    station = res["packets"][0]
    assert station["callsign"] == "W3XYZ-9"
    assert station["payload_type"] == "POSITION_TELEMETRY"
    assert station["lat"] == 28.6139

    wx = res["packets"][1]
    assert wx["payload_type"] == "WEATHER_REPORT"
    assert wx["weather"]["temp_c"] == 22.4


def test_evaluate_adsb_squawks():
    receiver = MultiBandSIGINTReceiver()
    guardian.resume()

    feed = [
        {"icao": "A4C981", "callsign": "AI-102", "squawk": "7700", "altitude_ft": 14000},  # Mayday
        {"icao": "C0842F", "callsign": "6E-542", "squawk": "7600", "altitude_ft": 22000},  # NORDO
        {"icao": "112233", "callsign": "PA-28", "squawk": "1200", "altitude_ft": 4500},    # Normal VFR
    ]

    alarms = receiver.evaluate_adsb_squawks(feed)
    assert len(alarms) == 2

    # Mayday alert
    assert any(a["squawk"] == "7700" and a["severity"] == "CRITICAL" for a in alarms)
    # NORDO alert
    assert any(a["squawk"] == "7600" and a["severity"] == "HIGH" for a in alarms)
    # Normal 1200 squawk should NOT trigger alarm
    assert not any(a["squawk"] == "1200" for a in alarms)


def test_guardian_killswitch_sigint():
    receiver = MultiBandSIGINTReceiver()
    guardian.trigger("Emergency SIGINT halt")

    with pytest.raises(PermissionError):
        receiver.decode_acars_stream()

    with pytest.raises(PermissionError):
        receiver.decode_aprs_packet_stream()

    with pytest.raises(PermissionError):
        receiver.evaluate_adsb_squawks([])

    guardian.resume()


def test_sigint_tools_registry():
    expected = [
        ("decode_acars_messages", 0),
        ("decode_aprs_packets", 0),
        ("evaluate_emergency_squawks", 0),
        ("get_multiband_sigint_telemetry", 0),
    ]
    for tool_name, exp_tier in expected:
        meta = registry.get(tool_name)
        assert meta is not None, f"Tool {tool_name} must be registered"
        assert meta.tier == exp_tier
