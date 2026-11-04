"""
Universal Guardian Kill Switch Sub-25ms SLA Benchmark for Milestone 13.0 (SAF-02).
Benchmarks 100 consecutive synchronous Guardian halts executed simultaneously
across all 6 Milestone 13 subsystems:
- LocalAdapterManager (EVO-01)
- VolumetricCanvasManager (VOL-01)
- VisionGestureTracker (VOL-01)
- SwarmNodeManager (SWM-01)
- SwarmWorkloadScheduler (SWM-01)
- KernelTelemetryFabric (KER-01)
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.evolution.adapter_manager import local_adapter_manager
from services.backend.volumetric.canvas_manager import volumetric_canvas_manager
from services.backend.volumetric.gesture_tracker import vision_gesture_tracker
from services.backend.swarm_compute.node_manager import swarm_node_manager
from services.backend.swarm_compute.workload_scheduler import swarm_workload_scheduler
from services.backend.kernel.telemetry_listener import kernel_telemetry_fabric


def test_milestone_13_universal_guardian_halt_sla_benchmark():
    guardian.resume()
    local_adapter_manager.reset()
    volumetric_canvas_manager.reset()
    swarm_workload_scheduler.reset()
    kernel_telemetry_fabric.reset()

    latencies = []
    iterations = 100

    for i in range(iterations):
        # 1. Setup active state in all subsystems
        local_adapter_manager.train_adapter(f"adapter_{i}", domain="coding", epochs=1)
        volumetric_canvas_manager.spawn_node(label=f"Card_{i}", x=0.1, y=0.1, z=1.5)
        swarm_workload_scheduler.dispatch_workload("EMBEDDING_BATCH", items_count=2)
        kernel_telemetry_fabric.ingest_crash_event(process_name="test.exe", exception_code="ModuleNotFoundError")

        # 2. Synchronous halt measurement across all 6 subsystems
        t0 = time.perf_counter()
        local_adapter_manager.halt()
        volumetric_canvas_manager.halt()
        vision_gesture_tracker.halt()
        swarm_node_manager.halt()
        swarm_workload_scheduler.halt()
        kernel_telemetry_fabric.halt()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        latencies.append(elapsed_ms)

        # 3. Verify invariant lockdowns
        assert local_adapter_manager.is_halted() is True
        assert volumetric_canvas_manager.is_halted() is True
        assert vision_gesture_tracker.is_halted() is True
        assert swarm_node_manager.is_halted() is True
        assert swarm_workload_scheduler.is_halted() is True
        assert kernel_telemetry_fabric.is_halted() is True

        # 4. Reset for next cycle
        local_adapter_manager.reset()
        volumetric_canvas_manager.reset()
        swarm_workload_scheduler.reset()
        kernel_telemetry_fabric.reset()

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    print(f"\n[Milestone 13 Universal Guardian SLA Benchmark] 100 Simultaneous Cycles across 6 Subsystems:")
    print(f"  Avg Latency: {avg_latency:.4f} ms")
    print(f"  Max Latency: {max_latency:.4f} ms")
    print(f"  Min Latency: {min_latency:.4f} ms")

    # Hard SLA verification
    assert avg_latency < 1.0, f"Average halt latency {avg_latency:.4f}ms exceeds target 1.0ms"
    assert max_latency < 25.0, f"Max halt latency {max_latency:.4f}ms exceeds hard limit 25.0ms"
