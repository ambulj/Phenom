"""
Companion Camera Vision Streamer for Phenom Milestone 11.0 (SEN-01, SAF-01, SAF-02)
Ingests live camera frames from paired mobile companion devices strictly in-RAM.
Performs local VLM (Moondream2) and OCR analysis with zero cloud exfiltration.
Enforces sub-millisecond synchronous Guardian kill switch halt SLA (< 25ms SLA).
Strictly adheres to AGENTS.md Permanent Rule 4: zero disk writes for camera buffers.
"""

import io
import base64
import time
import threading
from typing import Optional, Dict, Any, List, Callable
from PIL import Image

from services.backend.schemas.sensory import (
    CameraFramePayload,
    CameraAnalysisTask,
    CameraAnalysisResult,
    CameraStatus,
)
from services.backend.vision.moondream_client import MoondreamVisionClient
from services.backend.vision.ocr_engine import ScreenOCREngine


class InRamFrameBuffer:
    """
    Thread-safe, bounded in-RAM ring buffer for camera frames.
    Holds decoded PIL Image and frame telemetry in memory.
    Guarantees zero disk writes (Permanent Rule 4).
    """

    def __init__(self, max_frames: int = 5):
        self._max_frames = max_frames
        self._lock = threading.Lock()
        self._frames: List[Dict[str, Any]] = []

    def push(self, frame_data: Dict[str, Any]) -> None:
        """Pushes a decoded frame record to the in-memory ring buffer."""
        with self._lock:
            self._frames.append(frame_data)
            if len(self._frames) > self._max_frames:
                # Evict oldest frame reference to release memory
                self._frames.pop(0)

    def get_latest(self, node_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Returns the most recent frame record, optionally filtered by node_id."""
        with self._lock:
            if not self._frames:
                return None
            if node_id is None:
                latest = self._frames[-1]
                return {
                    "image": latest["image"].copy(),
                    "frame_id": latest["frame_id"],
                    "node_id": latest["node_id"],
                    "timestamp": latest["timestamp"],
                    "width": latest["width"],
                    "height": latest["height"],
                    "battery_level": latest.get("battery_level"),
                    "is_charging": latest.get("is_charging", False),
                    "wifi_rssi": latest.get("wifi_rssi"),
                    "thumbnail_base64": latest.get("thumbnail_base64"),
                }

            # Filter for specific node in reverse chronological order
            for f in reversed(self._frames):
                if f["node_id"] == node_id:
                    return {
                        "image": f["image"].copy(),
                        "frame_id": f["frame_id"],
                        "node_id": f["node_id"],
                        "timestamp": f["timestamp"],
                        "width": f["width"],
                        "height": f["height"],
                        "battery_level": f.get("battery_level"),
                        "is_charging": f.get("is_charging", False),
                        "wifi_rssi": f.get("wifi_rssi"),
                        "thumbnail_base64": f.get("thumbnail_base64"),
                    }
            return None

    def clear(self) -> None:
        """Synchronously clears all frame buffers in RAM."""
        with self._lock:
            self._frames.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._frames)


class CompanionCameraStreamer:
    """
    Manages live camera streaming from companion devices over encrypted P2P mesh.
    Operates strictly in memory with zero cloud exfiltration.
    Supports local OCR and Moondream2 VLM inspection.
    """

    def __init__(
        self,
        moondream_client: Optional[MoondreamVisionClient] = None,
        ocr_engine: Optional[ScreenOCREngine] = None,
    ):
        self._frame_buffer = InRamFrameBuffer(max_frames=5)
        self._moondream = moondream_client or MoondreamVisionClient()
        self._ocr = ocr_engine or ScreenOCREngine()

        self._lock = threading.Lock()
        self._halted: bool = False
        self._is_streaming: bool = False
        self._active_node_id: Optional[str] = None
        self._device_name: Optional[str] = None
        self._last_frame_ts: Optional[float] = None
        self._resolution: Optional[str] = None
        self._battery_level: Optional[float] = None
        self._is_charging: bool = False
        self._wifi_rssi: Optional[int] = None
        self._frames_received: int = 0
        self._broadcaster: Optional[Callable[[Dict[str, Any]], Any]] = None

    def register_broadcaster(self, broadcaster_fn: Callable[[Dict[str, Any]], Any]) -> None:
        """Register WebSocket broadcast callback for pushing live frames to Cyber HUD."""
        self._broadcaster = broadcaster_fn

    def is_halted(self) -> bool:
        with self._lock:
            return self._halted

    def halt(self) -> None:
        """
        Synchronous Guardian kill switch halt callback.
        Immediately stops streaming and wipes frame buffer in < 1.0ms (< 25ms SLA).
        """
        with self._lock:
            self._halted = True
            self._is_streaming = False
            self._frame_buffer.clear()

    def reset(self) -> None:
        """Resets halted state after Guardian disengagement."""
        with self._lock:
            self._halted = False

    def ingest_frame(self, payload: CameraFramePayload) -> Dict[str, Any]:
        """
        Ingests a camera frame snapshot from a paired companion node.
        Decodes JPEG strictly in RAM (BytesIO).
        Updates in-memory ring buffer and telemetry state.
        Raises PermissionError if Guardian kill switch is active.
        """
        if self._halted:
            raise PermissionError("Guardian kill switch is active: companion camera ingestion is strictly halted")

        # In-RAM base64 decode and PIL Image loading
        try:
            raw_bytes = base64.b64decode(payload.image_base64)
            buf = io.BytesIO(raw_bytes)
            img = Image.open(buf)
            img.load()  # Force decode in RAM
        except Exception as e:
            raise ValueError(f"Failed to decode JPEG frame payload in RAM: {str(e)}") from e

        # Generate lightweight in-RAM thumbnail (e.g. 320x180) for Cyber HUD preview
        try:
            thumb = img.copy()
            thumb.thumbnail((320, 180), Image.Resampling.BILINEAR)
            thumb_io = io.BytesIO()
            thumb.save(thumb_io, format="JPEG", quality=60)
            thumb_b64 = base64.b64encode(thumb_io.getvalue()).decode("utf-8")
        except Exception:
            thumb_b64 = ""

        with self._lock:
            if self._halted:
                raise PermissionError("Guardian kill switch is active: companion camera ingestion is strictly halted")

            self._frames_received += 1
            self._is_streaming = True
            self._active_node_id = payload.node_id
            self._last_frame_ts = payload.timestamp
            self._resolution = f"{img.width}x{img.height}"
            if payload.battery_level is not None:
                self._battery_level = payload.battery_level
            if payload.is_charging is not None:
                self._is_charging = payload.is_charging
            if payload.wifi_rssi is not None:
                self._wifi_rssi = payload.wifi_rssi

        frame_record = {
            "image": img,
            "frame_id": payload.frame_id,
            "node_id": payload.node_id,
            "timestamp": payload.timestamp,
            "width": img.width,
            "height": img.height,
            "battery_level": payload.battery_level,
            "is_charging": payload.is_charging,
            "wifi_rssi": payload.wifi_rssi,
            "thumbnail_base64": thumb_b64,
        }
        self._frame_buffer.push(frame_record)

        return {
            "status": "ingested",
            "frame_id": payload.frame_id,
            "frames_total": self._frames_received,
            "resolution": f"{img.width}x{img.height}",
        }

    def get_latest_frame(self, node_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves the latest available frame from the in-memory buffer.
        Raises PermissionError if Guardian kill switch is active.
        """
        if self._halted:
            raise PermissionError("Guardian kill switch is active: camera frames inaccessible")

        return self._frame_buffer.get_latest(node_id=node_id)

    def get_status(self) -> CameraStatus:
        """Returns the current operational status of companion camera streamer."""
        with self._lock:
            return CameraStatus(
                is_streaming=self._is_streaming,
                node_id=self._active_node_id,
                device_name=self._device_name,
                last_frame_ts=self._last_frame_ts,
                resolution=self._resolution,
                battery_level=self._battery_level,
                is_charging=self._is_charging,
                wifi_rssi=self._wifi_rssi,
                frames_received=self._frames_received,
                is_halted=self._halted,
            )

    async def analyze_frame(
        self,
        task_type: str = "object",
        prompt: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> CameraAnalysisResult:
        """
        Runs local VLM or OCR analysis on the current in-RAM frame.
        Guarantees zero cloud exfiltration (Permanent Rule 4).
        """
        if self._halted:
            raise PermissionError("Guardian kill switch is active: camera frame analysis is halted")

        frame_data = self.get_latest_frame(node_id=node_id)
        if not frame_data:
            raise ValueError("No active companion camera frame available in memory for analysis")

        start_time = time.perf_counter()
        img: Image.Image = frame_data["image"]
        extracted_text: Optional[str] = None
        description: Optional[str] = None
        detected_items: List[Dict[str, Any]] = []
        model_used = "unknown"

        task = task_type.lower()
        if task == CameraAnalysisTask.OCR.value:
            # Local OCR Text Extraction
            model_used = "easyocr"
            try:
                ocr_results = self._ocr.extract_text_via_ocr(img)
                detected_items = ocr_results
                extracted_lines = [item.get("text", "") for item in ocr_results if item.get("text")]
                extracted_text = "\n".join(extracted_lines)
            except Exception as e:
                extracted_text = f"Local OCR extraction error: {str(e)}"

        elif task == CameraAnalysisTask.WHITEBOARD.value:
            # Whiteboard mode: Extract handwritten/printed text & layout
            model_used = "moondream2+easyocr"
            try:
                ocr_results = self._ocr.extract_text_via_ocr(img)
                detected_items = ocr_results
                lines = [item.get("text", "") for item in ocr_results if item.get("text")]
                extracted_text = "\n".join(lines)
            except Exception:
                extracted_text = ""

            wb_prompt = prompt or "Summarize whiteboard diagrams, bullet points, headers, and notes visible in this image."
            try:
                vlm_resp = await self._moondream.query_image(img, prompt=wb_prompt)
                description = vlm_resp.get("description", "")
            except Exception as e:
                description = f"Local VLM whiteboard analysis unavailable: {str(e)}"

        else:
            # Object / Scene Query mode via local Moondream2 VLM
            model_used = "moondream2"
            obj_prompt = prompt or "Describe the physical objects, hardware components, or documents visible in this frame."
            try:
                vlm_resp = await self._moondream.query_image(img, prompt=obj_prompt)
                description = vlm_resp.get("description", "")
                if "detected_objects" in vlm_resp:
                    detected_items = vlm_resp["detected_objects"]
            except Exception as e:
                description = f"Local VLM inspection unavailable: {str(e)}"

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return CameraAnalysisResult(
            task_type=task,
            extracted_text=extracted_text,
            description=description,
            detected_items=detected_items,
            model_used=model_used,
            processing_time_ms=round(elapsed_ms, 2),
            timestamp=time.time(),
        )


# Global singleton instance
companion_camera_streamer = CompanionCameraStreamer()
