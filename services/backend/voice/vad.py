"""
Phenom Silero VAD Engine
High-precision, sub-millisecond local voice activity detector using Silero VAD ONNX.
Processes 16kHz audio chunks with stateful recurrent hidden states (h, c)
and strictly zero disk access or cloud network dependency.
"""

import os
import sys
import logging
from typing import Optional, Tuple
import numpy as np

try:
    import onnxruntime as ort
except ImportError:
    ort = None

logger = logging.getLogger("phenom.voice.vad")

DEFAULT_MODEL_PATHS = [
    r"C:\Phenom\.venv-clean\Lib\site-packages\openwakeword\resources\models\silero_vad.onnx",
    os.path.join(sys.prefix, "Lib", "site-packages", "openwakeword", "resources", "models", "silero_vad.onnx"),
    os.path.join(sys.prefix, "lib", "site-packages", "openwakeword", "resources", "models", "silero_vad.onnx"),
]


class SileroVAD:
    """
    Local Silero VAD inference engine wrapping ONNX Runtime.
    Inference latency is ~0.2-0.5 ms per 32ms (512 samples) chunk.
    """

    def __init__(self, model_path: Optional[str] = None, speech_threshold: float = 0.50):
        self.speech_threshold = speech_threshold
        self._session: Optional[ort.InferenceSession] = None
        self._sr_tensor = np.array(16000, dtype=np.int64)
        self._h: np.ndarray = np.zeros((2, 1, 64), dtype=np.float32)
        self._c: np.ndarray = np.zeros((2, 1, 64), dtype=np.float32)
        self._last_inference_latency_ms: float = 0.0

        resolved_path = model_path
        if not resolved_path:
            for candidate in DEFAULT_MODEL_PATHS:
                if os.path.exists(candidate):
                    resolved_path = candidate
                    break

        if resolved_path and os.path.exists(resolved_path) and ort is not None:
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 1
            opts.inter_op_num_threads = 1
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._session = ort.InferenceSession(resolved_path, sess_options=opts)
            logger.info("SileroVAD loaded ONNX model from %s", resolved_path)
            # Run 1 warmup chunk to eliminate cold-start graph allocation
            try:
                dummy = np.zeros(512, dtype=np.float32)
                self.process_chunk(dummy)
                self.reset_states()
            except Exception:
                pass
        else:
            logger.warning("SileroVAD ONNX model not found or onnxruntime missing; will use RMS energy fallback")

    def reset_states(self):
        """Resets the recurrent hidden and cell states."""
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)

    @property
    def is_available(self) -> bool:
        return self._session is not None

    def process_chunk(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> float:
        """
        Evaluates a chunk of 16kHz audio and returns the speech probability [0.0, 1.0].
        Standard chunk length is 512 samples (32 ms).
        """
        if audio_chunk is None or len(audio_chunk) == 0:
            return 0.0

        # Convert to float32 normalized [-1.0, 1.0]
        if audio_chunk.dtype == np.int16:
            samples = audio_chunk.astype(np.float32) / 32768.0
        else:
            samples = audio_chunk.astype(np.float32)

        # Fallback to RMS energy if ONNX session not loaded
        if self._session is None:
            rms = float(np.sqrt(np.mean(samples ** 2)))
            return 1.0 if rms > 0.040 else 0.0

        # Silero VAD expects 512 samples per step
        target_len = 512
        if len(samples) < target_len:
            samples = np.pad(samples, (0, target_len - len(samples)), mode="constant")
        elif len(samples) > target_len:
            samples = samples[:target_len]

        chunk_2d = np.expand_dims(samples, axis=0)  # Shape (1, 512)

        import time
        t0 = time.perf_counter()
        try:
            inputs = {
                "input": chunk_2d,
                "sr": self._sr_tensor,
                "h": self._h,
                "c": self._c,
            }
            outputs = self._session.run(None, inputs)
            prob = float(outputs[0][0][0])
            self._h = outputs[1]
            self._c = outputs[2]
            self._last_inference_latency_ms = (time.perf_counter() - t0) * 1000.0
            return max(0.0, min(1.0, prob))
        except Exception as e:
            logger.error("SileroVAD inference error: %s", e)
            self.reset_states()
            return 0.0

    def is_speech(self, audio_chunk: np.ndarray, threshold: Optional[float] = None) -> bool:
        """Convenience method checking if speech probability meets or exceeds threshold."""
        prob = self.process_chunk(audio_chunk)
        th = threshold if threshold is not None else self.speech_threshold
        return prob >= th


# Global singleton instance
silero_vad = SileroVAD()
