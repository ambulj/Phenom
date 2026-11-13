"""
Unit test suite for Phenom Memory Integrity & Code Injection Guard (MEMGUARD-02)
Tests:
1. scan_process_memory against current process (os.getpid())
2. verify_pe_header_integrity against current process
3. audit_system_rwx_pages with process count limit
4. quarantine_process verifies non-destructive egress shield integration
5. Guardian emergency abort (<25ms SLA) enforces immediate halt
6. ToolRegistry registration audit for memory integrity tools
"""

import os
import sys
import time
import pytest
from unittest.mock import patch, MagicMock

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.memory_integrity_guard import MemoryIntegrityGuard, memory_integrity_guard
import services.backend.tools.memory_integrity_tools as mit


@pytest.fixture(autouse=True)
def ensure_guardian_reset():
    guardian.resume()
    yield
    guardian.resume()


def test_scan_process_memory_current_pid():
    """Verify scan_process_memory audits the active test process."""
    current_pid = os.getpid()
    guard = MemoryIntegrityGuard()
    res = guard.scan_process_memory(current_pid)

    assert res["pid"] == current_pid
    assert res["process_name"] != "unknown"
    assert "total_pages_scanned" in res
    assert "rwx_pages_count" in res
    assert "unbacked_exec_pages_count" in res
    assert res["threat_verdict"] in ["CLEAN", "SUSPICIOUS", "CRITICAL"]
    assert "elapsed_ms" in res
    assert res["elapsed_ms"] >= 0.0
    assert len(guard.get_scan_history()) >= 1


def test_verify_pe_header_integrity_current_pid():
    """Verify verify_pe_header_integrity inspects DOS/NT headers cleanly."""
    current_pid = os.getpid()
    guard = MemoryIntegrityGuard()
    res = guard.verify_pe_header_integrity(current_pid)

    assert res["pid"] == current_pid
    assert "header_integrity" in res
    assert res["dos_signature"] == "0x5A4D (MZ)"
    assert res["status"] in ["PE_HEADER_VALID", "PE_HEADER_CORRUPTED_OR_HOLLOWED"]
    assert "T1055.012" in res["mitre_technique"]


def test_audit_system_rwx_pages_bounded():
    """Verify system-wide RWX page auditing works within max_processes boundary."""
    guard = MemoryIntegrityGuard()
    res = guard.audit_system_rwx_pages(max_processes=5)

    assert "total_processes_audited" in res
    assert res["total_processes_audited"] <= 5
    assert "anomalous_processes_count" in res
    assert "flagged_processes" in res
    assert res["system_memory_posture"] in ["SECURE", "ANOMALIES_DETECTED"]


def test_quarantine_process_non_destructive():
    """Verify quarantine_process invokes non-destructive network isolation."""
    current_pid = os.getpid()
    guard = MemoryIntegrityGuard()

    with patch("services.backend.cyber.incident_responder.incident_responder.isolate_pid_network_egress") as mock_isolate:
        mock_isolate.return_value = {"success": True, "pid": current_pid, "shield_status": "EGRESS_SEVERED"}
        res = guard.quarantine_process(current_pid)

        assert res["pid"] == current_pid
        assert res["quarantine_action"] == "NETSH_EGRESS_BLOCKED"
        assert res["process_state"] == "PRESERVED_IN_RAM"
        assert res["forensics_preserved"] is True
        assert res["shield_status"]["success"] is True
        mock_isolate.assert_called_once_with(current_pid)


def test_guardian_abort_sla_memory_guard():
    """Verify Guardian emergency kill switch aborts memory operations instantly (<25ms SLA)."""
    guard = MemoryIntegrityGuard()
    current_pid = os.getpid()

    # Trigger kill switch
    t0 = time.perf_counter()
    guardian.trigger("Test memory emergency abort")
    abort_latency_ms = (time.perf_counter() - t0) * 1000.0
    assert abort_latency_ms < 25.0, f"Guardian trigger exceeded 25ms SLA: {abort_latency_ms}ms"

    # Verify all operations raise PermissionError synchronously
    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        guard.scan_process_memory(current_pid)

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        guard.verify_pe_header_integrity(current_pid)

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        guard.quarantine_process(current_pid)

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        guard.audit_system_rwx_pages(max_processes=5)


def test_memory_integrity_tool_registry():
    """Verify all 4 memory integrity tools are registered with correct safety tiers and schemas."""
    expected_tools = {
        "scan_process_memory_integrity": 0,
        "audit_system_memory_posture": 0,
        "verify_process_pe_header": 0,
        "quarantine_anomalous_process": 1,
    }

    for tool_name, expected_tier in expected_tools.items():
        meta = registry.get(tool_name)
        assert meta is not None, f"Tool {tool_name} not registered in ToolRegistry"
        assert meta.tier == expected_tier, f"Tool {tool_name} tier mismatch: expected {expected_tier}, got {meta.tier}"
        assert meta.args_schema is not None
        assert callable(meta.preview_fn)
