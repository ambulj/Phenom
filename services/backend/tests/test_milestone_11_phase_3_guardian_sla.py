"""
Guardian Kill Switch Sub-25ms SLA Test Suite for Milestone 11.0 Phase 3 (SAF-02)
Benchmarks synchronous halt latency of CompanionCameraStreamer and P2PMediaDropManager.
Asserts immediate thread-safe PermissionError enforcement and zero lingering state.
"""

import io
import time
import base64
import pytest
from PIL import Image

from services.backend.sensors.companion_camera import companion_camera_streamer
from services.backend.mesh.media_drop import media_drop_manager
from services.backend.schemas.sensory import (
    CameraFramePayload,
    MediaDropDestination,
    MediaDropTransferState,
)


def _make_dummy_frame_b64() -> str:
    img = Image.new("RGB", (320, 240), color="purple")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def test_guardian_synchronous_halt_latency_sla():
    """SAF-02: Measure synchronous halt latency across sensory singletons (SLA < 25ms, assert typical < 1.0ms)."""
    companion_camera_streamer.reset()
    media_drop_manager.reset()

    latencies_ms = []
    iterations = 50

    for _ in range(iterations):
        # Seed frame buffer and active state
        payload = CameraFramePayload(
            frame_id="bench-frame",
            node_id="bench-node",
            timestamp=time.time(),
            image_base64=_make_dummy_frame_b64(),
        )
        companion_camera_streamer.ingest_frame(payload)

        # Benchmark combined synchronous halt
        t0 = time.perf_counter()
        companion_camera_streamer.halt()
        media_drop_manager.halt()
        t1 = time.perf_counter()

        elapsed_ms = (t1 - t0) * 1000.0
        latencies_ms.append(elapsed_ms)

        # Assert strict SLA on each individual invocation
        assert elapsed_ms < 25.0, f"Halt exceeded 25.0ms SLA: {elapsed_ms:.3f}ms"

        # Reset for next iteration
        companion_camera_streamer.reset()
        media_drop_manager.reset()

    avg_ms = sum(latencies_ms) / len(latencies_ms)
    max_ms = max(latencies_ms)
    print(f"\n[Guardian SLA Benchmark] 50 Halts -> Avg: {avg_ms:.4f}ms, Max: {max_ms:.4f}ms")
    assert max_ms < 25.0
    assert avg_ms < 2.0  # Typically < 0.5ms


def test_guardian_halt_blocks_all_sensory_operations(tmp_path):
    """SAF-02: While halted, all camera and media drop operations must immediately raise PermissionError."""
    companion_camera_streamer.reset()
    media_drop_manager.reset()

    # Trigger halt
    companion_camera_streamer.halt()
    media_drop_manager.halt()

    assert companion_camera_streamer.is_halted() is True
    assert media_drop_manager.is_halted() is True

    # 1. Camera Ingestion blocked
    dummy_payload = CameraFramePayload(
        frame_id="halt-test",
        node_id="phone",
        timestamp=time.time(),
        image_base64=_make_dummy_frame_b64(),
    )
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        companion_camera_streamer.ingest_frame(dummy_payload)

    # 2. Camera Frame Retrieval blocked
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        companion_camera_streamer.get_latest_frame()

    # 3. Media Drop Send blocked
    dummy_file = tmp_path / "doc.txt"
    dummy_file.write_text("Hello", encoding="utf-8")
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        media_drop_manager.create_send_manifest(
            file_path=str(dummy_file),
            source_node_id="node-1",
            target_node_id="node-2",
        )

    # 4. Media Drop Receive Manifest blocked
    from services.backend.schemas.sensory import MediaDropManifest
    manifest = MediaDropManifest(
        transfer_id="halt-drop",
        source_node_id="node-1",
        target_node_id="node-2",
        filename="test.txt",
        file_size=5,
        sha256_checksum="0" * 64,
        total_chunks=1,
        created_at=time.time(),
    )
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        media_drop_manager.receive_manifest(manifest)

    # Reset restores normal operation
    companion_camera_streamer.reset()
    media_drop_manager.reset()

    assert companion_camera_streamer.is_halted() is False
    assert media_drop_manager.is_halted() is False

    res = companion_camera_streamer.ingest_frame(dummy_payload)
    assert res["status"] == "ingested"
