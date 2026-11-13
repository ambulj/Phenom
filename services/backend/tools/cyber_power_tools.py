"""
Phenom Elite Cyber Warfare & Hardware Security Tool Suite
Registers high-autonomy cybersecurity tools in the Safety registry:
1. Autonomous Red-Team Pentest DAG Mission
2. Live Network Packet Sniffing & Traffic Interception
3. Binary Reverse Engineering & Vulnerability Copilot
4. ESP8266 Hardware Microcontroller USB UART Bridge
5. Windows ETW & Sysmon Kernel Telemetry Sensor
6. NVIDIA RTX GPU CUDA Cryptanalysis Pipeline
"""

import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.red_team_agent import red_team_agent
from services.backend.cyber.packet_interceptor import packet_interceptor
from services.backend.cyber.binary_copilot import BinaryReverseEngineeringCopilot
from services.backend.cyber.esp8266_controller import ESP8266Controller
from services.backend.cyber.etw_sensor import etw_sensor
from services.backend.cyber.cuda_hashcat import cuda_hashcat

# Shared instances
_binary_copilot = BinaryReverseEngineeringCopilot()
_esp8266 = ESP8266Controller()


# -------------------------------------------------------------
# 1. Autonomous Red-Team Mission
# -------------------------------------------------------------
class RedTeamMissionArgs(BaseModel):
    target: str = Field(description="Target host, IP address, or CIDR range (e.g. 192.168.1.1, scanme.nmap.org)")
    scope: str = Field(default="local", description="Scope boundary (local, lab, external)")

@registry.register(
    name="execute_red_team_mission",
    tier=1,
    description="Executes an autonomous 4-stage penetration testing workflow (Recon -> Enumeration -> Vulnerability Check -> Obsidian Debrief).",
    args_schema=RedTeamMissionArgs,
    preview_fn=lambda a: f"Execute autonomous red-team mission against target: {a.get('target')}",
    can_remember_per_folder=False
)
def execute_red_team_mission(target: str, scope: str = "local") -> Dict[str, Any]:
    return red_team_agent.execute_mission(target=target, scope=scope)


# -------------------------------------------------------------
# 2. Live Packet Sniffing
# -------------------------------------------------------------
class StartPacketSniffingArgs(BaseModel):
    interface: Optional[str] = Field(default=None, description="Network interface name (e.g. Wi-Fi, Ethernet, eth0)")
    filter_exp: str = Field(default="tcp or udp", description="BPF packet filter expression")

@registry.register(
    name="start_packet_sniffing",
    tier=1,
    description="Starts live background packet sniffing to detect cleartext credential leaks, ARP poisoning, and anomalous DNS beacons.",
    args_schema=StartPacketSniffingArgs,
    preview_fn=lambda a: f"Start live packet sniffer on interface {a.get('interface', 'default')}",
    can_remember_per_folder=False
)
def start_packet_sniffing(interface: Optional[str] = None, filter_exp: str = "tcp or udp") -> Dict[str, Any]:
    return packet_interceptor.start_sniffing(interface=interface, filter_exp=filter_exp)


class StopPacketSniffingArgs(BaseModel):
    pass

@registry.register(
    name="stop_packet_sniffing",
    tier=0,
    description="Stops active live packet sniffing and summarizes inspected traffic statistics.",
    args_schema=StopPacketSniffingArgs,
    preview_fn=lambda a: "Stop live network packet sniffing",
    can_remember_per_folder=False
)
def stop_packet_sniffing() -> Dict[str, Any]:
    return packet_interceptor.stop_sniffing()


# -------------------------------------------------------------
# 3. Binary Reverse Engineering Copilot
# -------------------------------------------------------------
class BinaryAnalysisArgs(BaseModel):
    file_path: str = Field(description="Absolute path to executable binary, DLL, or ELF file")

@registry.register(
    name="analyze_binary_security",
    tier=0,
    description="Performs static reverse engineering, disassembly analysis, compiler mitigation checking (ASLR, DEP, Canaries), and unsafe C/C++ primitive scanning.",
    args_schema=BinaryAnalysisArgs,
    preview_fn=lambda a: f"Analyze binary security posture: {os.path.basename(a.get('file_path', ''))}",
    can_remember_per_folder=False
)
def analyze_binary_security(file_path: str) -> Dict[str, Any]:
    return _binary_copilot.analyze_binary(file_path)


