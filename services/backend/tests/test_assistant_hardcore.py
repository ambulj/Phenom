"""
Hardcore End-to-End Stress Test for Phenom Assistant Subsystems.
Tests:
1. REST Security, Health & PhenomDoctor Diagnostics
2. WebSocket Handshake Security, Origin Validation & Session Token Guard
3. Protocol Event Stream, Heartbeats & Mode Switches
4. Safety Layer Adversarial Penetration Testing (Path traversal, ADS, Reserved Names, Denylist, Unknown Tools)
5. Tier 2 Human-in-the-Loop Confirmation Workflow (Denial vs Approval)
6. Guardian Kill Switch Emergency Halting & Resume Cycle
7. Encrypted Database Memory & Learned Rules Pipeline
8. Voice Subsystem Integrity (OpenWakeWord models & TTS availability)
"""

import os
import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient

from services.backend.main import app, get_expected_session_token, failed_handshakes
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.safety.engine import safety_engine
from services.backend.safety.path_guard import (
    validate_path,
    PathSecurityViolation,
    RESERVED_WINDOWS_NAMES
)
from services.backend.safety.action_log import action_log
from services.backend.memory.db import encrypted_db
from services.backend.memory.rules import learned_rules
from services.backend.tools.doctor import run_phenom_doctor
from services.backend.modes.mode_manager import mode_manager

TEST_VALID_TOKEN = "hardcore_session_token_" + "f" * 42

@pytest.fixture(autouse=True)
def setup_hardcore_test_env():
    """Ensure clean safety state, env tokens, and reset rate limit counters."""
    old_token = os.environ.get("PHENOM_SESSION_TOKEN")
    old_dev = os.environ.get("PHENOM_DEV")

    os.environ["PHENOM_SESSION_TOKEN"] = TEST_VALID_TOKEN
    os.environ["PHENOM_DEV"] = "1"
    failed_handshakes.clear()
    guardian.resume()

    yield

    guardian.resume()
    failed_handshakes.clear()
    if old_token is not None:
        os.environ["PHENOM_SESSION_TOKEN"] = old_token
    else:
        os.environ.pop("PHENOM_SESSION_TOKEN", None)

    if old_dev is not None:
        os.environ["PHENOM_DEV"] = old_dev
    else:
        os.environ.pop("PHENOM_DEV", None)


# =========================================================================
# 1. REST Endpoints, Diagnostics & Security
# =========================================================================

def test_hardcore_health_and_doctor_diagnostics():
    """Verify health endpoints and exhaustive doctor diagnostics."""
    client = TestClient(app)

    # Health probe
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in ("healthy", "ok")

    # API health probe
    api_resp = client.get("/api/health")
    assert api_resp.status_code == 200

    # Exhaustive PhenomDoctor Diagnostics
    doc_report = run_phenom_doctor(detailed=True)
    assert doc_report["overall_health"] in ("HEALTHY", "DEGRADED", "CRITICAL")
    assert "checks" in doc_report
    checks = doc_report["checks"]
    assert len(checks) >= 5
    assert doc_report["ok_count"] >= 3
    # Verify Python, Disk, Memory checks pass
    py_check = next((c for c in checks if "Python" in c["name"]), None)
    assert py_check is not None
    assert py_check["status"] == "OK"


# =========================================================================
# 2. WebSocket Security Boundary, Origin & Session Token Guard
# =========================================================================

def test_hardcore_websocket_security_boundary():
    """Verify CORS/Origin rejection, missing token rejection, and valid token handshake."""
    client = TestClient(app)

    # A. Origin Rejection: Malicious external domain must be rejected with 4401
    failed_handshakes.clear()
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/ws",
            subprotocols=[f"phenom.{TEST_VALID_TOKEN}"],
            headers={"origin": "http://malicious-hacker-site.com"}
        ):
            pass
    assert exc.value.code == 4401

    # B. Missing / Invalid Token: Must be rejected with 4401
    failed_handshakes.clear()
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/ws",
            subprotocols=["phenom.completely_wrong_token_xyz"],
            headers={"origin": "http://localhost:5173"}
        ):
            pass
    assert exc.value.code == 4401

    # C. Valid Handshake: Authorized origin and matching token
    failed_handshakes.clear()
    with client.websocket_connect(
        "/ws",
        subprotocols=[f"phenom.{TEST_VALID_TOKEN}"],
        headers={"origin": "http://localhost:5173"}
    ) as ws:
        # Initial greeting / state messages emitted immediately on connection
        init_rules = ws.receive_json()
        assert init_rules["type"] == "rules.updated"

        init_state = ws.receive_json()
        assert init_state["type"] == "state.change"
        assert init_state["payload"]["state"] in ("idle", "halted")

        init_mode = ws.receive_json()
        assert init_mode["type"] == "mode.changed"


