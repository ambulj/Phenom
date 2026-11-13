"""
Unit Tests for Phenom Cyber Warfare & Hardware Security Suite.
Validates:
1. ESP8266 Microcontroller USB UART connectivity & command telemetry
2. Live Packet Interceptor & Guardian kill switch halt
3. Binary Reverse Engineering Copilot & vulnerability detection
4. Autonomous Red-Team Pentest DAG Mission
5. Windows ETW Kernel Telemetry Sensor
6. NVIDIA CUDA Hashcat Cryptanalysis Pipeline
7. Safety Registry registration for all Cyber Power Tools
"""

import os
import tempfile
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.esp8266_controller import ESP8266Controller
from services.backend.cyber.packet_interceptor import LivePacketInterceptor
from services.backend.cyber.binary_copilot import BinaryReverseEngineeringCopilot
from services.backend.cyber.red_team_agent import AutonomousRedTeamAgent
from services.backend.cyber.etw_sensor import ETWKernelSensor
from services.backend.cyber.cuda_hashcat import CUDAHashcatPipeline
import services.backend.tools.cyber_power_tools as cyber_tools


def test_esp8266_controller_lifecycle():
    controller = ESP8266Controller()
    ports = controller.list_serial_ports()
    assert isinstance(ports, list)
    assert len(ports) >= 0

    conn = controller.connect(port="COM3", baud_rate=115200)
    assert conn["connected"] is True
    assert conn["port"] == "COM3"

    res_scan = controller.send_command("scan aps")
    assert res_scan["success"] is True
    assert "Found" in res_scan["response"] or "executed" in res_scan["response"]

    res_sys = controller.send_command("sysinfo")
    assert res_sys["success"] is True

    telemetry = controller.get_telemetry_stream()
    assert len(telemetry) > 0

    disconn = controller.disconnect()
    assert disconn["disconnected"] is True


def test_live_packet_interceptor_and_guardian_halt():
    interceptor = LivePacketInterceptor()
    guardian.resume()

    start_res = interceptor.start_sniffing(interface="Wi-Fi", filter_exp="tcp port 80")
    assert start_res["status"] == "started"
    assert interceptor.is_sniffing is True

    events = interceptor.get_security_events()
    assert isinstance(events, list)

    # Stop manually
    stop_res = interceptor.stop_sniffing()
    assert stop_res["status"] == "stopped"
    assert interceptor.is_sniffing is False

    # Start again, then trigger Guardian kill switch
    interceptor.start_sniffing()
    assert interceptor.is_sniffing is True
    guardian.trigger("Emergency cyber kill-switch test")

    # The sniff worker thread halts on guardian.is_halted
    import time
    time.sleep(0.1)
    # Check that guardian abort is enforced
    agent = AutonomousRedTeamAgent()
    with pytest.raises(PermissionError):
        agent.execute_mission(target="127.0.0.1")

    guardian.resume()


def test_binary_reverse_engineering_copilot():
    copilot = BinaryReverseEngineeringCopilot()

    # Create dummy binary with unsafe C primitives
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
        # MZ header + vulnerable strings
        tmp.write(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff")
        tmp.write(b"This is a test binary containing strcpy and sprintf and gets calls.")
        tmp_path = tmp.name

    try:
        analysis = copilot.analyze_binary(tmp_path)
        assert analysis["format"] == "PE (Windows)"
        assert "strcpy" in analysis["dangerous_primitives_detected"]
        assert "sprintf" in analysis["dangerous_primitives_detected"]
        assert "HIGH" in analysis["risk_assessment"] or "MEDIUM" in analysis["risk_assessment"]
        assert analysis["mitigations"]["safe_seh_cfg"] is True
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_autonomous_red_team_agent():
    agent = AutonomousRedTeamAgent()
    guardian.resume()

    mission = agent.execute_mission(target="127.0.0.1", scope="local_lab")
    assert mission["target"] == "127.0.0.1"
    assert mission["scope"] == "local_lab"
    assert mission["stages_completed"] >= 3
    assert "# Autonomous Red-Team Assessment: 127.0.0.1" in mission["executive_report"]


def test_etw_kernel_sensor():
    sensor = ETWKernelSensor()
    audit = sensor.audit_kernel_telemetry(hours=1, max_events=10)
    assert audit["sensor"] == "Windows ETW & Sysmon Kernel Sensor"
    assert audit["threat_signatures_checked"] >= 4
    assert "lsa_protection_enabled" in audit["kernel_protection_status"]


def test_cuda_hashcat_pipeline():
    pipeline = CUDAHashcatPipeline()
    hw = pipeline.get_hardware_status()
    assert "cuda_acceleration" in hw
    assert "temperature_c" in hw
    assert "wpa" in hw["supported_modes"]

    audit = pipeline.run_hash_audit(
        hash_string_or_file="5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
        hash_type="sha256"
    )
    assert audit["success"] is True
    assert audit["algorithm"] == "SHA2-256"
    assert audit["hashcat_mode_id"] == 1400
    assert "MH/s" in audit["estimated_hashrate"]


def test_cyber_power_tools_registry():
    expected_tools = [
        ("execute_red_team_mission", 1),
        ("start_packet_sniffing", 1),
        ("stop_packet_sniffing", 0),
        ("analyze_binary_security", 0),
        ("connect_esp8266", 0),
        ("send_esp8266_command", 1),
        ("audit_etw_kernel_telemetry", 0),
        ("run_cuda_hash_audit", 0),
    ]

    for tool_name, expected_tier in expected_tools:
        meta = registry.get(tool_name)
        assert meta is not None, f"Tool {tool_name} must be registered in safety registry"
        assert meta.tier == expected_tier, f"Tool {tool_name} expected tier {expected_tier}, got {meta.tier}"
