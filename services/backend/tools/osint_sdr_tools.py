"""
Phenom OSINT, SDR Radio Telemetry & Binary Triage Tool Registry
Registers defensive tools in the Safety registry:
1. Passive Domain DNS Enumeration & OSINT
2. Attack Surface Graph Builder for Obsidian
3. 1090 MHz Mode-S / ADS-B Aircraft Transponder Tracker
4. 433 MHz Ambient Environmental Sensor Decoder
5. Static Binary Triage & Section Entropy Analyzer
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.osint_engine import osint_engine
from services.backend.cyber.sdr_interceptor import sdr_receiver
from services.backend.cyber.binary_triage import binary_triage


# 1. OSINT DNS
class GatherOSINTArgs(BaseModel):
    domain: str = Field(description="Target domain to enumerate (e.g. example.com)")

@registry.register(
    name="gather_domain_osint",
    tier=0,
    description="Performs passive DNS record enumeration and Certificate Transparency log discovery to map external domain footprints.",
    args_schema=GatherOSINTArgs,
    preview_fn=lambda a: f"Enumerate DNS and public subdomains for {a.get('domain')}",
    can_remember_per_folder=False
)
def gather_domain_osint(domain: str) -> Dict[str, Any]:
    return osint_engine.enumerate_dns(domain)


# 2. Attack Surface Graph
class AttackSurfaceArgs(BaseModel):
    domain: str = Field(description="Target domain to map (e.g. example.com)")

@registry.register(
    name="generate_attack_surface_graph",
    tier=0,
    description="Discovers subdomains and builds an associative attack surface graph with Obsidian markdown report.",
    args_schema=AttackSurfaceArgs,
    preview_fn=lambda a: f"Build attack surface graph for {a.get('domain')}",
    can_remember_per_folder=False
)
def generate_attack_surface_graph(domain: str) -> Dict[str, Any]:
    return osint_engine.build_attack_surface_graph(domain)


# 3. ADS-B Radio Tracking
class ADSBTrackingArgs(BaseModel):
    duration_seconds: int = Field(default=5, description="Duration in seconds to sample Mode-S transponders")

@registry.register(
    name="start_adsb_flight_tracker",
    tier=0,
    description="Tunes connected RTL-SDR to 1090 MHz to decode live overhead aircraft ADS-B transponder telemetry (altitude, speed, callsign).",
    args_schema=ADSBTrackingArgs,
    preview_fn=lambda a: f"Track overhead aircraft transponders on 1090 MHz ({a.get('duration_seconds', 5)}s)",
    can_remember_per_folder=False
)
def start_adsb_flight_tracker(duration_seconds: int = 5) -> Dict[str, Any]:
    return sdr_receiver.start_adsb_tracking(duration_seconds=duration_seconds)


# 4. RF Sensor Demodulator
class RFSensorArgs(BaseModel):
    frequency_mhz: float = Field(default=433.92, description="Radio frequency in MHz (defaults to 433.92)")

@registry.register(
    name="decode_rf_sensor_stream",
    tier=0,
    description="Demodulates sub-GHz ISM band telemetry from local environmental sensors and weather stations.",
    args_schema=RFSensorArgs,
    preview_fn=lambda a: f"Demodulate RF sensor stream on {a.get('frequency_mhz', 433.92)} MHz",
    can_remember_per_folder=False
)
def decode_rf_sensor_stream(frequency_mhz: float = 433.92) -> Dict[str, Any]:
    return sdr_receiver.decode_rf_sensor_stream(frequency_mhz=frequency_mhz)


# 5. Static Binary Triage
class BinaryTriageArgs(BaseModel):
    file_path: str = Field(description="Path to executable or binary file")

@registry.register(
    name="triage_binary_sections",
    tier=0,
    description="Calculates Shannon entropy across binary sections, identifying packed, compressed, or encrypted native code.",
    args_schema=BinaryTriageArgs,
    preview_fn=lambda a: f"Triage binary sections and calculate entropy for {a.get('file_path')}",
    can_remember_per_folder=False
)
def triage_binary_sections(file_path: str) -> Dict[str, Any]:
    return binary_triage.triage_binary(file_path)
