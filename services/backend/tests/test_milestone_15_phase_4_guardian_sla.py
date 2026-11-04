import time
import pytest
from services.backend.voice_action import streaming_voice_action_kernel
from services.backend.cognitive_twin import cognitive_twin_manager
from services.backend.governance import subsystem_governance_watchdog
from services.backend.mesh_protocol import local_mesh_peer_discovery


def test_milestone_15_universal_guardian_halt_sla_benchmark():
    """
    Universal 100-cycle synchronous Guardian halt benchmark executed simultaneously
    across all 4 Milestone 15 subsystems.
    Hard SLA: < 25.0ms. Target: < 1.0ms typical.
    """
    latencies = []

    for _ in range(100):
        # Reset and prime all 4 subsystems
        streaming_voice_action_kernel.reset()
        cognitive_twin_manager.reset()
        subsystem_governance_watchdog.reset()
        local_mesh_peer_discovery.reset()

        streaming_voice_action_kernel.start_session("sla-universal")
        streaming_voice_action_kernel.ingest_chunk(0.3, 0.8)
        cognitive_twin_manager.ingest_episode("Active SLA testing episode")
        subsystem_governance_watchdog.record_telemetry("voice_action", 0.95, 120.0, 250.0)
        local_mesh_peer_discovery.register_peer("peer-sla", "Peer SLA", "192.168.1.99")

        # Measure simultaneous synchronous halt
        start = time.perf_counter()
        streaming_voice_action_kernel.halt()
        cognitive_twin_manager.halt()
        subsystem_governance_watchdog.halt()
        local_mesh_peer_discovery.halt()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        latencies.append(elapsed_ms)

        assert not streaming_voice_action_kernel.is_listening
        assert cognitive_twin_manager.is_locked
        assert not subsystem_governance_watchdog.is_active
        assert not local_mesh_peer_discovery.is_advertising

    streaming_voice_action_kernel.reset()
    cognitive_twin_manager.reset()
    subsystem_governance_watchdog.reset()
    local_mesh_peer_discovery.reset()

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    print(f"\n[Milestone 15 Universal Guardian SLA Benchmark] 100 Simultaneous Cycles across 4 Subsystems:")
    print(f"  Avg Latency: {avg_latency:.4f} ms")
    print(f"  Max Latency: {max_latency:.4f} ms")
    print(f"  Min Latency: {min_latency:.4f} ms")

    assert avg_latency < 1.0, f"Average simultaneous Guardian halt latency ({avg_latency:.4f}ms) exceeded 1.0ms target"
    assert max_latency < 25.0, f"Max simultaneous Guardian halt latency ({max_latency:.4f}ms) exceeded 25.0ms hard SLA"
