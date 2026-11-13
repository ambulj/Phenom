"""
Unit Tests for Phenom Autonomous Red-vs-Blue Cyber War Game & Hardening Suite.
Validates:
1. 3-Round duel simulation against isolated local target
2. Windows netsh and Linux iptables firewall script generation
3. Obsidian After-Action Report (AAR) generation
4. Guardian kill-switch SLA
5. Safety Registry metadata and risk tiers
"""

import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.cyber_wargame import CyberWarGameEngine
import services.backend.tools.wargame_tools as wg_tools


def test_execute_wargame_simulation():
    engine = CyberWarGameEngine()
    guardian.resume()

    res = engine.execute_wargame_simulation(target_scope="127.0.0.1", simulated_scenario="web_server")
    assert res["target_scope"] == "127.0.0.1"
    assert res["rounds_completed"] == 3
    assert res["initial_risk"] == "CRITICAL"
    assert res["post_hardening_risk"] == "LOW_HARDENED"

    # Verify rounds
    assert len(res["rounds"]) == 3
    for r in res["rounds"]:
        assert r["mitigation_status"] == "MITIGATED"

    # Verify Obsidian AAR report
    assert "# After-Action Report (AAR): Cyber War Game" in res["obsidian_aar_report"]
    assert "netsh advfirewall" in res["obsidian_aar_report"]

    history = engine.get_wargame_history()
    assert len(history) >= 1


def test_generate_firewall_hardening_script():
    engine = CyberWarGameEngine()
    guardian.resume()

    ports = [2323, 8088]

    # Windows
    win_script = engine.generate_firewall_hardening_script(blocked_ports=ports, platform="windows")
    assert win_script["platform"] == "windows"
    assert win_script["rule_count"] == 2
    assert "netsh advfirewall firewall add rule" in win_script["script"]
    assert "localport=2323" in win_script["script"]

    # Linux
    linux_script = engine.generate_firewall_hardening_script(blocked_ports=ports, platform="linux")
    assert linux_script["platform"] == "linux"
    assert linux_script["rule_count"] == 2
    assert "iptables -A INPUT -p tcp --dport 2323 -j DROP" in linux_script["script"]


def test_guardian_killswitch_wargame():
    engine = CyberWarGameEngine()
    guardian.trigger("Emergency war game halt")

    with pytest.raises(PermissionError):
        engine.execute_wargame_simulation()

    with pytest.raises(PermissionError):
        engine.generate_firewall_hardening_script(blocked_ports=[2323])

    guardian.resume()


def test_wargame_tools_registry():
    expected = [
        ("execute_cyber_wargame", 1),
        ("generate_firewall_hardening_script", 0),
        ("get_wargame_history", 0),
    ]
    for tool_name, exp_tier in expected:
        meta = registry.get(tool_name)
        assert meta is not None, f"Tool {tool_name} must be registered"
        assert meta.tier == exp_tier
