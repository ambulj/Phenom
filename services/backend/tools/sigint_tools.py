"""
Phenom Multi-Band Radio SIGINT Tool Suite
Registers:
1. decode_acars_messages (Tier 0) - Decodes VHF 131.55 MHz ACARS aircraft dispatch messages
2. decode_aprs_packets (Tier 0) - Demodulates VHF 144.39 MHz APRS AX.25 ham radio telemetry
3. evaluate_emergency_squawks (Tier 0) - Flags transponder squawks 7700 (Mayday), 7600 (NORDO), 7500 (Hijack)
4. get_multiband_sigint_telemetry (Tier 0) - Returns aggregated multi-band radio intelligence
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.multiband_sigint import multiband_sigint


# 1. ACARS Messages
class ACARSArgs(BaseModel):
    center_freq_mhz: float = Field(default=131.55, description="VHF center frequency in MHz (defaults to 131.55)")

@registry.register(
    name="decode_acars_messages",
    tier=0,
    description="Demodulates and parses ACARS VHF aircraft text messages (flight numbers, weather reports, gate updates).",
    args_schema=ACARSArgs,
    preview_fn=lambda a: f"Demodulate ACARS aircraft text messages on {a.get('center_freq_mhz', 131.55)} MHz",
    can_remember_per_folder=False
)
def decode_acars_messages(center_freq_mhz: float = 131.55) -> Dict[str, Any]:
    return multiband_sigint.decode_acars_stream(center_freq_mhz=center_freq_mhz)


# 2. APRS Packets
class APRSArgs(BaseModel):
    center_freq_mhz: float = Field(default=144.39, description="VHF center frequency in MHz (defaults to 144.39)")

@registry.register(
    name="decode_aprs_packets",
    tier=0,
    description="Demodulates APRS AX.25 packet radio frames for GPS station beacons and amateur weather telemetry.",
    args_schema=APRSArgs,
    preview_fn=lambda a: f"Demodulate APRS packet radio on {a.get('center_freq_mhz', 144.39)} MHz",
    can_remember_per_folder=False
)
def decode_aprs_packets(center_freq_mhz: float = 144.39) -> Dict[str, Any]:
    return multiband_sigint.decode_aprs_packet_stream(center_freq_mhz=center_freq_mhz)


# 3. Emergency Squawks
class SquawkArgs(BaseModel):
    aircraft_feed: List[Dict[str, Any]] = Field(description="List of aircraft transponder records containing 'squawk', 'callsign', etc.")

@registry.register(
    name="evaluate_emergency_squawks",
    tier=0,
    description="Scans incoming transponder feeds and fires high-priority alerts for emergency squawks 7700 (Mayday), 7600, or 7500.",
    args_schema=SquawkArgs,
    preview_fn=lambda a: f"Evaluate {len(a.get('aircraft_feed', []))} aircraft for emergency transponder squawk codes",
    can_remember_per_folder=False
)
def evaluate_emergency_squawks(aircraft_feed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return multiband_sigint.evaluate_adsb_squawks(aircraft_feed=aircraft_feed)


# 4. Aggregated Telemetry
class SIGINTTelemetryArgs(BaseModel):
    pass

@registry.register(
    name="get_multiband_sigint_telemetry",
    tier=0,
    description="Retrieves the latest chronological multi-band radio SIGINT telemetry across ACARS, APRS, and ADS-B.",
    args_schema=SIGINTTelemetryArgs,
    preview_fn=lambda a: "Retrieve multi-band radio SIGINT telemetry",
    can_remember_per_folder=False
)
def get_multiband_sigint_telemetry() -> Dict[str, Any]:
    return multiband_sigint.get_recent_sigint_telemetry()
