"""
Phenom Continuous Visual Memory Monitor
Background service sampling desktop screen frames in RAM, filtering stationary frames
via perceptual delta hashing, redacting sensitive application windows, extracting text,
and indexing embeddings into encrypted local storage.
Strictly zero disk writes - all frame buffers remain in memory.
"""

import sys
import time
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from PIL import Image

from services.backend.vision.frame_grabber import FrameGrabber
from services.backend.vision.delta_detector import DeltaDetector, delta_detector as default_delta_detector
from services.backend.vision.privacy_masker import PrivacyMasker
from services.backend.vision.ocr_engine import ScreenOCREngine, ocr_engine as default_ocr_engine
from services.backend.memory.embeddings import LocalEmbeddingPipeline, embedding_pipeline as default_embedding_pipeline
from services.backend.memory.visual_store import EncryptedVisualStore, visual_store as default_visual_store
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.visual_memory_monitor")


def get_active_window_info() -> Tuple[str, str]:
    """Retrieves active foreground process name and window title on Windows."""
    if sys.platform != "win32":
        return "desktop", "Desktop Workspace"
    try:
        import win32gui
        import win32process
        import psutil
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return "unknown", ""
        title = win32gui.GetWindowText(hwnd).strip()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc_name = psutil.Process(pid).name().lower() if pid > 0 else "unknown"
        return proc_name, title
    except Exception:
        return "unknown", ""


