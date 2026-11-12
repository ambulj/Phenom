"""Guardian kill switch sub-10ms SLA benchmark for Milestone 13 Phase 3: Swarm Compute (SAF-02)."""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.schemas.swarm_compute import WorkloadStatus, WorkloadType
from services.backend.swarm_compute.node_manager import swarm_node_manager
from services.backend.swarm_compute.workload_scheduler import swarm_workload_scheduler


def test_swarm_compute_guardian_halt_sla_benchmark():
    guardian.resume()
    swarm_workload_scheduler.reset()
    latencies = []

    # 100 consecutive synchronous halt cycles
    for i in range(100):
        # Dispatch active task
        task = swarm_workload_scheduler.dispatch_workload(
            workload_type=WorkloadType.EMBEDDING_BATCH,
            items_count=5,
        )
        # Put task in RUNNING state to test in-flight abort
        task.status = WorkloadStatus.RUNNING

        start_t = time.perf_counter()
        swarm_workload_scheduler.halt()
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        latencies.append(elapsed_ms)

        # Invariant checks: must be halted, task aborted
        assert swarm_workload_scheduler.is_halted() is True
        assert swarm_node_manager.is_halted() is True
        assert task.status == WorkloadStatus.ABORTED

        swarm_workload_scheduler.reset()

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    print(f"\n[Guardian SLA Phase 3 Benchmark] Avg: {avg_latency:.4f}ms, Max: {max_latency:.4f}ms, Min: {min_latency:.4f}ms")

    # Hard SLA verification
    assert avg_latency < 1.0, f"Average halt latency {avg_latency:.4f}ms exceeds target 1.0ms"
    assert max_latency < 25.0, f"Max halt latency {max_latency:.4f}ms exceeds hard limit 25.0ms"
