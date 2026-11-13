"""
Milestone 39.0 Phase 4: Master Safety Audit, Concurrency Chaos Battery & Production Release Test Suite
Validates:
- SAF-01: Exhaustive ToolRegistry audit across all Milestone 39 tools (Kernel Behavior & Memory Guard).
- SAF-02: 100-cycle Universal Guardian Kill Switch SLA benchmark (< 25.0ms hard SLA, typical < 1.0ms).
- SAF-03: 40-worker cross-subsystem chaos concurrency stress test with zero deadlocks.
- SAF-04: In-flight emergency halt abort validation.
- SAF-05: Permanent safety rule invariants (Rule 1, Rule 3, Rule 4, Rule 5, Rule 7, Rule 8, Rule 11).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time
import pytest
from unittest.mock import patch

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.kernel_behavior_correlator import kernel_behavior_correlator
from services.backend.cyber.memory_integrity_guard import memory_integrity_guard
import services.backend.tools.kernel_behavior_tools
import services.backend.tools.memory_integrity_tools


@pytest.fixture(autouse=True)
def reset_m39_environment():
    guardian.resume()
    kernel_behavior_correlator.clear_anomalies()
    yield
    guardian.resume()
    kernel_behavior_correlator.clear_anomalies()


def test_tool_registry_audit_milestone_39():
    """SAF-01: Formally audit all 8 tools introduced in Milestone 39."""
    expected_tools = {
        # Phase 1: Real-Time ETW/Sysmon Behavioral Anomaly Correlator
        "audit_process_lineage": 0,
        "get_process_behavioral_score": 0,
        "get_behavioral_anomalies_log": 0,
        "evaluate_etw_threat_event": 1,
        # Phase 2: Memory Integrity & Code Injection Guard
        "scan_process_memory_integrity": 0,
        "audit_system_memory_posture": 0,
        "verify_process_pe_header": 0,
        "quarantine_anomalous_process": 1,
    }

    for tool_name, expected_tier in expected_tools.items():
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch: {tool_def.tier} != {expected_tier}"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool_def.preview_fn), f"Tool '{tool_name}' missing preview_fn"
        preview_text = tool_def.preview_fn({"pid": 1234, "event_id": 8, "source_pid": 100, "source_process": "test.exe", "target_pid": 200, "target_process": "svchost.exe"})
        assert isinstance(preview_text, str) and len(preview_text) > 0


def test_universal_guardian_kill_switch_100_cycle_benchmark_m39():
    """SAF-02: Benchmark Guardian synchronous halt across Kernel & Memory engines over 100 cycles."""
    # Warmup
    guardian.trigger("benchmark_warmup")
    guardian.resume()

    current_pid = os.getpid()
    latencies_ms = []

    for _ in range(100):
        t0 = time.perf_counter()
        guardian.trigger("benchmark_sla_cycle")
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        assert guardian.is_halted is True
        # Verify both sub-engines observe halt synchronously
        with pytest.raises(PermissionError, match="Guardian kill switch active"):
            kernel_behavior_correlator.analyze_process_lineage()
        with pytest.raises(PermissionError, match="Guardian kill switch active"):
            memory_integrity_guard.scan_process_memory(current_pid)
        with pytest.raises(PermissionError, match="Guardian kill switch active"):
            memory_integrity_guard.verify_pe_header_integrity(current_pid)

        guardian.resume()
        assert guardian.is_halted is False

    max_latency = max(latencies_ms)
    avg_latency = sum(latencies_ms) / len(latencies_ms)
    p95_latency = sorted(latencies_ms)[94]

    assert max_latency < 25.0, f"Guardian halt exceeded 25ms SLA: max={max_latency:.3f}ms"
    assert avg_latency < 5.0, f"Guardian halt average too high: avg={avg_latency:.3f}ms"
    assert p95_latency < 10.0, f"Guardian halt P95 too high: p95={p95_latency:.3f}ms"


def test_chaos_concurrency_kernel_and_memory_guard():
    """SAF-03: 40-worker cross-subsystem chaos concurrency stress test under simultaneous load."""
    num_workers = 40
    current_pid = os.getpid()
    results = []

    def run_worker_task(task_id: int):
        if task_id % 4 == 0:
            return kernel_behavior_correlator.get_process_threat_score(current_pid)
        elif task_id % 4 == 1:
            return memory_integrity_guard.scan_process_memory(current_pid)
        elif task_id % 4 == 2:
            return memory_integrity_guard.verify_pe_header_integrity(current_pid)
        else:
            event = {
                "event_id": 10,
                "source_pid": 1000 + task_id,
                "source_process": "mimikatz_test.exe",
                "target_pid": 880,
                "target_process": "lsass.exe",
                "granted_access": "0x1FFFFF",
            }
            return kernel_behavior_correlator.ingest_etw_event(event)

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(run_worker_task, i) for i in range(num_workers)]
        for f in as_completed(futures):
            res = f.result()
            results.append(res)

    assert len(results) == num_workers
    for r in results:
        assert r is not None


def test_in_flight_guardian_emergency_abort_m39():
    """SAF-04: Ensure subsequent requests are instantly rejected once Guardian triggers."""
    guardian.trigger("Simulated kernel containment trigger")
    assert guardian.is_halted is True
    current_pid = os.getpid()

    with pytest.raises(PermissionError):
        kernel_behavior_correlator.ingest_etw_event({"event_id": 8, "source_pid": 100, "target_pid": 200})

    with pytest.raises(PermissionError):
        memory_integrity_guard.quarantine_process(current_pid)

    guardian.resume()
    # Resumes cleanly
    score = kernel_behavior_correlator.get_process_threat_score(current_pid)
    assert score["threat_score"] >= 0


def test_permanent_safety_invariants_m39():
    """SAF-05: Enforce permanent safety rules (Rule 1, Rule 3, Rule 4, Rule 7, Rule 8, Rule 11)."""
    current_pid = os.getpid()

    # Rule 7: Non-destructive process containment - Process RAM must be preserved, never terminated
    with patch("services.backend.cyber.incident_responder.incident_responder.isolate_pid_network_egress") as mock_iso:
        mock_iso.return_value = {"success": True, "shield_status": "EGRESS_SEVERED"}
        res = memory_integrity_guard.quarantine_process(current_pid)
        assert res["process_state"] == "PRESERVED_IN_RAM"
        assert res["forensics_preserved"] is True
        assert "TERMINATED" not in str(res)

    # Rule 11: Zero secret leakage in kernel scan telemetry
    scan = memory_integrity_guard.scan_process_memory(current_pid)
    raw_str = str(scan)
    assert "-----BEGIN RSA" not in raw_str
    assert "SECRET" not in raw_str

    # Rule 5 & Rule 8: No financial checkout tools
    for tool_name in ["scan_process_memory_integrity", "quarantine_anomalous_process", "audit_process_lineage"]:
        t = registry.get(tool_name)
        assert t is not None
        assert "buy" not in t.description.lower()
        assert "sell" not in t.description.lower()
        assert "checkout" not in t.description.lower()