class VisualMemoryMonitor:
    """
    Supervises background in-RAM visual memory ingestion.
    Runs on an asyncio loop and respects Guardian kill switch instantly.
    """

    def __init__(
        self,
        interval_seconds: float = 3.0,
        delta_threshold: float = 0.015,
        frame_grabber: Optional[FrameGrabber] = None,
        delta_det: Optional[DeltaDetector] = None,
        privacy_mask: Optional[PrivacyMasker] = None,
        ocr_eng: Optional[ScreenOCREngine] = None,
        visual_st: Optional[EncryptedVisualStore] = None,
        embed_pipe: Optional[LocalEmbeddingPipeline] = None
    ):
        self.interval_seconds = interval_seconds
        self.delta_threshold = delta_threshold
        self.frame_grabber = frame_grabber or FrameGrabber()
        self.delta_detector = delta_det or default_delta_detector
        self.privacy_masker = privacy_mask or PrivacyMasker()
        self.ocr_engine = ocr_eng or default_ocr_engine
        self.visual_store = visual_st or default_visual_store
        self.embedding_pipeline = embed_pipe or default_embedding_pipeline

        self._is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self.total_processed_frames: int = 0
        self.stationary_skipped_frames: int = 0
        self.total_indexed_chunks: int = 0

    @property
    def is_running(self) -> bool:
        return self._is_running

    def capture_and_index_step(
        self,
        override_img: Optional[Image.Image] = None,
        override_proc: Optional[str] = None,
        override_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a single in-RAM screen sampling, filtering, and indexing step.
        Returns execution telemetry.
        """
        if guardian.is_halted:
            logger.info("VisualMemoryMonitor: Ingestion paused by Guardian kill switch.")
            return {"status": "halted_by_guardian"}

        t_start = time.perf_counter()
        now_ts = time.time()
        iso_str = datetime.utcnow().isoformat() + "Z"

        # 1. Grab in-memory screen frame
        img = override_img if override_img is not None else self.frame_grabber.grab_frame()

        # 2. Perceptual Delta Check (skip stationary frames)
        has_changed, delta_score = self.delta_detector.compute_delta(img)
        if not has_changed and override_img is None:
            self.stationary_skipped_frames += 1
            return {
                "status": "skipped_stationary",
                "delta": delta_score,
                "latency_ms": (time.perf_counter() - t_start) * 1000.0
            }

        # 3. Context & Sensitive Window Analysis
        proc_name, window_title = (override_proc, override_title) if override_proc else get_active_window_info()

        # If foreground window itself is sensitive, redact completely
        if self.privacy_masker.is_sensitive_title(window_title):
            logger.info(f"VisualMemoryMonitor: Active window '{window_title}' is sensitive. Skipping ingestion.")
            return {
                "status": "skipped_sensitive_window",
                "window_title": window_title,
                "process_name": proc_name,
                "latency_ms": (time.perf_counter() - t_start) * 1000.0
            }

        # Scan for sensitive background/visible window bounds
        sensitive_windows = self.privacy_masker.scan_visible_sensitive_windows()
        masked_img, masked_list = self.privacy_masker.mask_sensitive_windows(img, custom_windows=sensitive_windows)

        # 4. Text Extraction (UI Automation + in-RAM OCR)
        extracted_elements = []

        # Windows UI Automation controls (pixel-exact, zero GPU load)
        uia_elements = self.ocr_engine.extract_elements_from_uia(max_depth=3)
        for elem in uia_elements:
            bbox = elem.get("bbox", [])
            if len(bbox) == 4 and not self._is_bbox_masked(bbox, sensitive_windows):
                text_clean = elem.get("name", "").strip()
                if len(text_clean) >= 3:
                    extracted_elements.append({
                        "text": text_clean,
                        "bbox": bbox,
                        "source": "uia"
                    })

        # OCR fallback for rendered text
        if len(extracted_elements) < 5 and masked_img:
            ocr_elements = self.ocr_engine.extract_text_via_ocr(masked_img)
            for elem in ocr_elements:
                bbox = elem.get("bbox", [])
                if len(bbox) == 4 and not self._is_bbox_masked(bbox, sensitive_windows):
                    text_clean = elem.get("text", "").strip()
                    if len(text_clean) >= 3:
                        extracted_elements.append({
                            "text": text_clean,
                            "bbox": bbox,
                            "source": "ocr"
                        })

        if not extracted_elements:
            return {
                "status": "no_text_extracted",
                "latency_ms": (time.perf_counter() - t_start) * 1000.0
            }

        # 5. Build Text Chunks
        chunks = []
        seen_texts = set()
        for elem in extracted_elements[:30]:  # limit to top 30 chunks per capture
            txt = elem["text"]
            if txt not in seen_texts:
                seen_texts.add(txt)
                chunks.append({
                    "timestamp": now_ts,
                    "iso_time": iso_str,
                    "process_name": proc_name,
                    "window_title": window_title,
                    "text_content": txt,
                    "bbox": elem["bbox"]
                })

        # 6. Generate Local CUDA/CPU Embeddings
        texts_to_embed = [c["text_content"] for c in chunks]
        embeddings = self.embedding_pipeline.embed_texts(texts_to_embed)

        # 7. Insert into Encrypted Store
        inserted_count = self.visual_store.insert_chunks(chunks, embeddings)
        self.total_processed_frames += 1
        self.total_indexed_chunks += inserted_count

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        return {
            "status": "indexed",
            "chunks_count": inserted_count,
            "delta": delta_score,
            "masked_windows_count": len(masked_list),
            "latency_ms": elapsed_ms
        }

    def _is_bbox_masked(self, bbox: List[int], sensitive_windows: List[Dict[str, Any]]) -> bool:
        """Checks if a bounding box intersects with any sensitive window rect."""
        if not sensitive_windows or len(bbox) != 4:
            return False
        bx, by, bw, bh = bbox
        br = bx + bw
        bb = by + bh

        for item in sensitive_windows:
            rect = item.get("rect")
            if rect and len(rect) == 4:
                sl, st, sr, sb = rect
                # Overlap test
                if not (br < sl or bx > sr or bb < st or by > sb):
                    return True
        return False

    async def _run_loop(self):
        """Asynchronous background monitoring loop."""
        logger.info("VisualMemoryMonitor background loop started.")
        while self._is_running:
            if not guardian.is_halted:
                try:
                    self.capture_and_index_step()
                except Exception as e:
                    logger.debug(f"VisualMemoryMonitor step error: {e}")
            await asyncio.sleep(self.interval_seconds)

    def start(self):
        """Starts background monitoring."""
        if not self._is_running:
            self._is_running = True
            try:
                loop = asyncio.get_running_loop()
                self._task = loop.create_task(self._run_loop())
            except RuntimeError:
                pass

    def stop(self):
        """Stops background monitoring immediately."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        logger.info("VisualMemoryMonitor background loop stopped.")


# Global singleton
visual_memory_monitor = VisualMemoryMonitor()
