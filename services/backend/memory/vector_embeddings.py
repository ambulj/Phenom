"""
Fast Dense Vector Embedding Pipeline (MEM-02.1).
Produces 384-dimensional dense vector embeddings for associative memory and semantic recall.
Runs on CPU/ONNX runtime to preserve 100% of GPU VRAM for the primary LLM and vision pipelines.
Includes deterministic offline fallback for airgapped environments and instantaneous testing.
"""

import os
import hashlib
import logging
from typing import List, Union
import numpy as np

# Enforce 100% offline local embeddings under Rule 4
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

logger = logging.getLogger("phenom.vector_embeddings")


class VectorEmbeddingEncoder:
    """Encodes text passages into 384-dimensional L2-normalized float32 dense vectors."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.dimension = 384
        self._model = None
        self._initialized = False

    def _load_model(self):
        if not self._initialized:
            try:
                import os
                os.environ["HF_HUB_OFFLINE"] = "1"
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
                from sentence_transformers import SentenceTransformer
                # Force CPU to guarantee zero GPU VRAM consumption and offline loading
                try:
                    self._model = SentenceTransformer(self.model_name, device="cpu", local_files_only=True)
                except Exception:
                    self._model = SentenceTransformer(self.model_name, device="cpu")
                # Warm up encoder
                self._model.encode(["warmup"], normalize_embeddings=True, show_progress_bar=False)
                logger.info(f"Loaded embedding model '{self.model_name}' on CPU.")
            except Exception as e:
                logger.warning(f"Could not initialize SentenceTransformer '{self.model_name}' ({e}). Using deterministic offline embedding generator.")
                self._model = None
            self._initialized = True

    def encode(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Encodes a single string or list of strings into unit-normalized float32 vectors.
        Returns array of shape (384,) if single string, or (N, 384) if list.
        """
        is_single = isinstance(text, str)
        texts = [text] if is_single else list(text)

        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        self._load_model()

        if self._model is not None:
            try:
                embeddings = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
                res = np.array(embeddings, dtype=np.float32)
                return res[0] if is_single else res
            except Exception:
                pass

        # Offline deterministic fallback: multi-seeded SHA256 projection
        vectors = []
        for t in texts:
            vec = np.zeros(self.dimension, dtype=np.float32)
            for i in range(self.dimension):
                h = hashlib.sha256(f"{t}_dim_{i}".encode("utf-8")).digest()
                val = (int.from_bytes(h[:4], "little", signed=True) / 2147483648.0)
                vec[i] = val
            norm = np.linalg.norm(vec)
            if norm > 1e-6:
                vec = vec / norm
            vectors.append(vec)

        res = np.array(vectors, dtype=np.float32)
        return res[0] if is_single else res


# Global singleton instance
vector_encoder = VectorEmbeddingEncoder()
