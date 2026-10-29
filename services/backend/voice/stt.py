"""
Phenom Speech-To-Text (STT) Engine (faster-whisper)
Supports:
1. English and multilingual Hindi/Hinglish transcription.
2. Code-switching prompt conditioning for Hinglish accuracy.
3. Configurable model sizes (tiny, base, small, medium) and compute types (float16 on CUDA, int8 on CPU).
4. Strict in-memory processing (RAM only, never touches disk or leaks to cloud).
"""

import os
import sys
import time
from typing import Optional, Tuple, Dict, Any
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

# Default code-switching prompt for Hinglish context
DEFAULT_HINGLISH_PROMPT = "Phenom, please file open karo aur analyze karo. Let's start the task."

class STTEngine:
    def __init__(self, model_size: str = "small", device: str = "cuda", compute_type: str = "float16"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language: Optional[str] = None # None = auto-detect; "en" = English; "hi" = Hindi
        self._model: Optional[faster_whisper.WhisperModel] = None

    def set_model(self, model_size: str, device: Optional[str] = None, compute_type: Optional[str] = None):
        """Allows switching STT model size (e.g. tiny, base, small, medium)."""
        if model_size != self.model_size or (device and device != self.device):
            self.model_size = model_size
            if device:
                self.device = device
            if compute_type:
                self.compute_type = compute_type
            self._model = None # Trigger reload on next call

    def _ensure_model_loaded(self):
        if self._model is None:
            try:
                self._model = faster_whisper.WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
            except Exception:
                # If CUDA is unavailable or saturated, fallback to CPU int8
                self._model = faster_whisper.WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8"
                )

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "is_multilingual": not self.model_size.endswith(".en")
        }

    def transcribe_audio_array(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None,
        initial_prompt: Optional[str] = None
    ) -> Tuple[str, float]:
        """
        Transcribes a 1D float32 or int16 numpy audio array in-memory.
        Supports Hindi/Hinglish via multilingual models and prompt conditioning.
        Returns (transcribed_text, latency_ms).
        Never touches the disk.
        """
        self._ensure_model_loaded()

        # Convert to float32 normalized between -1.0 and 1.0 if int16
        if audio_data.dtype == np.int16:
            audio_float = audio_data.astype(np.float32) / 32768.0
        else:
            audio_float = audio_data.astype(np.float32)

        # English-only models (.en) must use "en"
        if self.model_size.endswith(".en"):
            selected_language = "en"
            prompt = initial_prompt
        else:
            selected_language = language or self.language
            prompt = initial_prompt or DEFAULT_HINGLISH_PROMPT

        start_time = time.perf_counter()
        segments, info = self._model.transcribe(
            audio_float,
            language=selected_language,
            initial_prompt=prompt,
            beam_size=1,
            temperature=0.0,
            vad_filter=True # Use built-in Silero VAD to prune leading/trailing silence
        )
        
        text = " ".join([seg.text for seg in segments]).strip()
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return text, latency_ms

stt_engine = STTEngine()