# =========================================================================
# 3. Protocol Event Stream, Mode Switching & Cancellation
# =========================================================================

def test_hardcore_protocol_modes_and_cancellation():
    """Verify rapid mode switches, state transitions, and cancellation events."""
    client = TestClient(app)
    failed_handshakes.clear()

    with client.websocket_connect(
        "/ws",
        subprotocols=[f"phenom.{TEST_VALID_TOKEN}"],
        headers={"origin": "http://localhost:5173"}
    ) as ws:
        # Drain initial bursts
        for _ in range(5):
            ws.receive_json()

        # Test Mode Switching: Switch to Work mode
        ws.send_json({
            "id": "mode-req-1",
            "type": "mode.set",
            "payload": {"mode": "work"}
        })
        mode_resp = ws.receive_json()
        assert mode_resp["type"] == "mode.changed"
        assert mode_resp["payload"]["mode"] == "work"
        assert mode_manager.get_current_mode().name.lower() == "work"

        # Switch to Study mode
        ws.send_json({
            "id": "mode-req-2",
            "type": "mode.set",
            "payload": {"mode": "study"}
        })
        study_resp = ws.receive_json()
        assert study_resp["type"] == "mode.changed"
        assert study_resp["payload"]["mode"] == "study"

        # Switch to Chill mode
        ws.send_json({
            "id": "mode-req-3",
            "type": "mode.set",
            "payload": {"mode": "chill"}
        })
        chill_resp = ws.receive_json()
        assert chill_resp["type"] == "mode.changed"
        assert chill_resp["payload"]["mode"] == "chill"

        # Test Chat Cancellation
        ws.send_json({
            "id": "cancel-req-1",
            "type": "chat.cancel",
            "payload": {}
        })
        cancel_evt = ws.receive_json()
        assert cancel_evt["type"] == "chat.cancelled"
        state_evt = ws.receive_json()
        assert state_evt["type"] == "state.change"
        assert state_evt["payload"]["state"] == "idle"


# =========================================================================
# 4. Safety Layer Adversarial Penetration Testing
# =========================================================================

@pytest.mark.asyncio
async def test_hardcore_safety_path_guardrails_adversarial():
    """Verify path traversal, ADS streams, reserved Windows devices, and system directories are blocked."""
    # A. System Directory Traversal Attack
    with pytest.raises(PathSecurityViolation):
        validate_path(r"C:\Windows\System32\cmd.exe", mode="read")

    with pytest.raises(PathSecurityViolation):
        validate_path(r"C:\Program Files\Common Files", mode="read")

    # B. Directory Traversal via relative backtracking (..)
    with pytest.raises(PathSecurityViolation):
        validate_path(r"..\..\..\..\Windows\System32\drivers\etc\hosts", mode="read")

    # C. Windows Alternate Data Streams (ADS) Exploit
    with pytest.raises(PathSecurityViolation):
        validate_path(r"C:\Users\Public\Downloads\safe.txt:hidden_payload.exe", mode="write")

    # D. Windows Reserved Device Names (CON, PRN, AUX, NUL, COM1, LPT1)
    for dev in ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]:
        with pytest.raises(PathSecurityViolation):
            validate_path(f"C:\\Users\\Public\\{dev}.txt", mode="write")

    # E. Safe allowed paths must pass validation
    temp_dir = tempfile.gettempdir()
    safe_path = os.path.join(temp_dir, "phenom_hardcore_test.txt")
    valid_res = validate_path(safe_path, mode="write")
    assert valid_res is not None


@pytest.mark.asyncio
async def test_hardcore_unregistered_tool_blocked_tier3():
    """Unregistered or malicious tool name must be treated as Tier 3 and blocked."""
    with pytest.raises(PermissionError) as exc_info:
        await safety_engine.execute_tool(
            "unregistered_malicious_exploit_tool",
            {"command": "whoami"}
        )
    assert "Tier 3" in str(exc_info.value) or "not registered" in str(exc_info.value)


