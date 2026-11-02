"""
Phenom Delta Detector
Lightweight in-memory perceptual change detection to filter redundant stationary frames.
Computes difference hashes to reduce compute on idle screens.
"""

from typing import Tuple, Optional
import numpy as np
from PIL import Image


class DeltaDetector:
    def __init__(self, threshold: float = 0.015, thumbnail_size: Tuple[int, int] = (64, 36)):
        """
        :param threshold: Normalized difference threshold (0.015 = 1.5% mean change)
        :param thumbnail_size: Resolution for downsampled delta comparison
        """
        self.threshold = threshold
        self.thumbnail_size = thumbnail_size
        self._prev_thumb: Optional[np.ndarray] = None
        self.last_delta_score: float = 0.0

    def compute_delta(self, img: Image.Image) -> Tuple[bool, float]:
        """
        Calculates normalized pixel difference against the previous frame.
        Returns:
            (has_changed: bool, delta_score: float)
        """
        # Downsample to grayscale thumbnail for low-overhead comparison
        thumb = img.convert("L").resize(self.thumbnail_size, Image.Resampling.BILINEAR)
        curr_arr = np.asarray(thumb, dtype=np.float32)

        if self._prev_thumb is None:
            self._prev_thumb = curr_arr
            self.last_delta_score = 1.0
            return True, 1.0

        # Mean absolute difference normalized to [0.0, 1.0]
        diff = float(np.mean(np.abs(curr_arr - self._prev_thumb)) / 255.0)
        self.last_delta_score = diff

        has_changed = bool(diff >= self.threshold)
        if has_changed:
            self._prev_thumb = curr_arr

        return has_changed, self.last_delta_score

    def reset(self):
        """Resets the baseline comparison frame."""
        self._prev_thumb = None
        self.last_delta_score = 0.0


delta_detector = DeltaDetector()
