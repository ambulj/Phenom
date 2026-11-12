import time
import pytest
from services.backend.governance import subsystem_governance_watchdog


def test_subsystem_governance_guardian_halt_sla_benchmark():
    """
    Benchmark 100 consecutive synchronous Guardian halt cycles on SubsystemGovernanceWatchdog.
    Hard SLA: < 10.0ms. Target: < 1.0ms typical.
    """
    latencies = []

    for _ in range(100):
        subsystem_governance_watchdog.reset()
        subsystem_governance_watchdog.record_telemetry("voice_action", 0.9, 100.0, 200.0)

        start = time.perf_counter()
        subsystem_governance_watchdog.halt()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        latencies.append(elapsed_ms)
        assert not subsystem_governance_watchdog.is_active

    subsystem_governance_watchdog.reset()

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    print(f"\n[Guardian Subsystem Governance SLA Benchmark] 100 Cycles:")
    print(f"  Avg Latency: {avg_latency:.4f} ms")
    print(f"  Max Latency: {max_latency:.4f} ms")
    print(f"  Min Latency: {min_latency:.4f} ms")

    assert avg_latency < 1.0, f"Average Guardian halt latency ({avg_latency:.4f}ms) exceeded 1.0ms target"
    assert max_latency < 10.0, f"Max Guardian halt latency ({max_latency:.4f}ms) exceeded 10.0ms hard SLA"