# -------------------------------------------------------------
# 4. ESP8266 Hardware Microcontroller
# -------------------------------------------------------------
class ConnectESP8266Args(BaseModel):
    port: Optional[str] = Field(default=None, description="COM port (e.g. COM3, COM4) or leave empty for auto-detection")
    baud_rate: int = Field(default=115200, description="Serial baud rate (defaults to 115200)")

@registry.register(
    name="connect_esp8266",
    tier=0,
    description="Connects to a physical or emulated ESP8266 microcontroller (NodeMCU / D1 Mini / Deauther) over USB UART.",
    args_schema=ConnectESP8266Args,
    preview_fn=lambda a: f"Connect to ESP8266 hardware board on port {a.get('port', 'auto')}",
    can_remember_per_folder=False
)
def connect_esp8266(port: Optional[str] = None, baud_rate: int = 115200) -> Dict[str, Any]:
    return _esp8266.connect(port=port, baud_rate=baud_rate)


class SendESP8266CommandArgs(BaseModel):
    command: str = Field(description="Command string to send over UART (e.g. scan, beacon, help, deauth)")

@registry.register(
    name="send_esp8266_command",
    tier=1,
    description="Sends an 802.11 monitor / RF / deauth command to connected ESP8266 hardware.",
    args_schema=SendESP8266CommandArgs,
    preview_fn=lambda a: f"Send command to ESP8266 hardware: {a.get('command')}",
    can_remember_per_folder=False
)
def send_esp8266_command(command: str) -> Dict[str, Any]:
    return _esp8266.send_command(command)


# -------------------------------------------------------------
# 5. Windows ETW & Kernel Telemetry Sensor
# -------------------------------------------------------------
class AuditETWArgs(BaseModel):
    hours: int = Field(default=1, description="Audit time window in hours")
    max_events: int = Field(default=25, description="Max event records to interrogate")

@registry.register(
    name="audit_etw_kernel_telemetry",
    tier=0,
    description="Audits Windows Event Tracing & Sysmon kernel channels for Process Hollowing, LSASS injection, LOLBin abuses, and malicious PowerShell execution.",
    args_schema=AuditETWArgs,
    preview_fn=lambda a: f"Audit Windows ETW and Sysmon kernel telemetry for the last {a.get('hours', 1)} hour(s)",
    can_remember_per_folder=False
)
def audit_etw_kernel_telemetry(hours: int = 1, max_events: int = 25) -> Dict[str, Any]:
    return etw_sensor.audit_kernel_telemetry(hours=hours, max_events=max_events)


# -------------------------------------------------------------
# 6. CUDA GPU Cryptanalysis Pipeline
# -------------------------------------------------------------
class CUDAHashAuditArgs(BaseModel):
    hash_target: str = Field(description="Hash string (MD5, SHA256, NTLM) or path to hash file")
    hash_type: str = Field(default="sha256", description="Algorithm type: md5, sha1, sha256, sha512, ntlm, wpa, kerberos5, bcrypt")
    wordlist: Optional[str] = Field(default=None, description="Optional wordlist path (defaults to built-in top candidates)")

@registry.register(
    name="run_cuda_hash_audit",
    tier=0,
    description="Executes NVIDIA GPU-accelerated hash entropy auditing and candidate cryptanalysis with thermal throttle guards.",
    args_schema=CUDAHashAuditArgs,
    preview_fn=lambda a: f"Run CUDA GPU hash cryptanalysis audit for {a.get('hash_type', 'sha256')}",
    can_remember_per_folder=False
)
def run_cuda_hash_audit(hash_target: str, hash_type: str = "sha256", wordlist: Optional[str] = None) -> Dict[str, Any]:
    return cuda_hashcat.run_hash_audit(hash_string_or_file=hash_target, hash_type=hash_type, wordlist_path=wordlist)
