"""
Unit tests for Milestone 42 Phase 3: CHRONO-CYBER Autonomous Red-Team Mission DAG
Validates:
1. Autonomous Lab Safe-Mode target boundary enforcement.
2. 5-Stage autonomous kill-chain execution in Lab Mode.
3. Shared vault persistence of campaign state and findings.
4. MITRE ATT&CK v15 debrief synthesis.
5. Universal Guardian kill switch (<25ms SLA) enforcement.
6. ToolRegistry registration for all 3 tools.
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.chrono_cyber import chrono_cyber, SafeModeTargetError


@pytest.fixture(autouse=True)
def ensure_guardian_active():
    guardian.resume()
    yield
    guardian.resume()


def test_safe_mode_boundary_enforcement():
    # Safe lab targets
    assert chrono_cyber.is_safe_target("127.0.0.1") is True
    assert chrono_cyber.is_safe_target("192.168.1.50") is True
    assert chrono_cyber.is_safe_target("10.0.0.1") is True
    assert chrono_cyber.is_safe_target("172.16.1.10") is True

    # Unsafe public targets
    assert chrono_cyber.is_safe_target("8.8.8.8") is False
    assert chrono_cyber.is_safe_target("https://target.com") is False

    with pytest.raises(SafeModeTargetError):
        chrono_cyber.execute_campaign("Out-of-Scope Pentest", target_scope="93.184.216.34")


def test_5_stage_campaign_execution_in_lab_mode():
    res = chrono_cyber.execute_campaign(
        campaign_name="Operation Sovereign Shield",
        target_scope="127.0.0.1",
        autonomous_lab_mode=True
    )
    assert res["status"] == "COMPLETED"
    assert "run_id" in res
    findings = res["findings"]
    assert len(findings["stages_completed"]) == 5
    # Verify stages
    stage_names = [s["name"] for s in findings["stages_completed"]]
    assert "RECON_AND_FINGERPRINT" in stage_names
    assert "INITIAL_ACCESS_PROBE" in stage_names
    assert "PRIVILEGE_ESCALATION_AUDIT" in stage_names
    assert "PERSISTENCE_AUDIT" in stage_names
    assert "MITRE_ATTACK_DEBRIEF" in stage_names
    # Verify MITRE mappings
    assert len(findings["mitre_mappings"]) >= 4


def test_mitre_debrief_generation():
    campaign = chrono_cyber.execute_campaign("Test Campaign", target_scope="127.0.0.1")
    run_id = campaign["run_id"]

    debrief = chrono_cyber.generate_mitre_debrief(run_id)
    assert debrief["run_id"] == run_id
    assert "risk_score" in debrief
    assert len(debrief["mitre_matrix"]) >= 4
    assert "executive_recommendation" in debrief


def test_guardian_kill_switch_sla():
    guardian.trigger("Emergency drill")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError):
        chrono_cyber.execute_campaign("Halted Operation", target_scope="127.0.0.1")
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Guardian SLA violation: {latency_ms:.3f}ms >= 25.0ms"


def test_chrono_cyber_tools_registered():
    import services.backend.tools.chrono_cyber_tools

    expected = [
        ("execute_chrono_campaign", 1),
        ("get_campaign_dag_status", 0),
        ("generate_mitre_debrief", 0)
    ]
    for t_name, exp_tier in expected:
        tool = registry.get(t_name)
        assert tool is not None, f"Tool '{t_name}' must be registered"
        assert tool.tier == exp_tier
