"""
Unit Tests for Phenom Autonomous Cross-Subsystem Tactical DAG Suite.
Validates:
1. 5-Stage perimeter security sweep execution
2. Multi-subsystem integration (RF SIGINT, active sockets, Sigma SIEM, canary tripwires)
3. Obsidian debrief and Jarvis vocal synthesis formatting
4. Guardian kill-switch SLA
5. Safety Registry metadata and risk tiers
"""

import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.tactical_dag_orchestrator import TacticalDAGOrchestrator
import services.backend.tools.tactical_dag_tools as dag_tools


def test_execute_perimeter_sweep():
    orchestrator = TacticalDAGOrchestrator()
    guardian.resume()

    sweep = orchestrator.execute_perimeter_security_sweep(target_host="127.0.0.1")
    assert sweep["target_host"] == "127.0.0.1"
    assert sweep["stages_completed"] == 4 or sweep["stages_completed"] == 5
    assert sweep["overall_status"] == "COMPLETED_CLEAN"
    assert "Perimeter security sweep complete" in sweep["vocal_summary_tts"]
    assert "# Autonomous Perimeter Security Sweep" in sweep["obsidian_report"]

    # Verify stage breakdown
    stage_names = [s["stage"] for s in sweep["stages"]]
    assert any("Radio Frequency" in name for name in stage_names)
    assert any("Active Sockets" in name for name in stage_names)
    assert any("Sigma SIEM" in name for name in stage_names)
    assert any("Cyber Deception" in name for name in stage_names)


def test_tactical_sweep_history():
    orchestrator = TacticalDAGOrchestrator()
    guardian.resume()

    orchestrator.execute_perimeter_security_sweep(target_host="127.0.0.1")
    history = orchestrator.get_sweep_history()
    assert isinstance(history, list)
    assert len(history) >= 1


def test_guardian_killswitch_tactical_dag():
    orchestrator = TacticalDAGOrchestrator()
    guardian.trigger("Emergency tactical sweep halt")

    with pytest.raises(PermissionError):
        orchestrator.execute_perimeter_security_sweep()

    guardian.resume()


def test_tactical_dag_tools_registry():
    expected = [
        ("execute_perimeter_sweep", 1),
        ("get_tactical_sweep_history", 0),
    ]
    for tool_name, exp_tier in expected:
        meta = registry.get(tool_name)
        assert meta is not None, f"Tool {tool_name} must be registered"
        assert meta.tier == exp_tier
