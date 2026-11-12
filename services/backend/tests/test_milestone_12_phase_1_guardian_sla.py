"""
Guardian Kill Switch Sub-25ms SLA Benchmark for Dream Consolidation Engine (SAF-02).
Benchmarks synchronous shutdown latency of DreamConsolidationEngine across 50 cycles.
SLA Requirement: strictly < 25.0 ms (assert < 1.0 ms typical).
"""

import time
import pytest
from services.backend.safety.guardian import GuardianKillSwitch
from services.backend.memory.dream_engine import DreamConsolidationEngine
from services.backend.schemas.dream import DreamPhaseStatus


def test_dream_engine_guardian_halt_sla_benchmark():
    guardian = GuardianKillSwitch()
    engine = DreamConsolidationEngine()

    guardian.add_state_callback(lambda s: engine.halt() if s == "halted" else engine.reset())

    latencies_ms = []

    # Benchmark 50 consecutive synchronous halt cycles
    for i in range(50):
        # Simulate active state
        engine._is_running = True
        engine._phase = DreamPhaseStatus.REPLAYING_TRACES

        t_start = time.perf_counter()
        guardian.trigger(f"benchmark_dream_halt_{i}")
        t_end = time.perf_counter()

        elapsed_ms = (t_end - t_start) * 1000.0
        latencies_ms.append(elapsed_ms)

        # Invariant checks while halted
        assert guardian.is_halted is True
        assert engine.is_halted() is True
        assert engine._is_running is False
        assert engine._phase == DreamPhaseStatus.HALTED

        # Fail closed check
        with pytest.raises(PermissionError):
            engine.run_dream_cycle(force=True)

        with pytest.raises(PermissionError):
            engine.prune_stale_memory()

        # Resume for next cycle
        guardian.resume()
        assert guardian.is_halted is False
        assert engine.is_halted() is False
        assert engine._phase == DreamPhaseStatus.IDLE

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    max_latency = max(latencies_ms)
    min_latency = min(latencies_ms)

    print(f"\n[DREAM ENGINE GUARDIAN SLA BENCHMARK - 50 CYCLES]")
    print(f"  Avg Latency: {avg_latency:.4f} ms")
    print(f"  Max Latency: {max_latency:.4f} ms")
    print(f"  Min Latency: {min_latency:.4f} ms")

    # Hard SLA requirements
    assert avg_latency < 1.0, f"Average halt latency {avg_latency:.4f}ms exceeds 1.0ms target"
    assert max_latency < 25.0, f"Maximum halt latency {max_latency:.4f}ms exceeds 25.0ms SLA"


def test_dream_engine_clean_resumption_after_resume():
    """Verify clean resumption of operations after Guardian resumes."""
    guardian = GuardianKillSwitch()
    engine = DreamConsolidationEngine(idle_threshold_seconds=0.0)

    guardian.add_state_callback(lambda s: engine.halt() if s == "halted" else engine.reset())

    guardian.trigger("lockdown")
    assert engine.is_halted()

    guardian.resume()
    assert not engine.is_halted()

    # Engine should successfully run dream cycle post-resumption
    report = engine.run_dream_cycle(force=True)
    assert report.cycle_id is not None
    assert engine.get_status().phase == "COMPLETED"
