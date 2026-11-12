"""
Phenom Local Embedding Pipeline
Provides fast, 100% on-device text vector embeddings using sentence-transformers.
Prefers CUDA on NVIDIA RTX GPUs with automatic CPU fallback.
Normalized 384-dimensional dense vectors for sub-millisecond cosine similarity search.
"""

import hashlib
import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger("phenom.embeddings")


class LocalEmbeddingPipeline:
    """
    Local embedding encoder wrapping sentence-transformers with lazy loading
    and zero-network fallback for offline / test resilience.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: Optional[str] = None):
        self.model_name = model_name
        self._device = device
        self._model = None
        self._dimension = 384

    @property
    def dimension(self) -> int:
        return self._dimension

    def _get_device(self) -> str:
        if self._device:
            return self._device
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                dev = self._get_device()
                logger.info(f"Loading local embedding model '{self.model_name}' on device '{dev}'")
                self._model = SentenceTransformer(self.model_name, device=dev)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer '{self.model_name}' ({e}). Using deterministic offline fallback.")
                self._model = None
        return self._model

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Embeds a batch of texts into L2-normalized float32 vectors.
        Shape: (len(texts), 384).
        """
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)

        model = self._get_model()
        if model is not None:
            try:
                vectors = model.encode(
                    texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False
                )
                return vectors.astype(np.float32)
            except Exception as e:
                logger.warning(f"SentenceTransformer encoding failed ({e}). Falling back to deterministic embeddings.")

        # Resilient offline/test fallback: deterministic normalized vector based on SHA256 seed
        embeddings = []
        for text in texts:
            seed = int(hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:8], 16)
            rng = np.random.RandomState(seed)
            raw = rng.randn(self._dimension).astype(np.float32)
            norm = float(np.linalg.norm(raw))
            vec = (raw / norm) if norm > 1e-6 else raw
            embeddings.append(vec)

        return np.array(embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embeds a single query string into a 1D vector of shape (384,)."""
        res = self.embed_texts([query])
        return res[0]


# Global singleton
embedding_pipeline = LocalEmbeddingPipeline()
