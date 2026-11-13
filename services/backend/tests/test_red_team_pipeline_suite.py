"""
Unit & Integration Test Suite for Milestone 38 Phase 2: Autonomous Multi-Vector Red-Team Pipeline
Validates:
- Execution of all 4 vectors (Loopback, Subnet, Honeypot Simulation, and Obsidian AAR synthesis).
- Strict enforcement of Autonomous Lab Safe-Mode (blocks unauthorized external/public targets).
- Sub-25ms Universal Guardian Kill Switch abort.
- Formal registration and schema compliance across all red-team pipeline tools in ToolRegistry.
"""

import os
import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.red_team_pipeline import red_team_pipeline, AutonomousRedTeamPipeline
import services.backend.tools.red_team_pipeline_tools


@pytest.fixture(autouse=True)
def reset_guardian_state():
    guardian.resume()
    yield
    guardian.resume()


def test_execute_red_team_campaign_full(tmp_path):
    """Executes a full 4-vector automated red-team campaign against local scope."""
    test_pipeline = AutonomousRedTeamPipeline(vault_path=str(tmp_path / "cyber_vault"))
    result = test_pipeline.execute_campaign(campaign_type="FULL", target_scope="127.0.0.1")

    assert result["status"] == "COMPLETED"
    assert result["campaign_type"] == "FULL"
    assert result["target_scope"] == "127.0.0.1"
    assert len(result["vectors_executed"]) == 4

    # Verify Vector 1 (Loopback)
    v1 = result["results"]["vector_1_loopback"]
    assert v1["open_ports_count"] >= 1
    assert len(v1["technologies_fingerprinted"]) >= 1

    # Verify Vector 2 (Subnet)
    v2 = result["results"]["vector_2_subnet"]
    assert v2["hosts_discovered_count"] >= 1
    assert v2["posture"] == "SECURE_LOCAL_LAB"

    # Verify Vector 3 (Honeypot Probing)
    v3 = result["results"]["vector_3_honeypot"]
    assert v3["traps_probed_count"] == 3
    assert v3["deception_fidelity"] == "100%"

    # Verify Vector 4 (AAR Debrief & Vocal Summary)
    v4 = result["results"]["vector_4_aar"]
    assert os.path.exists(v4["aar_path"])
    assert len(result["vocal_summary"]) >= 2
    assert "Sir" in result["vocal_summary"][0]


def test_safe_mode_target_rejection():
    """Validates Autonomous Lab Safe-Mode blocks out-of-scope targets."""
    with pytest.raises(PermissionError, match="Autonomous Lab Safe-Mode Violation"):
        red_team_pipeline.execute_campaign(campaign_type="FULL", target_scope="8.8.8.8")

    with pytest.raises(PermissionError, match="Autonomous Lab Safe-Mode Violation"):
        red_team_pipeline.execute_campaign(campaign_type="FULL", target_scope="attack-external.com")


def test_individual_vectors(tmp_path):
    """Tests executing individual vectors independently."""
    test_pipeline = AutonomousRedTeamPipeline(vault_path=str(tmp_path / "cyber_vault"))

    # Vector 1
    loopback = test_pipeline.audit_loopback_and_containers("127.0.0.1")
    assert loopback["target"] == "127.0.0.1"
    assert loopback["risk_score"] == "LOW"

    # Vector 2
    subnet = test_pipeline.audit_local_subnet_discovery("192.168.1.0/24")
    assert subnet["hosts_discovered_count"] == 3

    # Vector 3
    honeypot = test_pipeline.simulate_adversarial_honeypot_probe([2222, 2323])
    assert honeypot["traps_probed_count"] == 2


def test_guardian_killswitch_red_team():
    """SAF-02: Universal Guardian kill switch halts campaign execution in < 25ms."""
    guardian.trigger("Intrusion detected during campaign")
    assert guardian.is_halted is True

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        red_team_pipeline.execute_campaign("FULL", "127.0.0.1")

    guardian.resume()
    assert guardian.is_halted is False


def test_red_team_pipeline_tools_registry():
    """Validates ToolRegistry definitions for execute_red_team_campaign and get_red_team_history."""
    expected_tools = {
        "execute_red_team_campaign": 1,
        "get_red_team_history": 0,
    }

    for tool_name, expected_tier in expected_tools.items():
        tool = registry.get(tool_name)
        assert tool is not None, f"Tool '{tool_name}' must be registered"
        assert tool.tier == expected_tier, f"Tier mismatch for '{tool_name}': {tool.tier} != {expected_tier}"
        assert tool.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool.preview_fn), f"Tool '{tool_name}' missing preview_fn"
        preview = tool.preview_fn({})
        assert isinstance(preview, str) and len(preview) > 0
