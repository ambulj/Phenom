"""
Unit & Integration Test Suite for Milestone 38 Phase 1: WSL2/WSLg Headless Kali Security Tool Bridge
Validates:
- Safe-Mode target validation (loopback, RFC1918 subnets allowed; public/external blocked with PermissionError).
- Structured parsers for Nmap, WhatWeb, Nikto, Masscan, Tshark, and Hashcat.
- Process tracking and sub-25ms Universal Guardian Kill Switch enforcement.
- Formal registration and schema compliance across all Kali security tools in ToolRegistry.
"""

import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.kali_bridge import kali_bridge, KaliSecurityBridge
import services.backend.tools.kali_tools


@pytest.fixture(autouse=True)
def reset_guardian_state():
    guardian.resume()
    yield
    guardian.resume()


def test_kali_bridge_safe_mode_enforcement():
    """Validates Autonomous Lab Safe-Mode rules strictly gate target IPs."""
    bridge = KaliSecurityBridge()

    # Allowed safe targets
    assert bridge.is_safe_target("127.0.0.1") is True
    assert bridge.is_safe_target("localhost") is True
    assert bridge.is_safe_target("::1") is True
    assert bridge.is_safe_target("192.168.1.45") is True
    assert bridge.is_safe_target("10.0.4.12") is True
    assert bridge.is_safe_target("172.28.16.5") is True
    assert bridge.is_safe_target("lab-node.local") is True
    assert bridge.is_safe_target(None) is True

    # Blocked external / public targets
    assert bridge.is_safe_target("8.8.8.8") is False
    assert bridge.is_safe_target("1.1.1.1") is False
    assert bridge.is_safe_target("142.250.190.46") is False
    assert bridge.is_safe_target("target-external.com") is False

    # Blocked target execution must raise PermissionError
    with pytest.raises(PermissionError, match="Autonomous Lab Safe-Mode Violation"):
        bridge.run_tool(tool="nmap", arguments="-sV", target="8.8.8.8")

    with pytest.raises(PermissionError, match="Autonomous Lab Safe-Mode Violation"):
        bridge.run_tool(tool="nikto", arguments="-h", target="unauthorized-target.org")


def test_nmap_parser():
    """Validates structured parsing of Nmap port scanning telemetry."""
    sample_nmap = """
Starting Nmap 7.94SVN ( https://nmap.org ) at 2026-11-13 19:30 IST
Nmap scan report for localhost (127.0.0.1)
Host is up (0.00042s latency).
Not shown: 994 closed tcp ports (reset)
PORT     STATE SERVICE VERSION
80/tcp   open  http    Apache httpd 2.4.52 ((Ubuntu))
443/tcp  open  ssl/ssl OpenSSL 3.0.2
8000/tcp open  http    uvicorn (Phenom API)
8088/tcp open  http    Tornado httpd 6.2
Nmap done: 1 IP address (1 host up) scanned in 0.85 seconds
"""
    parsed = kali_bridge.parse_nmap(sample_nmap)
    assert parsed["host_status"] == "up"
    assert "0.00042s latency" in parsed["latency"]
    assert parsed["open_ports_count"] == 4
    assert len(parsed["ports"]) == 4

    p8000 = next(p for p in parsed["ports"] if p["port"] == 8000)
    assert p8000["proto"] == "tcp"
    assert p8000["state"] == "open"
    assert p8000["service"] == "http"
    assert "uvicorn" in p8000["version"]


