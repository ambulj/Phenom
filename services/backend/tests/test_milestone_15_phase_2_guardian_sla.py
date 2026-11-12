import time
import pytest
from services.backend.cognitive_twin import cognitive_twin_manager
from services.backend.schemas.cognitive_twin import EpisodicNodeType


def test_cognitive_twin_guardian_halt_sla_benchmark():
    """
    Benchmark 100 consecutive synchronous Guardian halt cycles on CognitiveTwinManager.
    Hard SLA: < 10.0ms. Target: < 1.0ms typical.
    """
    latencies = []

    for _ in range(100):
        cognitive_twin_manager.reset()
        cognitive_twin_manager.ingest_episode("Active context task", node_type=EpisodicNodeType.ACTIVITY)

        start = time.perf_counter()
        cognitive_twin_manager.halt()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        latencies.append(elapsed_ms)
        assert cognitive_twin_manager.is_locked
        assert len(cognitive_twin_manager._active_node_ids) == 0

    cognitive_twin_manager.reset()

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    print(f"\n[Guardian Cognitive Twin SLA Benchmark] 100 Cycles:")
    print(f"  Avg Latency: {avg_latency:.4f} ms")
    print(f"  Max Latency: {max_latency:.4f} ms")
    print(f"  Min Latency: {min_latency:.4f} ms")

    assert avg_latency < 1.0, f"Average Guardian halt latency ({avg_latency:.4f}ms) exceeded 1.0ms target"
    assert max_latency < 10.0, f"Max Guardian halt latency ({max_latency:.4f}ms) exceeded 10.0ms hard SLA"
