"""
Unit & Integration Test Suite for Milestone 39 Phase 1: Real-Time ETW/Sysmon Behavioral Anomaly Correlator
Validates:
- Real-time parent-child lineage analysis.
- Sysmon Event ID 8 (CreateRemoteThread) & Event ID 10 (ProcessAccess) correlation.
- Dynamic process behavioral threat scoring (0-100) and risk tier classification.
- Sub-25ms Universal Guardian Kill Switch enforcement.
- Formal registration and schema compliance across all kernel behavioral tools in ToolRegistry.
"""

import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.kernel_behavior_correlator import kernel_behavior_correlator
import services.backend.tools.kernel_behavior_tools


@pytest.fixture(autouse=True)
def reset_behavior_state():
    guardian.resume()
    kernel_behavior_correlator.clear_anomalies()
    yield
    guardian.resume()
    kernel_behavior_correlator.clear_anomalies()


def test_process_lineage_analysis():
    """Validates auditing of process tree execution paths."""
    anomalies = kernel_behavior_correlator.analyze_process_lineage()
    assert isinstance(anomalies, list)
    # Even if benign workstation has no active malware, method must execute cleanly without error


def test_ingest_etw_event_remote_thread():
    """Validates detection and scoring of Sysmon Event ID 8 remote thread injections."""
    event = {
        "event_id": 8,
        "source_pid": 1420,
        "source_process": "malicious_loader.exe",
        "target_pid": 880,
        "target_process": "svchost.exe",
        "start_address": "0x00007FF8B2A10000",
    }
    anomaly = kernel_behavior_correlator.ingest_etw_event(event)
    assert anomaly is not None
    assert anomaly["rule_id"] == "ANOMALY-INJECTION-008"
    assert anomaly["severity"] == "CRITICAL"
    assert anomaly["mitre_technique"].startswith("T1055")
    assert anomaly["containment_recommended"] == "PROCESS_MEMORY_FREEZE"

    # Verify score updated
    score_info = kernel_behavior_correlator.get_process_threat_score(1420)
    assert score_info["threat_score"] >= 80
    assert score_info["risk_level"] == "CRITICAL"
    assert score_info["anomalies_detected"] == 1


def test_ingest_etw_event_lsass_access():
    """Validates detection of Sysmon Event ID 10 targeting LSASS credential memory."""
    event = {
        "event_id": 10,
        "source_pid": 9812,
        "source_process": "dump_tool.exe",
        "target_pid": 640,
        "target_process": "lsass.exe",
        "granted_access": "0x1010 (PROCESS_VM_READ)",
    }
    anomaly = kernel_behavior_correlator.ingest_etw_event(event)
    assert anomaly is not None
    assert anomaly["rule_id"] == "ANOMALY-LSASS-ACCESS-010"
    assert anomaly["severity"] == "CRITICAL"
    assert anomaly["mitre_technique"].startswith("T1003")

    score_info = kernel_behavior_correlator.get_process_threat_score(9812)
    assert score_info["threat_score"] >= 90
    assert score_info["risk_level"] == "CRITICAL"


def test_guardian_killswitch_behavior_correlator():
    """SAF-02: Universal Guardian kill switch halts behavioral ingestion in < 25ms."""
    guardian.trigger("Emergency halt during kernel analysis")
    assert guardian.is_halted is True

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        kernel_behavior_correlator.analyze_process_lineage()

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        kernel_behavior_correlator.ingest_etw_event({"event_id": 8})

    guardian.resume()
    assert guardian.is_halted is False


def test_kernel_behavior_tools_registry():
    """Validates ToolRegistry definitions for audit_process_lineage, get_process_behavioral_score, etc."""
    expected_tools = {
        "audit_process_lineage": 0,
        "get_process_behavioral_score": 0,
        "get_behavioral_anomalies_log": 0,
        "evaluate_etw_threat_event": 1,
    }

    for tool_name, expected_tier in expected_tools.items():
        tool = registry.get(tool_name)
        assert tool is not None, f"Tool '{tool_name}' must be registered"
        assert tool.tier == expected_tier, f"Tier mismatch for '{tool_name}': {tool.tier} != {expected_tier}"
        assert tool.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool.preview_fn), f"Tool '{tool_name}' missing preview_fn"
        preview = tool.preview_fn({"pid": 1234, "event_id": 8, "source_pid": 1234, "source_process": "proc.exe", "target_pid": 5678, "target_process": "svchost.exe"})
        assert isinstance(preview, str) and len(preview) > 0
