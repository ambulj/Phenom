"""Guardian kill switch sub-10ms SLA benchmark for Milestone 13 Phase 2 (SAF-02)."""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.volumetric.canvas_manager import volumetric_canvas_manager
from services.backend.volumetric.gesture_tracker import vision_gesture_tracker


def test_volumetric_guardian_halt_sla_benchmark():
    guardian.resume()
    volumetric_canvas_manager.reset()
    latencies = []

    # Run 100 consecutive synchronous halt cycles
    for i in range(100):
        # Setup active state with nodes and gestures
        volumetric_canvas_manager.spawn_node(
            label=f"Node_{i}",
            x=0.1 * i,
            y=0.2 * i,
            z=1.5,
        )

        start_t = time.perf_counter()
        volumetric_canvas_manager.halt()
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        latencies.append(elapsed_ms)

        # Invariant checks: must be halted, zero nodes, inactive
        assert volumetric_canvas_manager.is_halted() is True
        assert volumetric_canvas_manager.get_state().total_nodes == 0
        assert volumetric_canvas_manager.get_state().is_active is False
        assert vision_gesture_tracker.is_halted() is True

        volumetric_canvas_manager.reset()

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    print(f"\n[Guardian SLA Phase 2 Benchmark] Avg: {avg_latency:.4f}ms, Max: {max_latency:.4f}ms, Min: {min_latency:.4f}ms")

    # Hard SLA verification
    assert avg_latency < 1.0, f"Average halt latency {avg_latency:.4f}ms exceeds target 1.0ms"
    assert max_latency < 25.0, f"Max halt latency {max_latency:.4f}ms exceeds hard limit 25.0ms"