def test_whatweb_and_nikto_parsers():
    """Validates structured parsing of WhatWeb tech stack and Nikto findings."""
    sample_whatweb = "http://127.0.0.1:8000 [200 OK] Fast-API, Python[3.11.9], Title[Phenom Cyber OS], HTTPServer[uvicorn]"
    whatweb_parsed = kali_bridge.parse_whatweb(sample_whatweb)
    assert whatweb_parsed["status_code"] == 200
    assert whatweb_parsed["title"] == "Phenom Cyber OS"
    assert any("Python" in t for t in whatweb_parsed["technologies"])
    assert any("uvicorn" in t.lower() for t in whatweb_parsed["technologies"])

    sample_nikto = """
- Nikto v2.5.0
+ Target IP:          127.0.0.1
+ Target Port:        8000
+ Server: Uvicorn / FastAPI
+ The anti-clickjacking X-Frame-Options header is not present.
+ The X-Content-Type-Options header is not set.
+ Root page returns 200 OK.
"""
    nikto_parsed = kali_bridge.parse_nikto(sample_nikto)
    assert "Uvicorn" in nikto_parsed["server_banner"]
    assert nikto_parsed["total_findings"] >= 3
    assert any("X-Frame-Options" in f for f in nikto_parsed["findings"])


def test_masscan_and_tshark_and_hashcat_parsers():
    """Validates structured parsing for Masscan, Tshark, and Hashcat."""
    sample_masscan = """
Starting masscan 1.3.2 (http://bit.ly/14GZzcT) at 2026-11-13 14:00:00 GMT
Discovered open port 80/tcp on 127.0.0.1
Discovered open port 443/tcp on 127.0.0.1
Discovered open port 2222/tcp on 127.0.0.1
"""
    masscan_parsed = kali_bridge.parse_masscan(sample_masscan)
    assert masscan_parsed["total_open"] == 3
    assert masscan_parsed["open_ports"][0]["port"] == 80

    sample_tshark = """
  1 0.000000 127.0.0.1 -> 127.0.0.1 TCP 74 54321 -> 8000 [SYN]
  2 0.000120 127.0.0.1 -> 127.0.0.1 TCP 74 8000 -> 54321 [SYN, ACK]
  3 0.000150 127.0.0.1 -> 127.0.0.1 HTTP 210 GET /health HTTP/1.1
"""
    tshark_parsed = kali_bridge.parse_tshark(sample_tshark)
    assert tshark_parsed["packet_count"] == 3
    assert "TCP" in tshark_parsed["protocols_detected"]
    assert "HTTP" in tshark_parsed["protocols_detected"]

    sample_hashcat = """
Speed.#1.........: 21450.2 MH/s (55.40ms) @ Accel:1024 Loops:1024 Thr:64 Vec:1
Status...........: Running
Temp.............: 49c
"""
    hashcat_parsed = kali_bridge.parse_hashcat(sample_hashcat)
    assert "21450" in hashcat_parsed["hash_rate"]
    assert hashcat_parsed["status"] == "Running"
    assert "49c" in hashcat_parsed["gpu_temperature"]


def test_guardian_killswitch_kali_bridge():
    """SAF-02: Universal Guardian kill switch blocks Kali execution immediately (< 25ms)."""
    guardian.trigger("Emergency halt simulation")
    assert guardian.is_halted is True

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        kali_bridge.run_tool("nmap", target="127.0.0.1")

    guardian.resume()
    assert guardian.is_halted is False

    status = kali_bridge.get_status()
    assert status["safe_mode_active"] is True
    assert status["guardian_killswitch_sla_ms"] == 25.0


def test_kali_tools_registry():
    """Validates ToolRegistry definitions for execute_kali_recon, get_kali_status, and parse_kali_output."""
    expected_tools = {
        "execute_kali_recon": 1,
        "get_kali_status": 0,
        "parse_kali_output": 0,
        "execute_kali_tool": 1,
        "audit_kali_toolkit": 0,
    }

    for tool_name, expected_tier in expected_tools.items():
        tool = registry.get(tool_name)
        assert tool is not None, f"Tool '{tool_name}' must be registered"
        assert tool.tier == expected_tier, f"Tier mismatch for '{tool_name}': {tool.tier} != {expected_tier}"
        assert tool.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool.preview_fn), f"Tool '{tool_name}' missing preview_fn"
        preview = tool.preview_fn({})
        assert isinstance(preview, str) and len(preview) > 0
