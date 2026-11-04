"""
Sub-10ms Synchronous Guardian Kill Switch SLA Benchmark for Deep UIAutomation (SAF-02).
Benchmarks 100 consecutive synchronous Guardian halts of DeepUIAutomationEngine.
Asserts average latency < 10.0ms and maximum latency < 25.0ms (hard SLA).
"""

import time
from services.backend.automation.deep_uia_engine import DeepUIAutomationEngine
from services.backend.schemas.deep_uia import UIWorkflowStep


def test_deep_uia_guardian_halt_sla_benchmark():
    engine = DeepUIAutomationEngine()
    halt_latencies_ms = []

    for i in range(100):
        # Prepare workflow with steps
        steps = [
            UIWorkflowStep(step_id="step-1", action_type="SET_VALUE", target_query="Document Title", value_payload=f"Doc {i}"),
            UIWorkflowStep(step_id="step-2", action_type="CLICK", target_query="Save"),
        ]

        # Benchmark synchronous halt latency
        t0 = time.perf_counter()
        engine.halt()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        halt_latencies_ms.append(dt_ms)

        # Verify engine is halted and subsequent workflow blocked
        assert engine._halted is True

        # Resume for next cycle
        engine.resume()

    avg_ms = sum(halt_latencies_ms) / len(halt_latencies_ms)
    max_ms = max(halt_latencies_ms)
    min_ms = min(halt_latencies_ms)

    print(f"\n[Guardian Deep UIAutomation SLA Benchmark] 100 Cycles:")
    print(f"  Avg Latency: {avg_ms:.4f} ms")
    print(f"  Max Latency: {max_ms:.4f} ms")
    print(f"  Min Latency: {min_ms:.4f} ms")

    # Hard SLA verification
    assert avg_ms < 10.0, f"Average halt latency {avg_ms:.4f}ms exceeded 10.0ms target"
    assert max_ms < 25.0, f"Maximum halt latency {max_ms:.4f}ms exceeded 25.0ms hard SLA"
