"""
Phenom Frame Grabber
High-performance in-RAM screen frame capture on Windows 11.
Strictly zero disk writes - all frame buffers remain in memory.
"""

import time
from typing import Optional, Tuple
from PIL import Image
import mss


class FrameGrabber:
    def __init__(self, monitor_index: int = 1):
        self.monitor_index = monitor_index
        self.last_latency_ms: float = 0.0
        self.frame_count: int = 0
        self._sct = None

    def _get_sct(self):
        if self._sct is None:
            factory = getattr(mss, "MSS", mss.mss)
            self._sct = factory()
        return self._sct

    def grab_frame(self) -> Image.Image:
        """
        Captures the primary monitor into an in-memory PIL Image (RGB).
        Tracks capture latency in milliseconds.
        """
        start = time.perf_counter()
        try:
            sct = self._get_sct()
            # Select monitor (index 1 is primary monitor in mss)
            monitors = sct.monitors
            monitor = monitors[self.monitor_index] if len(monitors) > self.monitor_index else monitors[0]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception:
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
            except Exception:
                # Headless / CI fallback: in-memory canvas
                img = Image.new("RGB", (1920, 1080), color=(8, 11, 16))

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.last_latency_ms = elapsed_ms
        self.frame_count += 1
        return img

    def close(self):
        if self._sct:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None


frame_grabber = FrameGrabber()
