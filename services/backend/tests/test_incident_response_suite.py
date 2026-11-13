"""
Unit Tests for Phenom Tactical Incident Response & RAM Forensics Suite.
Validates:
1. Rolling packet buffer and automated PCAP dump generation
2. Network Egress Shield isolation and restoration on active PID
3. Process RAM memory string and IOC triage (IPs, URLs, Base64)
4. Guardian kill-switch SLA
5. Safety Registry metadata and risk tiers
"""

import os
import json
import tempfile
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.incident_responder import TacticalIncidentResponder
import services.backend.tools.incident_response_tools as ir_tools


def test_rolling_pcap_buffer_and_dump():
    responder = TacticalIncidentResponder()
    guardian.resume()

    # Record test packets
    for i in range(5):
        responder.record_network_packet({
            "timestamp": 1700000000 + i,
            "proto": "TCP",
            "src": f"192.168.1.100:{5000+i}",
            "dst": "10.0.0.1:443",
            "length": 128
        })

    with tempfile.TemporaryDirectory() as tmp_dir:
        res = responder.trigger_incident_pcap_dump(alert_id="SIGMA-TEST-001", output_dir=tmp_dir)
        assert res["success"] is True
        assert os.path.exists(res["pcap_file"])
        assert res["packet_count"] >= 5

        with open(res["pcap_file"], "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["alert_id"] == "SIGMA-TEST-001"
        assert len(data["packets"]) >= 5


def test_network_egress_shield():
    responder = TacticalIncidentResponder()
    guardian.resume()

    my_pid = os.getpid()

    # Isolate current process
    iso = responder.isolate_pid_network_egress(pid=my_pid)
    assert iso["success"] is True
    assert iso["pid"] == my_pid
    assert iso["shield_status"] == "EGRESS_SEVERED"

    isolated_list = responder.list_isolated_processes()
    assert any(p["pid"] == my_pid for p in isolated_list)

    # Remove isolation
    rem = responder.remove_pid_isolation(pid=my_pid)
    assert rem["success"] is True
    assert rem["status"] == "ISOLATION_REMOVED"

    isolated_after = responder.list_isolated_processes()
    assert not any(p["pid"] == my_pid for p in isolated_after)


def test_process_memory_forensics():
    responder = TacticalIncidentResponder()
    guardian.resume()

    my_pid = os.getpid()
    dump = responder.dump_process_memory_forensics(pid=my_pid)
    assert dump["pid"] == my_pid
    assert "memory_mb" in dump
    assert "iocs_identified" in dump
    assert isinstance(dump["iocs_identified"]["ips"], list)
    assert "# Process RAM Forensic Debrief" in dump["obsidian_report"]


def test_guardian_killswitch_incident_response():
    responder = TacticalIncidentResponder()
    guardian.trigger("Emergency IR halt")

    with pytest.raises(PermissionError):
        responder.trigger_incident_pcap_dump(alert_id="TEST")

    with pytest.raises(PermissionError):
        responder.isolate_pid_network_egress(pid=os.getpid())

    with pytest.raises(PermissionError):
        responder.dump_process_memory_forensics(pid=os.getpid())

    guardian.resume()


def test_incident_response_tools_registry():
    expected = [
        ("trigger_incident_pcap_dump", 0),
        ("isolate_pid_network_egress", 1),
        ("remove_pid_network_isolation", 1),
        ("dump_process_memory_forensics", 0),
        ("list_isolated_processes", 0),
    ]
    for tool_name, exp_tier in expected:
        meta = registry.get(tool_name)
        assert meta is not None, f"Tool {tool_name} must be registered"
        assert meta.tier == exp_tier
