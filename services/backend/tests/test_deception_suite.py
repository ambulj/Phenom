"""
Unit Tests for Phenom Active Cyber Deception Enclave & Canary Token Factory.
Validates:
1. In-RAM multi-port honeypot lifecycle (SSH 2222, Telnet 2323, HTTP 8088)
2. Live TCP probe connection and decoy banner response
3. Canary Token Factory file generation (.env, json)
4. Tripwire detection on canary file modification / deletion
5. Tool Registry metadata and risk tiers
6. Guardian kill-switch SLA
"""

import os
import time
import socket
import tempfile
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.deception_enclave import CyberDeceptionEnclave
import services.backend.tools.deception_tools as dec_tools


def test_honeypot_lifecycle_and_probe():
    enclave = CyberDeceptionEnclave()
    guardian.resume()

    # Bind on ephemeral test ports
    test_ports = [12222, 12323]
    start_res = enclave.start_honeypots(ports=test_ports)
    assert start_res["status"] == "active"
    assert enclave.is_active is True
    assert len(start_res["ports_active"]) == 2

    # Probe the first test port via TCP client
    p = test_ports[0]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    sock.connect(("127.0.0.1", p))
    banner = sock.recv(512)
    sock.sendall(b"probe_payload_test\r\n")
    sock.close()

    assert len(banner) > 0
    time.sleep(0.2)

    logs = enclave.get_intruder_logs()
    assert len(logs) >= 1
    assert logs[-1]["target_port"] == p
    assert "probe_payload_test" in logs[-1]["payload_intercepted"] or "[BANNER_PROBE]" in logs[-1]["payload_intercepted"]

    # Stop honeypots
    stop_res = enclave.stop_honeypots()
    assert stop_res["status"] == "stopped"
    assert enclave.is_active is False


def test_canary_token_factory_and_tripwire():
    enclave = CyberDeceptionEnclave()
    guardian.resume()

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Generate env canary
        canary = enclave.generate_canary_token(token_type="env", target_dir=tmp_dir)
        assert canary["token_id"] is not None
        assert canary["tripwire_status"] == "ARMED"
        assert os.path.exists(canary["file_path"])

        # Check tripwires when file is unmodified
        alerts = enclave.check_canary_tripwires()
        assert len(alerts) == 0

        # Tamper with file
        with open(canary["file_path"], "a") as f:
            f.write("UNAUTHORIZED_ACCESS=true\n")

        alerts_after_tamper = enclave.check_canary_tripwires()
        assert len(alerts_after_tamper) == 1
        assert alerts_after_tamper[0]["event"] == "CANARY_FILE_MODIFIED"
        assert alerts_after_tamper[0]["severity"] == "CRITICAL"

        # Delete file
        os.remove(canary["file_path"])
        alerts_after_delete = enclave.check_canary_tripwires()
        assert len(alerts_after_delete) == 1
        assert alerts_after_delete[0]["event"] == "CANARY_FILE_DELETED_OR_MOVED"


def test_guardian_killswitch_deception():
    enclave = CyberDeceptionEnclave()
    enclave.start_honeypots(ports=[12444])
    assert enclave.is_active is True

    guardian.trigger("Emergency deception halt")

    with pytest.raises(PermissionError):
        enclave.start_honeypots(ports=[12444])

    with pytest.raises(PermissionError):
        enclave.generate_canary_token(token_type="env")

    guardian.resume()
    enclave.stop_honeypots()


def test_deception_tools_registry():
    expected = [
        ("start_cyber_honeypots", 1),
        ("stop_cyber_honeypots", 0),
        ("generate_canary_token_file", 1),
        ("audit_canary_tripwires", 0),
        ("get_deception_intruder_logs", 0),
    ]
    for tool_name, exp_tier in expected:
        meta = registry.get(tool_name)
        assert meta is not None, f"Tool {tool_name} must be registered"
        assert meta.tier == exp_tier
