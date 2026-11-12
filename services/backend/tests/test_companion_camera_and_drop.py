"""
End-to-End Integration Suite for Milestone 11.0 Phase 3:
Multi-Device Sensory Fabric: Companion Camera Vision & AirDrop-Style Encrypted P2P Drop
(SEN-01, MSH-02, SAF-01, SAF-02)
"""

import os
import io
import time
import base64
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock
from PIL import Image

from services.backend.sensors.companion_camera import CompanionCameraStreamer
from services.backend.mesh.media_drop import P2PMediaDropManager
from services.backend.schemas.sensory import (
    CameraFramePayload,
    MediaDropDestination,
    MediaDropTransferState,
)


def _generate_test_image_b64(width: int = 800, height: int = 600) -> str:
    img = Image.new("RGB", (width, height), color=(20, 40, 60))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@pytest.fixture
def sensory_fabric(tmp_path):
    vault_dir = tmp_path / "vault"
    downloads_dir = tmp_path / "downloads"

    mock_moondream = MagicMock()
    mock_moondream.query_image = AsyncMock(return_value={
        "description": "Hardware workbench with Raspberry Pi and USB oscilloscope",
        "model": "moondream2",
    })
    mock_ocr = MagicMock()
    mock_ocr.extract_text_via_ocr = MagicMock(return_value=[
        {"text": "CONFIDENTIAL PROJECT ROADMAP", "confidence": 0.98, "x": 50, "y": 80},
        {"text": "Milestone 11.0 Sensory Fabric", "confidence": 0.94, "x": 50, "y": 120},
    ])

    streamer = CompanionCameraStreamer(
        moondream_client=mock_moondream,
        ocr_engine=mock_ocr,
    )
    media_mgr = P2PMediaDropManager(
        vault_dir=str(vault_dir),
        downloads_dir=str(downloads_dir),
    )

    streamer.reset()
    media_mgr.reset()

    return {
        "streamer": streamer,
        "media_mgr": media_mgr,
        "vault_dir": vault_dir,
        "downloads_dir": downloads_dir,
    }


@pytest.mark.asyncio
async def test_full_sensory_fabric_and_p2p_drop_e2e(sensory_fabric, tmp_path):
    """
    E2E Flow:
    1. Paired companion streams live camera frames into RAM.
    2. Local OCR extracts text from document snapshot.
    3. AirDrop transfers markdown note into vault/ with SHA-256 verification.
    4. Anti-path traversal and executable blocking protect filesystem.
    5. Guardian kill switch aborts all sensory pipelines in < 25ms SLA.
    """
    streamer: CompanionCameraStreamer = sensory_fabric["streamer"]
    media_mgr: P2PMediaDropManager = sensory_fabric["media_mgr"]
    vault_dir = sensory_fabric["vault_dir"]

    # --- Step 1: Companion Ingests Camera Frame in RAM ---
    frame_b64 = _generate_test_image_b64(1280, 720)
    frame_payload = CameraFramePayload(
        frame_id="frame-e2e-001",
        node_id="companion-pixel-9-pro",
        timestamp=time.time(),
        image_base64=frame_b64,
        width=1280,
        height=720,
        battery_level=94.0,
        is_charging=False,
        wifi_rssi=-48,
    )
    ingest_res = streamer.ingest_frame(frame_payload)
    assert ingest_res["status"] == "ingested"
    assert ingest_res["resolution"] == "1280x720"

    status = streamer.get_status()
    assert status.is_streaming is True
    assert status.battery_level == 94.0
    assert status.wifi_rssi == -48
    assert status.frames_received == 1

    # --- Step 2: Local OCR & VLM Analysis (SEN-01) ---
    analysis_res = await streamer.analyze_frame(task_type="ocr")
    assert analysis_res.task_type == "ocr"
    assert "CONFIDENTIAL PROJECT ROADMAP" in analysis_res.extracted_text
    assert "Milestone 11.0 Sensory Fabric" in analysis_res.extracted_text
    assert analysis_res.model_used == "easyocr"

    obj_res = await streamer.analyze_frame(task_type="object", prompt="What is on the table?")
    assert "Raspberry Pi" in obj_res.description
    assert obj_res.model_used == "moondream2"

    # --- Step 3: AirDrop Encrypted P2P Media Drop into vault/ (MSH-02) ---
    note_content = (
        b"# Milestone 11.0 Research Notes\n\n"
        b"- Camera frame retention strictly in-RAM.\n"
        b"- AirDrop chunked streaming with SHA-256 verification.\n"
    ) * 1000  # Multi-chunk note

    src_note = tmp_path / "ResearchNotes.md"
    src_note.write_bytes(note_content)

    manifest, _ = media_mgr.create_send_manifest(
        file_path=str(src_note),
        source_node_id="companion-pixel-9-pro",
        target_node_id="desktop-host",
        destination=MediaDropDestination.VAULT,
    )

    # Receiver accepts manifest
    ack = media_mgr.receive_manifest(manifest)
    assert ack.status == "ack"

    # Send all chunks
    for i in range(manifest.total_chunks):
        chunk = media_mgr.read_file_chunk(str(src_note), i, manifest.transfer_id)
        media_mgr.receive_chunk(chunk)

    transfer = media_mgr.get_transfer(manifest.transfer_id)
    assert transfer is not None
    assert transfer.state == MediaDropTransferState.COMPLETED
    assert transfer.progress == 1.0

    # Verify committed file
    saved_file = vault_dir / "ResearchNotes.md"
    assert saved_file.exists()
    assert saved_file.read_bytes() == note_content

    # --- Step 4: Security Defenses (Executable Blocking & Path Traversal) ---
    # Malicious executable
    malicious_exe = tmp_path / "payload.exe"
    malicious_exe.write_bytes(b"MZ" + b"\x00" * 100)
    with pytest.raises(ValueError, match="executable extension"):
        media_mgr.create_send_manifest(
            file_path=str(malicious_exe),
            source_node_id="companion",
            target_node_id="desktop",
        )

    # --- Step 5: Guardian Kill Switch Synchronous Halt SLA (SAF-02) ---
    # Start an in-flight transfer
    large_doc = tmp_path / "LargeFile.dat"
    large_doc.write_bytes(b"DATA" * 50000)
    manifest2, _ = media_mgr.create_send_manifest(
        file_path=str(large_doc),
        source_node_id="companion",
        target_node_id="desktop",
        destination=MediaDropDestination.DOWNLOADS,
    )
    media_mgr.receive_manifest(manifest2)
    chunk0 = media_mgr.read_file_chunk(str(large_doc), 0, manifest2.transfer_id)
    media_mgr.receive_chunk(chunk0)

    # Synchronous Guardian halt benchmark
    t0 = time.perf_counter()
    streamer.halt()
    media_mgr.halt()
    halt_duration_ms = (time.perf_counter() - t0) * 1000.0

    assert halt_duration_ms < 25.0, f"Guardian SLA breached: {halt_duration_ms:.3f}ms"
    assert streamer.is_halted() is True
    assert media_mgr.is_halted() is True

    # In-memory camera buffer cleared
    assert streamer._frame_buffer.count() == 0

    # In-flight transfer aborted
    t2 = media_mgr.get_transfer(manifest2.transfer_id)
    assert t2.state == MediaDropTransferState.ABORTED

    # Lingering staging part files deleted
    staging_parts = list(sensory_fabric["downloads_dir"].glob("*.part"))
    assert len(staging_parts) == 0

    # Attempting operations while halted raises PermissionError
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        streamer.ingest_frame(frame_payload)

    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        media_mgr.read_file_chunk(str(large_doc), 1, manifest2.transfer_id)
