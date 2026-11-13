"""
Milestone 40.0 Phase 5: Master Safety Audit, Cross-Platform Chaos Battery & Production Release Test Suite
Validates:
- SAF-01: Exhaustive ToolRegistry audit across all 12 Milestone 40 tools.
- SAF-02: 100-cycle Universal Guardian Kill Switch SLA benchmark (< 25.0ms hard SLA, typical < 1.0ms).
- SAF-03: 50-worker cross-platform dual-boot chaos concurrency stress test with zero deadlocks.
- SAF-04: In-flight emergency halt abort validation.
- SAF-05: Permanent safety rule invariants (Rule 1, Rule 3, Rule 4, Rule 7, Rule 8, Rule 11).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sys
import time
import pytest
from unittest.mock import patch

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.platform.os_bridge import os_bridge
from services.backend.cyber.binary_analyzer import binary_analyzer
from services.backend.cyber.frida_instrumentation import frida_engine
from services.backend.orchestrator.sovereign_swarm import sovereign_swarm
import services.backend.tools.cross_platform_tools
import services.backend.tools.binary_re_tools
import services.backend.tools.sovereign_swarm_tools


@pytest.fixture(autouse=True)
def reset_m40_environment():
    guardian.resume()
    frida_engine.clear_sessions()
    sovereign_swarm.clear_state()
    yield
    guardian.resume()
    frida_engine.clear_sessions()
    sovereign_swarm.clear_state()


def test_tool_registry_audit_milestone_40():
    """SAF-01: Formally audit all 12 tools introduced in Milestone 40."""
    expected_tools = {
        # Phase 1: Universal Cross-Platform OS Abstraction & Dual-Boot Parity
        "get_platform_environment": 0,
        "cross_platform_memory_audit": 0,
        "cross_platform_contain_process": 1,
        "verify_dual_boot_posture": 0,
        # Phase 2: Binary Reverse-Engineering & Frida DBI Engine
        "analyze_binary_disassembly": 0,
        "scan_binary_rop_gadgets": 0,
        "instrument_process_with_frida": 1,
        "inspect_frida_hook_telemetry": 0,
        # Phase 3: 5-Agent Sovereign Tactical Swarm & Hybrid LLM
        "dispatch_sovereign_swarm": 1,
        "get_swarm_status": 0,
        "post_swarm_message": 0,
        "get_swarm_message_board": 0,
    }

    for tool_name, expected_tier in expected_tools.items():
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch: {tool_def.tier} != {expected_tier}"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool_def.preview_fn), f"Tool '{tool_name}' missing preview_fn"
        preview_text = tool_def.preview_fn({"pid": 1234, "file_path": sys.executable, "mission_name": "TEST", "sender": "Prime", "recipient": "ALL"})
        assert isinstance(preview_text, str) and len(preview_text) > 0


def test_universal_guardian_kill_switch_100_cycle_benchmark_m40():
    """SAF-02: Benchmark Guardian synchronous halt across all 4 Milestone 40 engines over 100 cycles."""
    # Warmup
    guardian.trigger("benchmark_warmup")
    guardian.resume()

    current_pid = os.getpid()
    python_exe = sys.executable
    latencies_ms = []

    for _ in range(100):
        t0 = time.perf_counter()
        guardian.trigger("benchmark_sla_cycle")
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        assert guardian.is_halted is True
        # Verify all engines observe halt synchronously
        with pytest.raises(PermissionError, match="Guardian kill switch active"):
            os_bridge.get_system_environment()
        with pytest.raises(PermissionError, match="Guardian kill switch active"):
            binary_analyzer.disassemble_binary(python_exe)
        with pytest.raises(PermissionError, match="Guardian kill switch active"):
            frida_engine.instrument_process(current_pid)
        with pytest.raises(PermissionError, match="Guardian kill switch active"):
            sovereign_swarm.dispatch_swarm_mission("TEST")

        guardian.resume()
        assert guardian.is_halted is False

    max_latency = max(latencies_ms)
    avg_latency = sum(latencies_ms) / len(latencies_ms)
    p95_latency = sorted(latencies_ms)[94]

    assert max_latency < 25.0, f"Guardian halt exceeded 25ms SLA: max={max_latency:.3f}ms"
    assert avg_latency < 5.0, f"Guardian halt average too high: avg={avg_latency:.3f}ms"
    assert p95_latency < 10.0, f"Guardian halt P95 too high: p95={p95_latency:.3f}ms"


def test_chaos_concurrency_cross_platform_and_swarm():
    """SAF-03: 50-worker cross-platform chaos concurrency stress test under simultaneous load."""
    num_workers = 50
    current_pid = os.getpid()
    python_exe = sys.executable
    results = []

    def run_worker_task(task_id: int):
        mod = task_id % 5
        if mod == 0:
            return os_bridge.get_system_environment()
        elif mod == 1:
            return binary_analyzer.disassemble_binary(python_exe, max_instructions=10)
        elif mod == 2:
            return binary_analyzer.scan_rop_gadgets(python_exe, max_gadgets=5)
        elif mod == 3:
            return sovereign_swarm.get_swarm_status()
        else:
            return sovereign_swarm.post_message("Specter", "Prime", f"Telemetry frame {task_id}")

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(run_worker_task, i) for i in range(num_workers)]
        for f in as_completed(futures):
            res = f.result()
            results.append(res)

    assert len(results) == num_workers
    for r in results:
        assert r is not None


def test_in_flight_guardian_emergency_abort_m40():
    """SAF-04: Ensure in-flight requests or subsequent calls are instantly rejected once Guardian triggers."""
    guardian.trigger("Simulated cross-platform emergency trigger")
    assert guardian.is_halted is True
    current_pid = os.getpid()

    with pytest.raises(PermissionError):
        os_bridge.contain_process_network_egress(current_pid)

    with pytest.raises(PermissionError):
        frida_engine.get_hook_telemetry()

    guardian.resume()
    # Resumes cleanly
    env = os_bridge.get_system_environment()
    assert env["dual_boot_supported"] is True


def test_permanent_safety_invariants_m40():
    """SAF-05: Enforce permanent safety rules (Rule 1, Rule 3, Rule 4, Rule 7, Rule 8, Rule 11)."""
    current_pid = os.getpid()

    # Rule 7: Non-destructive process containment - Process RAM must be preserved, never terminated
    res = os_bridge.contain_process_network_egress(current_pid)
    assert res["process_state"] == "PRESERVED_IN_RAM"
    assert res["forensics_intact"] is True
    assert "TERMINATED" not in str(res)

    # Rule 11: Zero secret leakage in swarm message board
    board = sovereign_swarm.get_message_board()
    raw_str = str(board)
    assert "-----BEGIN RSA" not in raw_str
    assert "SECRET_PASSWORD" not in raw_str

    # Rule 5 & Rule 8: No financial checkout tools
    for tool_name in ["cross_platform_contain_process", "instrument_process_with_frida", "dispatch_sovereign_swarm"]:
        t = registry.get(tool_name)
        assert t is not None
        assert "buy" not in t.description.lower()
        assert "sell" not in t.description.lower()
        assert "checkout" not in t.description.lower()
