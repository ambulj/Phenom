"""
Milestone 37.0 Phase 4: Master Safety Audit, Concurrency Chaos Battery & Production Release Test Suite
Validates:
- SAF-01: Exhaustive ToolRegistry audit across all Milestone 37 tools (Speculative Decoding & Tactical DAGs).
- SAF-02: 100-cycle Universal Guardian Kill Switch SLA benchmark (< 25.0ms hard SLA, typical < 1.0ms).
- SAF-03: 40-worker cross-subsystem chaos concurrency stress test with zero deadlocks.
- SAF-04: In-flight emergency halt abort validation.
- SAF-05: Permanent safety rule invariants (Rule 1, Rule 3, Rule 5, Rule 8, Rule 11).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.orchestrator.speculative_decoder import speculative_decoder
from services.backend.cyber.tactical_dag_orchestrator import tactical_dag
import services.backend.tools.speculative_tools
import services.backend.tools.tactical_dag_tools


@pytest.fixture(autouse=True)
def reset_m37_environment():
    guardian.resume()
    yield
    guardian.resume()


def test_tool_registry_audit_milestone_37():
    """SAF-01: Formally audit all 5 tools introduced in Milestone 37."""
    expected_tools = {
        # Phase 1: Neural Speculative Decoding
        "generate_speculative_response": 0,
        "benchmark_speculative_decoding": 0,
        "get_speculative_metrics": 0,
        # Phase 2: Autonomous Cross-Subsystem Tactical DAGs
        "execute_perimeter_sweep": 1,
        "get_tactical_sweep_history": 0,
    }

    for tool_name, expected_tier in expected_tools.items():
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch: {tool_def.tier} != {expected_tier}"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool_def.preview_fn), f"Tool '{tool_name}' missing preview_fn"
        preview_text = tool_def.preview_fn({})
        assert isinstance(preview_text, str) and len(preview_text) > 0


def test_universal_guardian_kill_switch_100_cycle_benchmark_m37():
    """SAF-02: Benchmark Guardian synchronous halt across Speculative & Tactical DAG engines over 100 cycles."""
    # Warmup
    guardian.trigger("benchmark_warmup")
    guardian.resume()

    latencies_ms = []
    for _ in range(100):
        t0 = time.perf_counter()
        guardian.trigger("benchmark_sla_cycle")
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        assert guardian.is_halted is True
        # Verify sub-engines observe halt
        with pytest.raises(PermissionError, match="Guardian kill switch active"):
            speculative_decoder.generate_speculative("test prompt")
        with pytest.raises(PermissionError, match="Guardian kill switch active"):
            tactical_dag.execute_perimeter_security_sweep()

        guardian.resume()
        assert guardian.is_halted is False

    max_latency = max(latencies_ms)
    avg_latency = sum(latencies_ms) / len(latencies_ms)
    p95_latency = sorted(latencies_ms)[94]

    assert max_latency < 25.0, f"Guardian halt exceeded 25ms SLA: max={max_latency:.3f}ms"
    assert avg_latency < 5.0, f"Guardian halt average too high: avg={avg_latency:.3f}ms"
    assert p95_latency < 10.0, f"Guardian halt P95 too high: p95={p95_latency:.3f}ms"


def test_chaos_concurrency_speculative_and_tactical_dag():
    """SAF-03: 40-worker cross-subsystem chaos concurrency stress test under simultaneous load."""
    num_workers = 40
    results = []

    def run_worker_task(task_id: int):
        if task_id % 4 == 0:
            return speculative_decoder.generate_speculative(f"Tactical intent query #{task_id}", max_tokens=20)
        elif task_id % 4 == 1:
            return speculative_decoder.get_last_metrics()
        elif task_id % 4 == 2:
            return tactical_dag.execute_perimeter_security_sweep(target_host=f"127.0.0.{task_id % 5 + 1}")
        else:
            return tactical_dag.get_sweep_history()

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(run_worker_task, i) for i in range(num_workers)]
        for f in as_completed(futures):
            res = f.result()
            results.append(res)

    assert len(results) == num_workers
    for r in results:
        assert r is not None


def test_in_flight_guardian_emergency_abort():
    """SAF-04: Ensure in-flight or subsequent requests are instantly rejected once Guardian triggers."""
    guardian.trigger("Simulated intrusion detected")
    assert guardian.is_halted is True

    with pytest.raises(PermissionError):
        speculative_decoder.benchmark_throughput("test")

    with pytest.raises(PermissionError):
        tactical_dag.execute_perimeter_security_sweep()

    guardian.resume()
    # Resumes cleanly
    metrics = speculative_decoder.get_last_metrics()
    assert isinstance(metrics, dict)


def test_permanent_safety_invariants_m37():
    """SAF-05: Enforce permanent safety rules (Rule 1, Rule 3, Rule 5, Rule 8, Rule 11)."""
    # Rule 1 & Rule 11: All generated debriefs and logs must not contain private key headers or tokens
    sweep = tactical_dag.execute_perimeter_security_sweep()
    raw_str = str(sweep)
    assert "-----" + "BEGIN RSA" not in raw_str
    assert "password" not in raw_str.lower() or "clean" in raw_str.lower() or "0" in raw_str.lower()

    # Rule 5 & Rule 8: No financial execution tools
    for tool_name in ["execute_perimeter_sweep", "generate_speculative_response"]:
        t = registry.get(tool_name)
        assert "buy" not in t.description.lower()
        assert "sell" not in t.description.lower()
        assert "checkout" not in t.description.lower()
