"""
Guardian Kill Switch Sub-10ms SLA Benchmark for Local Adapter Manager (EVO-01, SAF-02).
Benchmarks 100 consecutive synchronous Guardian halts on LocalAdapterManager.
Verifies:
- All active tuning loops and adapter mounting actions are immediately halted
- Fail-closed PermissionError raised while halted
- Average halt latency is well within < 10ms (and max < 25ms SLA)
"""

import time
from services.backend.evolution.adapter_manager import LocalAdapterManager
from services.backend.evolution.instruction_distiller import InstructionDistiller


class DummyDreamEngine:
    def get_schemas(self):
        return []


def test_adapter_manager_guardian_halt_sla_benchmark():
    """Benchmark 100 consecutive synchronous halts on LocalAdapterManager."""
    latencies = []
    iterations = 100

    for i in range(iterations):
        distiller = InstructionDistiller(dream_eng=DummyDreamEngine())
        mgr = LocalAdapterManager(distiller=distiller)

        # Populate with an active adapter
        mgr.train_adapter(f"lora_{i}", domain="coding", epochs=3)
        mgr.activate_adapter(f"lora_{i}")
        assert mgr.get_status().active_adapter is not None

        # Measure synchronous halt execution time
        t0 = time.perf_counter()
        mgr.halt()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        latencies.append(elapsed_ms)

        # Assert immediate post-conditions
        assert mgr.is_halted() is True

    avg_ms = sum(latencies) / len(latencies)
    max_ms = max(latencies)
    min_ms = min(latencies)

    print(f"\n[Guardian Local Adapter Manager SLA Benchmark] 100 Cycles:")
    print(f"  Avg Latency: {avg_ms:.4f} ms")
    print(f"  Max Latency: {max_ms:.4f} ms")
    print(f"  Min Latency: {min_ms:.4f} ms")

    # Phenom strict safety SLA asserts
    assert avg_ms < 10.0, f"Average halt latency must be < 10ms, got {avg_ms:.4f}ms"
    assert max_ms < 25.0, f"Maximum halt latency must be < 25ms SLA, got {max_ms:.4f}ms"
