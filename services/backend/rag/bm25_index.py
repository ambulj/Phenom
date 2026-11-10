"""
High-Speed In-Memory Okapi BM25 Inverted Index.
Provides sub-5ms lexical keyword search with term frequency saturation
and document length normalization (k1=1.5, b=0.75).

Part of Phenom 20.0 Large-Scale Offline Hybrid RAG Engine (RAG-02.2).
"""

import math
import re
import time
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from services.backend.rag.document_parser import ParsedChunk
from services.backend.safety.guardian import guardian


class BM25Hit(BaseModel):
    chunk_id: str = Field(..., description="Matched chunk ID")
    score: float = Field(..., description="Raw BM25 relevance score")
    rank: int = Field(..., description="Zero-indexed ordinal rank")
    text: str = Field(..., description="Chunk content text")
    file_path: str = Field(..., description="Source file path")
    section_title: Optional[str] = Field(default=None, description="Section heading")


class BM25Index:
    """
    In-memory Okapi BM25 keyword search index.
    """

    STOPWORDS: Set[str] = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
        "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
        "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
        "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
        "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
        "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
        "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more",
        "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
        "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
        "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
        "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they",
        "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under",
        "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
        "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom",
        "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've",
        "your", "yours", "yourself", "yourselves"
    }

    TOKEN_RE = re.compile(r"[A-Za-z0-9_\-\.]+")

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        # Inverted index: term -> {chunk_id: term_frequency}
        self.postings: Dict[str, Dict[str, int]] = {}
        # Metadata storage: chunk_id -> ParsedChunk
        self.chunks: Dict[str, ParsedChunk] = {}
        # Document lengths: chunk_id -> length in tokens
        self.doc_lens: Dict[str, int] = {}
        self.total_tokens: int = 0

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenizes text into normalized alphanumeric keywords, filtering standard English stopwords.
        Preserves technical code terms (e.g. `ast_parser`, `MiniLM`).
        """
        raw_tokens = self.TOKEN_RE.findall(text.lower())
        return [t for t in raw_tokens if t not in self.STOPWORDS and len(t) > 1]

    def add_chunk(self, chunk: ParsedChunk) -> None:
        """
        Adds a single ParsedChunk to the inverted index.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Inverted index update halted.")

        cid = chunk.chunk_id
        # If chunk already present, remove it first to avoid double counting
        if cid in self.chunks:
            self._remove_chunk(cid)

        tokens = self.tokenize(chunk.text)
        doc_len = len(tokens)
        self.doc_lens[cid] = doc_len
        self.total_tokens += doc_len
        self.chunks[cid] = chunk

        # Count frequencies
        freqs: Dict[str, int] = {}
        for token in tokens:
            freqs[token] = freqs.get(token, 0) + 1

        for token, count in freqs.items():
            if token not in self.postings:
                self.postings[token] = {}
            self.postings[token][cid] = count

    def add_chunks(self, chunks: List[ParsedChunk]) -> int:
        """
        Batch adds multiple chunks. Returns count of indexed chunks.
        """
        for chunk in chunks:
            self.add_chunk(chunk)
        return len(chunks)

    def _remove_chunk(self, chunk_id: str) -> None:
        """Removes a chunk from the index."""
        if chunk_id not in self.chunks:
            return
        old_len = self.doc_lens.pop(chunk_id, 0)
        self.total_tokens = max(0, self.total_tokens - old_len)
        self.chunks.pop(chunk_id, None)

        # Clean from postings
        for term in list(self.postings.keys()):
            self.postings[term].pop(chunk_id, None)
            if not self.postings[term]:
                del self.postings[term]

    def search(self, query: str, top_k: int = 10) -> List[BM25Hit]:
        """
        Executes an Okapi BM25 lexical ranking query in < 5ms.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. BM25 search halted.")

        t0 = time.perf_counter()
        query_tokens = self.tokenize(query)
        if not query_tokens or not self.chunks:
            return []

        N = len(self.chunks)
        avgdl = self.total_tokens / N if N > 0 else 1.0

        scores: Dict[str, float] = {}

        for q in query_tokens:
            if q not in self.postings:
                continue

            posting = self.postings[q]
            n_q = len(posting)
            # Standard Okapi IDF
            idf = math.log(((N - n_q + 0.5) / (n_q + 0.5)) + 1.0)

            for cid, f_qd in posting.items():
                D_len = self.doc_lens.get(cid, 0)
                denom = f_qd + self.k1 * (1.0 - self.b + self.b * (D_len / avgdl))
                term_score = idf * ((f_qd * (self.k1 + 1.0)) / denom)
                scores[cid] = scores.get(cid, 0.0) + term_score

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        hits: List[BM25Hit] = []
        for rank, (cid, score) in enumerate(ranked):
            chunk = self.chunks[cid]
            hits.append(
                BM25Hit(
                    chunk_id=cid,
                    score=float(score),
                    rank=rank,
                    text=chunk.text,
                    file_path=chunk.file_path,
                    section_title=chunk.section_title,
                )
            )

        t1 = time.perf_counter()
        _elapsed_ms = (t1 - t0) * 1000.0
        return hits

    def get_stats(self) -> Dict[str, Any]:
        """Returns index metrics."""
        n_chunks = len(self.chunks)
        return {
            "indexed_chunks": n_chunks,
            "vocabulary_size": len(self.postings),
            "total_tokens": self.total_tokens,
            "avg_chunk_tokens": (self.total_tokens / n_chunks) if n_chunks > 0 else 0.0,
        }

    def clear(self) -> None:
        """Resets the index."""
        self.postings.clear()
        self.chunks.clear()
        self.doc_lens.clear()
        self.total_tokens = 0


# Global singleton
bm25_index = BM25Index()
