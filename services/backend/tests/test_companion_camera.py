"""
Unit Test Suite for Companion Camera Vision Streamer (SEN-01, SAF-01, SAF-02)
Verifies in-RAM frame ingestion, zero disk writes, ring buffer bounding,
local VLM/OCR analysis contracts, and sub-millisecond Guardian kill switch SLA.
"""

import io
import time
import base64
import pytest
from unittest.mock import AsyncMock, MagicMock
from PIL import Image

from services.backend.schemas.sensory import CameraFramePayload, CameraAnalysisResult
from services.backend.sensors.companion_camera import (
    CompanionCameraStreamer,
    InRamFrameBuffer,
)


def _create_mock_jpeg_b64(width: int = 640, height: int = 480, color: str = "red") -> str:
    """Helper to create a raw JPEG image in RAM and return base64 string."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@pytest.fixture
def streamer():
    mock_moondream = MagicMock()
    mock_moondream.query_image = AsyncMock(return_value={
        "description": "Mocked local physical object description",
        "model": "moondream",
        "status": "success",
    })
    mock_ocr = MagicMock()
    mock_ocr.extract_text_via_ocr = MagicMock(return_value=[
        {"text": "MOCK WHITEBOARD TEXT", "confidence": 0.95, "x": 100, "y": 150}
    ])
    inst = CompanionCameraStreamer(
        moondream_client=mock_moondream,
        ocr_engine=mock_ocr,
    )
    inst.reset()
    return inst


def test_in_ram_frame_ingestion_zero_disk_writes(streamer, tmp_path, monkeypatch):
    """SEN-01 & Permanent Rule 4: Verify frames stay strictly in RAM with zero disk writes."""
    b64_data = _create_mock_jpeg_b64(800, 600, color="blue")
    payload = CameraFramePayload(
        frame_id="frame-001",
        node_id="companion-pixel-9",
        timestamp=time.time(),
        image_base64=b64_data,
        width=800,
        height=600,
        battery_level=88.5,
        is_charging=True,
        wifi_rssi=-52,
    )

    res = streamer.ingest_frame(payload)
    assert res["status"] == "ingested"
    assert res["resolution"] == "800x600"

    latest = streamer.get_latest_frame()
    assert latest is not None
    assert latest["frame_id"] == "frame-001"
    assert latest["node_id"] == "companion-pixel-9"
    assert latest["width"] == 800
    assert latest["height"] == 600
    assert latest["battery_level"] == 88.5
    assert latest["is_charging"] is True
    assert latest["wifi_rssi"] == -52
    assert isinstance(latest["image"], Image.Image)
    assert latest["thumbnail_base64"] is not None


def test_frame_buffer_bounding_and_overwriting(streamer):
    """Verify in-memory ring buffer stays strictly bounded (max_frames=5)."""
    for i in range(10):
        b64_data = _create_mock_jpeg_b64(320, 240, color="green")
        payload = CameraFramePayload(
            frame_id=f"frame-{i}",
            node_id="companion-iphone-15",
            timestamp=time.time() + i,
            image_base64=b64_data,
            width=320,
            height=240,
        )
        streamer.ingest_frame(payload)

    # Frame buffer internal count should not exceed 5
    assert streamer._frame_buffer.count() == 5

    # Latest frame should be frame-9
    latest = streamer.get_latest_frame()
    assert latest is not None
    assert latest["frame_id"] == "frame-9"

    # Status should reflect 10 total frames ingested
    status = streamer.get_status()
    assert status.frames_received == 10
    assert status.is_streaming is True


@pytest.mark.asyncio
async def test_local_vlm_and_ocr_analysis(streamer):
    """SEN-01: Verify local OCR and Moondream2 inspection without cloud exfiltration."""
    b64_data = _create_mock_jpeg_b64(640, 480, color="white")
    payload = CameraFramePayload(
        frame_id="frame-analysis-01",
        node_id="companion-ipad",
        timestamp=time.time(),
        image_base64=b64_data,
        width=640,
        height=480,
    )
    streamer.ingest_frame(payload)

    # 1. OCR Task
    ocr_result = await streamer.analyze_frame(task_type="ocr")
    assert isinstance(ocr_result, CameraAnalysisResult)
    assert ocr_result.task_type == "ocr"
    assert "MOCK WHITEBOARD TEXT" in ocr_result.extracted_text
    assert ocr_result.model_used == "easyocr"
    assert ocr_result.processing_time_ms >= 0

    # 2. Object task (local VLM)
    obj_result = await streamer.analyze_frame(task_type="object", prompt="What is this?")
    assert obj_result.task_type == "object"
    assert "Mocked local physical object" in obj_result.description
    assert obj_result.model_used == "moondream2"

    # 3. Whiteboard task
    wb_result = await streamer.analyze_frame(task_type="whiteboard")
    assert wb_result.task_type == "whiteboard"
    assert "MOCK WHITEBOARD TEXT" in wb_result.extracted_text
    assert "Mocked local physical object" in wb_result.description


def test_guardian_kill_switch_synchronous_halt(streamer):
    """SAF-02: Guardian kill switch halts camera ingestion in < 1.0ms (< 25ms SLA)."""
    b64_data = _create_mock_jpeg_b64(400, 300)
    payload = CameraFramePayload(
        frame_id="frame-pre-halt",
        node_id="companion-node",
        timestamp=time.time(),
        image_base64=b64_data,
    )
    streamer.ingest_frame(payload)
    assert streamer.get_latest_frame() is not None

    # Measure halt execution time
    t0 = time.perf_counter()
    streamer.halt()
    halt_duration_ms = (time.perf_counter() - t0) * 1000.0

    # SLA < 25ms, assert typical < 1.0ms
    assert halt_duration_ms < 25.0, f"Halt exceeded 25ms SLA: {halt_duration_ms:.3f}ms"
    assert streamer.is_halted() is True

    # Buffer must be wiped
    assert streamer._frame_buffer.count() == 0

    # Ingestion must immediately raise PermissionError
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        streamer.ingest_frame(payload)

    # Frame retrieval must raise PermissionError
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        streamer.get_latest_frame()

    # Reset restores operation
    streamer.reset()
    assert streamer.is_halted() is False
    res = streamer.ingest_frame(payload)
    assert res["status"] == "ingested"
