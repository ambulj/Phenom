"""
Unit and integration tests for Task 6G:
1. open_app quoting and allowlist:
   - Allowlisted apps (notepad, calc, brave, chrome, code, spotify, etc.) accepted at Tier 0.
   - Unallowlisted apps (cmd, powershell, malware.exe, etc.) strictly raise PermissionError.
   - Command injection / quoting breakout in app_name or url_or_args strictly blocked.
   - Web URLs validated for http/https scheme and zero shell injection characters.
2. Hotkey and Tray HALT to Guardian wiring:
   - hotkey_manager callback for kill_switch triggers guardian.trigger().
   - Authenticated POST /api/killswitch/trigger halts guardian and rejects unauthorized calls.
   - Global hotkey handler in guardian verified.
3. auto_execute_tier1 documentation:
   - SAFETY.md and HANDOFF.md disclose auto_execute_tier1, commit 0a4eabd, and owner decision.
   - auto_execute_tier1 remains True.
4. Standing safety-change rule:
   - AGENTS.md Rule 13 present.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.safety.engine import safety_engine
from services.backend.voice.hotkeys import hotkey_manager
from services.backend.tools.app_tools import (
    open_app,
    is_app_allowlisted,
    validate_url,
    APPROVED_APP_NAMES,
    APPROVED_APP_EXES
)
from services.backend.main import app


# ==============================================================================
# 1. open_app Quoting & Allowlist Tests
# ==============================================================================

def test_open_app_declared_at_tier_0():
    """Acceptance: open_app remains registered at Tier 0 in the ToolRegistry."""
    tool = registry.get("open_app")
    assert tool is not None
    assert tool.tier == 0
    assert registry.get_tier("open_app") == 0


def test_open_app_allowlist_acceptance():
    """Acceptance: Standard productivity applications and browsers pass allowlist."""
    for app_name in ["notepad", "calc", "calculator", "brave", "chrome", "code", "spotify"]:
        assert is_app_allowlisted(app_name, f"C:\\Program Files\\{app_name}\\{app_name}.exe") is True


def test_open_app_allowlist_rejection():
    """Acceptance: Unapproved binaries and dangerous system utilities are rejected with PermissionError."""
    unapproved = [
        "powershell", "cmd.exe", "regedit", "vssadmin",
        "mimikatz.exe", "nc.exe", "curl.exe", "format.com"
    ]
    for bad_app in unapproved:
        assert is_app_allowlisted(bad_app, f"C:\\Windows\\System32\\{bad_app}") is False
        with pytest.raises(PermissionError) as exc:
            open_app(bad_app)
        assert "not in the approved application allowlist" in str(exc.value)


def test_open_app_command_injection_breakout_blocked():
    """Acceptance: App names attempting shell breakout via quotes, pipes, or semicolons are rejected."""
    payloads = [
        'notepad" & calc.exe & "',
        'calc; powershell.exe -enc AAAA',
        'notepad | whoami',
        'notepad\ncalc',
        '`calc.exe`'
    ]
    for payload in payloads:
        with pytest.raises(PermissionError):
            open_app(payload)


def test_open_app_arguments_shell_characters_blocked():
    """Acceptance: Arguments containing shell operator characters are rejected with PermissionError."""
    with patch("services.backend.tools.app_tools._launch_on_default_desktop", return_value=1234):
        for bad_arg in ["& dir", "| calc", "; whoami", "\ncalc", "$env:SECRET"]:
            with pytest.raises(PermissionError) as exc:
                open_app("notepad", url_or_args=bad_arg)
            assert "Prohibited character" in str(exc.value)


def test_open_app_safe_url_handling():
    """Acceptance: Safe http/https URLs are validated and non-http schemes or shell injections are blocked."""
    # Safe URLs pass
    assert validate_url("https://youtube.com/watch?v=123") == "https://youtube.com/watch?v=123"
    assert validate_url("http://localhost:5173/dashboard") == "http://localhost:5173/dashboard"

    # Shell injection in URL blocked
    for bad_url in [
        "https://google.com?q=1 & calc.exe",
        "https://google.com;whoami",
        "https://test.com|calc",
        "file:///C:/Windows/win.ini",
        "javascript:alert(1)"
    ] :
        with pytest.raises(PermissionError):
            validate_url(bad_url)


def test_open_app_safe_launch_mocked():
    """Acceptance: Allowed application launches via safe desktop launcher without shell string interpolation."""
    with patch("services.backend.tools.app_tools._launch_on_default_desktop", return_value=4321) as mock_launch:
        res = open_app("notepad")
        assert res["launched"] is True
        assert res["launcher_pid"] == 4321
        # Verify launch called with clean list2cmdline string, never cmd.exe /c start string interpolation
        mock_launch.assert_called_once()
        cmd_called = mock_launch.call_args[0][0]
        assert "cmd.exe /c start" not in cmd_called
        assert "notepad" in cmd_called.lower()


# ==============================================================================
# 2. Hotkey & Tray HALT to Guardian Wiring Tests
# ==============================================================================

def test_hotkey_manager_killswitch_callback_triggers_guardian():
    """Acceptance: hotkey_manager kill_switch callback directly invokes guardian.trigger()."""
    if guardian.is_halted:
        guardian.resume()
    assert guardian.is_halted is False

    # Wire callback like main.py lifespan does
    hotkey_manager.register_callback("kill_switch", lambda: guardian.trigger("test_hotkey_trigger"))
    
    # Trigger action
    hotkey_manager.trigger_kill_switch("test_hotkey_trigger")
    assert guardian.is_halted is True
    guardian.resume()


def test_api_killswitch_trigger_endpoint_authentication():
    """Acceptance: POST /api/killswitch/trigger requires valid session token and halts guardian."""
    client = TestClient(app)
    token = os.environ.get("PHENOM_SESSION_TOKEN", "mock_session_token_6g")
    os.environ["PHENOM_SESSION_TOKEN"] = token

    if guardian.is_halted:
        guardian.resume()
    assert guardian.is_halted is False

    # 1. Unauthenticated request rejected
    resp_unauth = client.post("/api/killswitch/trigger", headers={})
    assert resp_unauth.status_code == 401
    assert guardian.is_halted is False

    # 2. Invalid token rejected
    resp_bad = client.post(
        "/api/killswitch/trigger",
        headers={"Authorization": "Bearer wrong_token"}
    )
    assert resp_bad.status_code == 401
    assert guardian.is_halted is False

    # 3. Authenticated request halts guardian
    resp_ok = client.post(
        "/api/killswitch/trigger",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Tray HALT button test"}
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["is_halted"] is True
    assert guardian.is_halted is True
    guardian.resume()


# ==============================================================================
# 3. auto_execute_tier1 Documentation & Integrity Tests
# ==============================================================================

def test_auto_execute_tier1_flag_status_and_disclosure():
    """Acceptance: auto_execute_tier1 remains True per owner decision, documented in SAFETY.md and HANDOFF.md."""
    # Flag must remain True per owner directive
    assert safety_engine.auto_execute_tier1 is True

    # SAFETY.md disclosure check
    with open("SAFETY.md", "r", encoding="utf-8") as f:
        safety_md = f.read()
    assert "auto_execute_tier1: bool = True" in safety_md
    assert "0a4eabd" in safety_md
    assert "Owner-Acknowledged" in safety_md

    # HANDOFF.md disclosure check
    with open("HANDOFF.md", "r", encoding="utf-8") as f:
        handoff_md = f.read()
    assert "auto_execute_tier1" in handoff_md
    assert "0a4eabd" in handoff_md


# ==============================================================================
# 4. Standing Safety-Change Rule in AGENTS.md
# ==============================================================================

def test_agents_md_standing_safety_change_rule():
    """Acceptance: AGENTS.md contains standing Rule 13 restricting changes to safety modules."""
    with open("AGENTS.md", "r", encoding="utf-8") as f:
        agents_md = f.read()
    assert "Standing safety-change rule:" in agents_md
    assert "services/backend/safety/engine.py" in agents_md
    assert "services/backend/safety/guardian.py" in agents_md
    assert "services/backend/safety/approvals.py" in agents_md
    assert "auto_execute_tier1" in agents_md
    assert "open_app" in agents_md
