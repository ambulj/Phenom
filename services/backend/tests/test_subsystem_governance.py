import pytest
from services.backend.schemas.subsystem_governance import (
    CircuitBreakerStatus,
    RemediationActionType,
)
from services.backend.governance.watchdog import SubsystemGovernanceWatchdog


def test_subsystem_governance_initialization_and_telemetry():
    watchdog = SubsystemGovernanceWatchdog()
    assert watchdog.is_active

    health = watchdog.get_health()
    assert health.is_active
    assert health.overall_health == 1.0
    assert len(health.subsystems) == 6
    assert "telepresence" in health.subsystems
    assert "voice_action" in health.subsystems


def test_subsystem_governance_error_recording_and_circuit_tripping():
    watchdog = SubsystemGovernanceWatchdog()

    # Record 3 errors -> DEGRADED
    for _ in range(3):
        telem = watchdog.record_telemetry(
            subsystem="voice_action",
            health_score=0.7,
            memory_mb=150.0,
            vram_mb=300.0,
            is_error=True,
        )
    assert telem.circuit_status == CircuitBreakerStatus.DEGRADED

    # Record 2 more errors -> TRIPPED (threshold=5)
    for _ in range(2):
        telem = watchdog.record_telemetry(
            subsystem="voice_action",
            health_score=0.4,
            memory_mb=150.0,
            vram_mb=300.0,
            is_error=True,
        )
    assert telem.circuit_status == CircuitBreakerStatus.TRIPPED

    # Health report should include active anomaly
    health = watchdog.get_health()
    assert len(health.active_anomalies) >= 1
    assert "voice_action circuit tripped" in health.active_anomalies[0]


def test_subsystem_governance_remediation_actions():
    watchdog = SubsystemGovernanceWatchdog()

    # Trip breaker
    for _ in range(5):
        watchdog.record_telemetry("telepresence", 0.3, 200.0, 500.0, is_error=True)

    health_tripped = watchdog.get_health("telepresence")
    assert health_tripped.subsystems["telepresence"].circuit_status == CircuitBreakerStatus.TRIPPED

    # Execute FLUSH_STALE_BUFFERS remediation
    res = watchdog.trigger_remediation("telepresence", RemediationActionType.FLUSH_STALE_BUFFERS)
    assert res.success
    assert "flushed" in res.message

    health_recovered = watchdog.get_health("telepresence")
    assert health_recovered.subsystems["telepresence"].circuit_status == CircuitBreakerStatus.NORMAL

    # Test TRIM_GPU_CACHE
    res_gpu = watchdog.trigger_remediation("telepresence", RemediationActionType.TRIM_GPU_CACHE)
    assert res_gpu.success
    assert "PyTorch" in res_gpu.message


def test_subsystem_governance_configure_thresholds():
    watchdog = SubsystemGovernanceWatchdog()
    cfg = watchdog.configure_thresholds(max_error_count=8, max_memory_mb=4096.0)
    assert cfg["max_error_count"] == 8
    assert cfg["max_memory_mb"] == 4096.0
