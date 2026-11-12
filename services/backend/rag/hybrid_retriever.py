"""
Hybrid RAG Retriever with Reciprocal Rank Fusion (RRF).
Fuses Okapi BM25 keyword rankings with 384-dimensional dense vector embeddings
(all-MiniLM-L6-v2) via standard Reciprocal Rank Fusion (k=60), delivering
superior recall across technical and semantic search queries under Rule 4.

Part of Phenom 20.0 Large-Scale Offline Hybrid RAG Engine (RAG-02.3).
"""

import time
from typing import Any, Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field

from services.backend.rag.document_parser import ParsedChunk, ParsedDocument, document_parser
from services.backend.rag.bm25_index import BM25Index, BM25Hit, bm25_index
from services.backend.memory.vector_embeddings import vector_encoder
from services.backend.safety.guardian import guardian


class HybridHit(BaseModel):
    chunk_id: str = Field(..., description="Unique chunk identifier")
    rrf_score: float = Field(..., description="Combined Reciprocal Rank Fusion score")
    bm25_rank: Optional[int] = Field(default=None, description="Ordinal 1-based rank in BM25 index")
    vector_rank: Optional[int] = Field(default=None, description="Ordinal 1-based rank in Vector index")
    bm25_score: Optional[float] = Field(default=None, description="Raw BM25 score")
    vector_cosine: Optional[float] = Field(default=None, description="Raw cosine similarity score [0.0 - 1.0]")
    text: str = Field(..., description="Chunk text content")
    file_path: str = Field(..., description="Origin source file path")
    section_title: Optional[str] = Field(default=None, description="Origin section or heading")
    provenance: str = Field(default="hybrid", description="Retrieval source: consensus, bm25_only, vector_only")


class HybridRetriever:
    """
    Orchestrates dual-channel BM25 + Vector retrieval and merges results via Reciprocal Rank Fusion.
    """

    def __init__(self, bm25: Optional[BM25Index] = None):
        self.bm25 = bm25 or bm25_index
        # In-memory vector store: chunk_id -> np.ndarray (384,)
        self._vectors: Dict[str, np.ndarray] = {}
        # Chunk metadata store: chunk_id -> ParsedChunk
        self._chunks: Dict[str, ParsedChunk] = {}

    def ingest_document(
        self,
        file_path: str,
        chunk_size_words: int = 250,
        overlap_words: int = 40,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> ParsedDocument:
        """
        Parses a document, updates the in-memory BM25 index, and calculates dense vector embeddings.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Ingestion halted.")

        doc = document_parser.parse_file(
            file_path=file_path,
            chunk_size_words=chunk_size_words,
            overlap_words=overlap_words,
            custom_metadata=custom_metadata,
        )

        if not doc.chunks:
            return doc

        # 1. Update BM25 index
        self.bm25.add_chunks(doc.chunks)

        # 2. Extract texts and batch compute dense embeddings
        texts = [chunk.text for chunk in doc.chunks]
        embeddings = vector_encoder.encode(texts)

        # 3. Store vectors and chunks in registry
        for idx, chunk in enumerate(doc.chunks):
            cid = chunk.chunk_id
            self._chunks[cid] = chunk
            # If batch returned 2D array, slice row
            vec = embeddings[idx] if len(embeddings.shape) == 2 else embeddings
            self._vectors[cid] = vec

        return doc

    def search_vector(self, query: str, top_k: int = 20) -> List[tuple[str, float]]:
        """
        Computes cosine similarity between query embedding and all indexed chunk vectors.
        Returns list of (chunk_id, cosine_similarity) tuples sorted descending.
        """
        if not self._vectors:
            return []

        q_vec = vector_encoder.encode(query)
        if len(q_vec.shape) > 1:
            q_vec = q_vec[0]

        scores: List[tuple[str, float]] = []
        for cid, d_vec in self._vectors.items():
            # Vectors are unit normalized, dot product = cosine similarity
            sim = float(np.dot(q_vec, d_vec))
            scores.append((cid, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        rrf_k: int = 60,
        candidate_pool: int = 25,
    ) -> List[HybridHit]:
        """
        Executes dual-channel retrieval and applies Reciprocal Rank Fusion (RRF).
        RRF(d) = sum(1 / (k + rank))
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Hybrid retrieval halted.")

        t0 = time.perf_counter()

        # 1. Channel A: Lexical BM25 retrieval
        bm25_hits: List[BM25Hit] = self.bm25.search(query, top_k=candidate_pool)
        bm25_ranks: Dict[str, tuple[int, float]] = {
            hit.chunk_id: (hit.rank + 1, hit.score) for hit in bm25_hits
        }

        # 2. Channel B: Semantic Vector retrieval
        vec_hits: List[tuple[str, float]] = self.search_vector(query, top_k=candidate_pool)
        vec_ranks: Dict[str, tuple[int, float]] = {
            cid: (rank + 1, sim) for rank, (cid, sim) in enumerate(vec_hits)
        }

        # 3. Reciprocal Rank Fusion
        all_cids = set(bm25_ranks.keys()) | set(vec_ranks.keys())
        rrf_scores: Dict[str, float] = {}

        for cid in all_cids:
            score = 0.0
            if cid in bm25_ranks:
                r_bm25 = bm25_ranks[cid][0]
                score += 1.0 / (rrf_k + r_bm25)
            if cid in vec_ranks:
                r_vec = vec_ranks[cid][0]
                score += 1.0 / (rrf_k + r_vec)
            rrf_scores[cid] = score

        # Sort combined results descending
        ranked_cids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results: List[HybridHit] = []
        for cid, rrf_score in ranked_cids:
            chunk = self._chunks.get(cid) or self.bm25.chunks.get(cid)
            if not chunk:
                continue

            in_bm25 = cid in bm25_ranks
            in_vec = cid in vec_ranks

            if in_bm25 and in_vec:
                provenance = "consensus"
            elif in_bm25:
                provenance = "bm25_only"
            else:
                provenance = "vector_only"

            results.append(
                HybridHit(
                    chunk_id=cid,
                    rrf_score=float(rrf_score),
                    bm25_rank=bm25_ranks[cid][0] if in_bm25 else None,
                    vector_rank=vec_ranks[cid][0] if in_vec else None,
                    bm25_score=bm25_ranks[cid][1] if in_bm25 else None,
                    vector_cosine=vec_ranks[cid][1] if in_vec else None,
                    text=chunk.text,
                    file_path=chunk.file_path,
                    section_title=chunk.section_title,
                    provenance=provenance,
                )
            )

        t1 = time.perf_counter()
        _elapsed_ms = (t1 - t0) * 1000.0
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Returns hybrid retriever statistics."""
        return {
            "bm25_stats": self.bm25.get_stats(),
            "indexed_vectors": len(self._vectors),
            "indexed_chunks": len(self._chunks),
        }

    def clear(self) -> None:
        """Clears all indexed chunks and vectors."""
        self.bm25.clear()
        self._vectors.clear()
        self._chunks.clear()


# Global singleton
hybrid_retriever = HybridRetriever()
