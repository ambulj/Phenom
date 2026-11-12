"""
Guardian Kill Switch Sub-10ms SLA Benchmark for Spatial Canvas (OVR-01, SAF-02).
Benchmarks 100 consecutive synchronous Guardian halts on SpatialCanvasManager and FocusTrackingEngine.
Verifies:
- All active annotations are immediately purged
- Overlay state is de-activated
- Average halt latency is well within < 10ms (and max < 25ms SLA)
"""

import time
from services.backend.safety.guardian import guardian
from services.backend.spatial.canvas_manager import SpatialCanvasManager
from services.backend.spatial.focus_tracker import FocusTrackingEngine


def test_spatial_canvas_guardian_halt_sla_benchmark():
    """Benchmark 100 consecutive synchronous halts on SpatialCanvasManager."""
    latencies = []
    iterations = 100

    for i in range(iterations):
        tracker = FocusTrackingEngine()
        canvas = SpatialCanvasManager(focus_tracker=tracker)

        # Populate with floating annotations
        for j in range(5):
            canvas.add_annotation(
                title=f"Annotation {j}",
                content=f"Sample note content {j}",
                anchor="top-right",
            )
        assert len(canvas.get_state().annotations) == 5
        assert canvas.get_state().is_active is True

        # Measure synchronous halt execution time
        t0 = time.perf_counter()
        canvas.halt()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        latencies.append(elapsed_ms)

        # Assert immediate post-conditions
        assert canvas.is_halted() is True
        assert canvas.get_state().is_active is False
        assert len(canvas.get_state().annotations) == 0
        assert tracker.is_halted() is True

    avg_ms = sum(latencies) / len(latencies)
    max_ms = max(latencies)
    min_ms = min(latencies)

    print(f"\n[Guardian Spatial Canvas SLA Benchmark] 100 Cycles:")
    print(f"  Avg Latency: {avg_ms:.4f} ms")
    print(f"  Max Latency: {max_ms:.4f} ms")
    print(f"  Min Latency: {min_ms:.4f} ms")

    # Phenom strict safety SLA asserts
    assert avg_ms < 10.0, f"Average halt latency must be < 10ms, got {avg_ms:.4f}ms"
    assert max_ms < 25.0, f"Maximum halt latency must be < 25ms SLA, got {max_ms:.4f}ms"
