"""
Milestone 11.0 Phase 4 Universal Guardian Kill Switch SLA Benchmark (SAF-02).
Benchmarks synchronous shutdown latency of all Milestone 11 subsystems:
- DynamicToolSynthesizer & RestrictedToolSandbox (Phase 1)
- TreeOfThoughtPlanner, DAGStateManager, MetacognitiveReflector (Phase 2)
- CompanionCameraStreamer & P2PMediaDropManager (Phase 3)

SLA Requirement: strictly < 25.0 ms (assert < 1.0 ms typical).
"""

import io
import base64
import time
import pytest
from PIL import Image
from services.backend.safety.guardian import GuardianKillSwitch
from services.backend.coding.dynamic_synthesizer import dynamic_synthesizer, dynamic_synthesizer_manager
from services.backend.coding.restricted_sandbox import restricted_sandbox
from services.backend.orchestrator.tot_planner import TreeOfThoughtPlanner
from services.backend.orchestrator.dag_state import DAGStateManager
from services.backend.orchestrator.metacognition import MetacognitiveReflector
from services.backend.sensors.companion_camera import CompanionCameraStreamer
from services.backend.mesh.media_drop import P2PMediaDropManager
from services.backend.schemas.sensory import MediaDropDestination, CameraFramePayload


def _make_dummy_frame_payload(node_id: str, frame_id: str) -> CameraFramePayload:
    img = Image.new("RGB", (320, 240), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return CameraFramePayload(
        frame_id=frame_id,
        node_id=node_id,
        timestamp=time.time(),
        image_base64=b64,
        width=320,
        height=240,
    )


def test_milestone_11_universal_guardian_sla_benchmark(tmp_path):
    guardian = GuardianKillSwitch()

    # Instantiate isolated subsystems for benchmark
    tot = TreeOfThoughtPlanner()
    dag_mgr = DAGStateManager()
    reflector = MetacognitiveReflector()
    camera = CompanionCameraStreamer()
    drop_mgr = P2PMediaDropManager(
        vault_dir=str(tmp_path / "vault"),
        downloads_dir=str(tmp_path / "downloads"),
    )

    # Hook all into Guardian state callback
    def on_guardian_state(state: str):
        if state == "halted":
            restricted_sandbox.halt()
            tot.halt()
            dag_mgr.halt()
            reflector.halt()
            camera.halt()
            drop_mgr.halt()
        elif state == "idle":
            restricted_sandbox.reset()
            tot.reset()
            dag_mgr.reset()
            reflector.reset()
            camera.reset()
            drop_mgr.reset()

    guardian.add_state_callback(on_guardian_state)

    latencies_ms = []

    # Run 100 consecutive synchronous halt cycles
    for i in range(100):
        # Setup mock active states
        payload = _make_dummy_frame_payload(node_id=f"phone-{i}", frame_id=f"frame-{i}")
        camera.ingest_frame(payload)

        t_start = time.perf_counter()
        guardian.trigger(f"benchmark_run_{i}")
        t_end = time.perf_counter()

        elapsed_ms = (t_end - t_start) * 1000.0
        latencies_ms.append(elapsed_ms)

        # Invariant checks while halted
        assert guardian.is_halted is True
        assert camera.is_halted() is True
        assert camera._frame_buffer.get_latest() is None
        assert drop_mgr.is_halted() is True
        assert tot.is_halted is True
        assert dag_mgr.is_halted is True

        # Check immediate fail-closed behavior
        with pytest.raises(PermissionError):
            tot.plan_objective("Decompose goal during halt")

        with pytest.raises(PermissionError):
            drop_mgr.create_send_manifest(
                file_path=str(tmp_path / "nonexistent.txt"),
                source_node_id="desktop",
                target_node_id="phone",
                destination=MediaDropDestination.VAULT,
            )

        # Resume for next cycle
        guardian.resume()
        assert guardian.is_halted is False
        assert camera.is_halted() is False
        assert drop_mgr.is_halted() is False
        assert tot.is_halted is False
        assert dag_mgr.is_halted is False

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    max_latency = max(latencies_ms)
    min_latency = min(latencies_ms)

    print(f"\n[UNIVERSAL GUARDIAN SLA BENCHMARK - 100 CYCLES]")
    print(f"  Avg Latency: {avg_latency:.4f} ms")
    print(f"  Max Latency: {max_latency:.4f} ms")
    print(f"  Min Latency: {min_latency:.4f} ms")

    # Hard SLA requirements
    assert avg_latency < 1.0, f"Average halt latency {avg_latency:.4f}ms exceeds 1.0ms target"
    assert max_latency < 25.0, f"Maximum halt latency {max_latency:.4f}ms exceeds 25.0ms SLA"


def test_milestone_11_subsystem_recovery_after_halt(tmp_path):
    """Verify that after resuming from Guardian halt, all subsystems fully recover operational capacity."""
    guardian = GuardianKillSwitch()
    tot = TreeOfThoughtPlanner()
    camera = CompanionCameraStreamer()
    drop_mgr = P2PMediaDropManager(
        vault_dir=str(tmp_path / "vault"),
        downloads_dir=str(tmp_path / "downloads"),
    )

    guardian.add_state_callback(
        lambda s: (tot.halt(), camera.halt(), drop_mgr.halt()) if s == "halted"
        else (tot.reset(), camera.reset(), drop_mgr.reset())
    )

    # 1. Halt
    guardian.trigger("lockdown_recovery_test")
    assert guardian.is_halted is True

    # 2. Resume
    guardian.resume()
    assert guardian.is_halted is False

    # 3. Perform standard operations post-resumption
    dag = tot.plan_objective("Calculate prime numbers and store report")
    assert dag.dag_id is not None
    assert len(dag.nodes) >= 1

    sample_file = tmp_path / "test_recovery.md"
    sample_file.write_text("# Recovery Verification", encoding="utf-8")
    manifest, transfer = drop_mgr.create_send_manifest(
        file_path=str(sample_file),
        source_node_id="desktop",
        target_node_id="phone-companion",
        destination=MediaDropDestination.VAULT,
    )
    assert manifest.file_size > 0
    assert transfer.transfer_id is not None
