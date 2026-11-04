"""
Sub-10ms Synchronous Guardian Kill Switch SLA Benchmark for Biometric Enclaves (SAF-02).
Benchmarks 100 consecutive synchronous Guardian halts of BiometricEnclaveManager.
Asserts average latency < 10.0ms and maximum latency < 25.0ms (hard SLA).
"""

import time
from services.backend.schemas.biometrics import (
    BiometricAuthMethod,
    EnclaveStatus,
    WorkspacePartitionType,
)
from services.backend.security.biometric_enclave import BiometricEnclaveManager


def test_biometric_enclave_guardian_halt_sla_benchmark():
    manager = BiometricEnclaveManager()
    halt_latencies_ms = []

    for i in range(100):
        # Setup: unlock both partitions and issue active credential leases
        token1 = f"pin-personal-{i}"
        token2 = f"pin-prof-{i}"
        manager.unlock_partition(WorkspacePartitionType.PERSONAL, token1, BiometricAuthMethod.WINDOWS_HELLO_PIN)
        manager.unlock_partition(WorkspacePartitionType.PROFESSIONAL, token2, BiometricAuthMethod.TPM_HARDWARE_SEAL)

        # Issue 5 ephemeral leases with allocated memory buffers
        for j in range(5):
            secret_data = f"ephemeral-data-{i}-{j}".encode("utf-8")
            manager.lease_credential(f"service_{j}", secret_data, ttl_seconds=60)

        # Benchmark synchronous halt latency
        t0 = time.perf_counter()
        manager.halt()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        halt_latencies_ms.append(dt_ms)

        # Verify fail-closed states
        state = manager.get_state()
        assert state.partitions[WorkspacePartitionType.PERSONAL.value].status == EnclaveStatus.LOCKED
        assert state.partitions[WorkspacePartitionType.PROFESSIONAL.value].status == EnclaveStatus.LOCKED
        assert len(state.active_leases) == 0
        assert len(manager._partition_keys) == 0

        # Resume for next cycle
        manager.resume()

    avg_ms = sum(halt_latencies_ms) / len(halt_latencies_ms)
    max_ms = max(halt_latencies_ms)
    min_ms = min(halt_latencies_ms)

    print(f"\n[Guardian Biometric Enclave SLA Benchmark] 100 Cycles:")
    print(f"  Avg Latency: {avg_ms:.4f} ms")
    print(f"  Max Latency: {max_ms:.4f} ms")
    print(f"  Min Latency: {min_ms:.4f} ms")

    # Hard SLA verification
    assert avg_ms < 10.0, f"Average halt latency {avg_ms:.4f}ms exceeded 10.0ms target"
    assert max_ms < 25.0, f"Maximum halt latency {max_ms:.4f}ms exceeded 25.0ms hard SLA"
