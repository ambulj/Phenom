"""
Phenom Cyber Warfare & Infosec Operations Core Package.
Provides autonomous red-teaming, live packet sniffing, binary reverse engineering,
ESP8266 hardware interfacing, kernel ETW sensors, CUDA-accelerated cryptanalysis,
OSINT attack surface discovery, SDR radio telemetry, and binary entropy triage.
"""

from services.backend.cyber.esp8266_controller import ESP8266Controller
from services.backend.cyber.packet_interceptor import LivePacketInterceptor, packet_interceptor
from services.backend.cyber.binary_copilot import BinaryReverseEngineeringCopilot
from services.backend.cyber.red_team_agent import AutonomousRedTeamAgent, red_team_agent
from services.backend.cyber.etw_sensor import ETWKernelSensor, etw_sensor
from services.backend.cyber.cuda_hashcat import CUDAHashcatPipeline, cuda_hashcat
from services.backend.cyber.osint_engine import OSINTDiscoveryEngine, osint_engine
from services.backend.cyber.sdr_interceptor import SDRTelemetryReceiver, sdr_receiver
from services.backend.cyber.binary_triage import BinaryTriageAnalyzer, binary_triage

__all__ = [
    "ESP8266Controller",
    "LivePacketInterceptor",
    "packet_interceptor",
    "BinaryReverseEngineeringCopilot",
    "AutonomousRedTeamAgent",
    "red_team_agent",
    "ETWKernelSensor",
    "etw_sensor",
    "CUDAHashcatPipeline",
    "cuda_hashcat",
    "OSINTDiscoveryEngine",
    "osint_engine",
    "SDRTelemetryReceiver",
    "sdr_receiver",
    "BinaryTriageAnalyzer",
    "binary_triage",
]
