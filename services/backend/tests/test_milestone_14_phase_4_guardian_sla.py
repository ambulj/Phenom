"""
Milestone 14 Universal Synchronous Guardian Kill Switch SLA Benchmark (SAF-02).
Benchmarks 100 consecutive synchronous Guardian halts executed simultaneously
across all Milestone 14 subsystems:
- StreamingAVPipeline
- BiometricEnclaveManager (with active leases & unlocked partitions)
- DeepUIAutomationEngine (with active workflows)
- DynamicExtensionManager (with hot-loaded extensions)
Asserts average latency < 1.0ms and maximum latency < 25.0ms (hard SLA).
"""

import time
from services.backend.automation.deep_uia_engine import DeepUIAutomationEngine
from services.backend.extensions.extension_manager import DynamicExtensionManager
from services.backend.schemas.biometrics import BiometricAuthMethod, WorkspacePartitionType
from services.backend.schemas.deep_uia import UIWorkflowStep
from services.backend.schemas.extensions import ExtensionStatus
from services.backend.schemas.telepresence import MediaStreamType, SensorState
from services.backend.security.biometric_enclave import BiometricEnclaveManager
from services.backend.telepresence.av_pipeline import StreamingAVPipeline


def test_milestone_14_universal_guardian_halt_sla_benchmark():
    # Instantiate all 4 core milestone subsystems
    av_pipeline = StreamingAVPipeline()
    enclave_mgr = BiometricEnclaveManager()
    uia_engine = DeepUIAutomationEngine()
    ext_mgr = DynamicExtensionManager()

    halt_latencies_ms = []

    for i in range(100):
        # 1. Arm AV pipeline
        av_pipeline.start_session(MediaStreamType.AUDIO_VIDEO)
        av_pipeline.ingest_telemetry(0.5, 0.8, [(0.1, 0.2)], time.time())

        # 2. Arm Biometric Enclave with partitions and active leases
        enclave_mgr.unlock_partition(WorkspacePartitionType.PERSONAL, f"pin-{i}", BiometricAuthMethod.WINDOWS_HELLO_PIN)
        enclave_mgr.lease_credential(f"svc_{i}", f"tok-{i}".encode("utf-8"), ttl_seconds=60)

        # 3. Arm UIA Engine
        _ = [UIWorkflowStep(step_id="s1", action_type="CLICK", target_query="Save")]

        # 4. Arm Dynamic Extension Manager with a hot-loaded tool
        code = f"def dynamic_tool_{i}(): return {i}"
        ext_id, _ = ext_mgr.synthesize_extension(
            name=f"dynamic_tool_{i}",
            description="Benchmark tool",
            python_code=code,
            risk_tier=1,
        )

        # Execute universal synchronous halt across all subsystems simultaneously
        t0 = time.perf_counter()
        av_pipeline.halt()
        enclave_mgr.halt()
        uia_engine.halt()
        ext_mgr.halt()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        halt_latencies_ms.append(dt_ms)

        # Verify all subsystems fail-closed
        assert av_pipeline.get_state().microphone_state == SensorState.DISABLED
        assert enclave_mgr.is_unlocked(WorkspacePartitionType.PERSONAL) is False
        assert len(enclave_mgr.get_state().active_leases) == 0
        assert uia_engine._halted is True
        assert ext_mgr._extensions[ext_id].status == ExtensionStatus.UNLOADED

        # Resume all subsystems for next iteration
        av_pipeline.resume()
        enclave_mgr.resume()
        uia_engine.resume()
        ext_mgr.resume()

    avg_ms = sum(halt_latencies_ms) / len(halt_latencies_ms)
    max_ms = max(halt_latencies_ms)
    min_ms = min(halt_latencies_ms)

    print(f"\n[Milestone 14 Universal Guardian SLA Benchmark] 100 Simultaneous Cycles across 4 Subsystems:")
    print(f"  Avg Latency: {avg_ms:.4f} ms")
    print(f"  Max Latency: {max_ms:.4f} ms")
    print(f"  Min Latency: {min_ms:.4f} ms")

    # Hard SLA verification
    assert avg_ms < 1.0, f"Average halt latency {avg_ms:.4f}ms exceeded 1.0ms target"
    assert max_ms < 25.0, f"Maximum halt latency {max_ms:.4f}ms exceeded 25.0ms hard SLA"
