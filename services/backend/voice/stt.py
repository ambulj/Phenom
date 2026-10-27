"""
Phenom Speech-To-Text (STT) Engine
Uses faster-whisper (tiny.en on CUDA with float16) for high-speed local transcription.
Audio is processed strictly in-memory (RAM) and NEVER saved to disk or sent to the cloud.
"""

import os
import sys
import time
from typing import Optional, Tuple
import numpy as np

# Ensure Windows discovers CUDA cublas libraries
try:
    import torch
    torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
    if os.path.exists(torch_lib):
        os.add_dll_directory(torch_lib)
        os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

import faster_whisper

class STTEngine:
    def __init__(self, model_size: str = "tiny.en", device: str = "cuda", compute_type: str = "float16"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Optional[faster_whisper.WhisperModel] = None

    def _ensure_model_loaded(self):
        if self._model is None:
            try:
                self._model = faster_whisper.WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
            except Exception as e:
                # If CUDA is saturated, fallback to CPU
                self._model = faster_whisper.WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8"
                )

    def transcribe_audio_array(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Tuple[str, float]:
        """
        Transcribes a 1D float32 or int16 numpy audio array in-memory.
        Returns (transcribed_text, latency_ms).
        Never touches the disk.
        """
        self._ensure_model_loaded()

        # Convert to float32 normalized between -1.0 and 1.0 if int16
        if audio_data.dtype == np.int16:
            audio_float = audio_data.astype(np.float32) / 32768.0
        else:
            audio_float = audio_data.astype(np.float32)

        start_time = time.perf_counter()
        segments, info = self._model.transcribe(
            audio_float,
            language="en",
            beam_size=1,
            temperature=0.0,
            vad_filter=True # Use built-in Silero VAD to prune leading/trailing silence
        )
        
        text = " ".join([seg.text for seg in segments]).strip()
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return text, latency_ms

stt_engine = STTEngine()