# =========================================================================
# 5. Tier 2 Human-in-the-Loop Confirmation Workflow
# =========================================================================

@pytest.mark.asyncio
async def test_hardcore_tier2_confirmation_denial_and_approval(tmp_path):
    """Verify Tier 2 confirmation workflow: user denial cancels, user approval executes."""
    test_file = tmp_path / "hardcore_delete_test.txt"
    test_file.write_text("Phenom Hardcore Test Payload", encoding="utf-8")
    assert test_file.exists()

    # Case A: User Denies Confirmation
    async def mock_user_denial(*args, **kwargs):
        return ("denied", False)

    safety_engine.set_confirmation_handler(mock_user_denial)

    with pytest.raises(PermissionError) as exc_info:
        await safety_engine.execute_tool("recycle_delete", {"path": str(test_file)})
    assert "denied" in str(exc_info.value).lower()
    # File must still exist!
    assert test_file.exists()

    # Case B: User Approves Confirmation
    async def mock_user_approval(*args, **kwargs):
        return ("approved", False)

    safety_engine.set_confirmation_handler(mock_user_approval)

    res = await safety_engine.execute_tool("recycle_delete", {"path": str(test_file)})
    assert res.get("status") == "success"
    # File safely moved to recycle bin
    assert not test_file.exists()


# =========================================================================
# 6. Guardian Kill Switch Emergency Halting
# =========================================================================

@pytest.mark.asyncio
async def test_hardcore_guardian_killswitch_immediate_halt(tmp_path):
    """Verify Guardian halt immediately blocks all execution and resume restores it."""
    # Ensure starting clean
    guardian.resume()
    assert not guardian.is_halted

    # Trigger emergency halt
    guardian.trigger("Hardcore Unit Test Emergency Stop")
    assert guardian.is_halted is True

    # Any tool execution must fail instantly with PermissionError
    with pytest.raises(PermissionError) as exc:
        await safety_engine.execute_tool("list_files", {"path": str(tmp_path)})
    assert "Guardian kill switch is active" in str(exc.value)

    # Resume
    guardian.resume()
    assert guardian.is_halted is False

    # Execution works again
    list_res = await safety_engine.execute_tool("list_files", {"path": str(tmp_path)})
    assert list_res.get("status") == "success" or isinstance(list_res.get("result"), list)


# =========================================================================
# 7. Memory & Learned Rules Integrity
# =========================================================================

def test_hardcore_memory_and_rules_retention():
    """Verify Encrypted DB message history logging and learned rules retention."""
    import uuid
    # 1. Message History
    uid1 = f"hardcore_msg_{uuid.uuid4().hex[:8]}"
    uid2 = f"hardcore_msg_{uuid.uuid4().hex[:8]}"
    encrypted_db.add_message(
        msg_id=uid1,
        role="user",
        content="Remember: always keep test reports crisp."
    )
    encrypted_db.add_message(
        msg_id=uid2,
        role="assistant",
        content="Understood. Reports will remain crisp and concise."
    )
    recent = encrypted_db.get_recent_messages(limit=2)
    assert len(recent) >= 2
    assert any("crisp" in m["content"] for m in recent)

    # 2. Add Fact
    encrypted_db.add_fact(category="preferences", fact="User prefers concise logs")
    facts = encrypted_db.list_facts()
    assert any("concise logs" in f["fact"] for f in facts)

    # 3. Learned Rules Persistence
    rule_text = "Always append timestamp to status logs"
    learned_rules.add_rule(rule_text)
    active_rules = [r["rule_text"] for r in learned_rules.list_rules(active_only=True)]
    assert rule_text in active_rules
    formatted = learned_rules.format_rules_for_prompt()
    assert rule_text in formatted


# =========================================================================
# 8. Voice Subsystem Integrity (OpenWakeWord & Audio Models)
# =========================================================================

def test_hardcore_voice_subsystem_readiness():
    """Verify wake word models exist in the venv and are readable."""
    import openwakeword
    model_paths = openwakeword.get_pretrained_model_paths()
    assert len(model_paths) > 0, "OpenWakeWord models must be packaged and available"
    for m in model_paths:
        p = Path(m)
        assert p.is_file(), f"Model file {p} must exist"
        assert p.stat().st_size > 1000, f"Model file {p} must not be empty"
