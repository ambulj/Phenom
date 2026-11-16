"""Hybrid Associative Memory Retriever for Phenom (Milestone 49 Phase 1).

Combines:
1. Okapi BM25 lexical token matching across entity names, content, and tags.
2. Dense semantic embedding cosine similarity (SentenceTransformer / CPU ONNX).
3. Exponential temporal recency decay based on valid occurrence time (T_v).
4. NetworkX graph topology and multi-hop neighborhood expansion.
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from services.backend.schemas.temporal_graph import (
    AssociativeQuery,
    EntityType,
    MemorySearchResult,
    TemporalEntity,
)
from services.backend.memory.temporal_graph_engine import TemporalGraphEngine
from services.backend.memory.vector_embeddings import vector_encoder, VectorEmbeddingEncoder
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.memory.associative_retriever")

_TOKEN_RE = re.compile(r"\b\w{2,}\b")


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in _TOKEN_RE.findall(text)]


class AssociativeRetriever:
    """Fuses BM25 lexical ranking, dense vector search, temporal decay, and graph structure."""

    def __init__(
        self,
        engine: TemporalGraphEngine,
        encoder: Optional[VectorEmbeddingEncoder] = None,
        k1: float = 1.5,
        b: float = 0.75,
        weight_lexical: float = 0.45,
        weight_semantic: float = 0.40,
        weight_graph: float = 0.15,
    ) -> None:
        self.engine = engine
        self.encoder = encoder or vector_encoder
        self.k1 = k1
        self.b = b
        self.w_lex = weight_lexical
        self.w_sem = weight_semantic
        self.w_graph = weight_graph

    def search(self, query: AssociativeQuery) -> List[MemorySearchResult]:
        """Executes a hybrid associative query over the knowledge graph."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Memory retrieval aborted.")

        # 1. Fetch candidate entities under valid/transaction constraints
        candidates = self._fetch_candidates(query)
        if not candidates:
            return []

        # 2. Compute BM25 Lexical Scores
        bm25_scores = self._compute_bm25(query.query, candidates)

        # 3. Compute Dense Vector Semantic Scores
        sem_scores = self._compute_semantic(query.query, candidates)

        # 4. Compute Temporal Decay Scores
        ref_time = query.as_of_valid_time if query.as_of_valid_time is not None else float(np.max([c.valid_from for c in candidates]))
        decay_factors = self._compute_temporal_decay(candidates, ref_time, query.half_life_days)

        # 5. Compute Graph Centrality / Proximity Scores
        graph_scores = self._compute_graph_scores(candidates)

        # 6. Rank and Assemble Results
        ranked_results: List[MemorySearchResult] = []
        for i, ent in enumerate(candidates):
            lex = bm25_scores.get(ent.id, 0.0)
            sem = sem_scores.get(ent.id, 0.0)
            dec = decay_factors.get(ent.id, 1.0)
            grp = graph_scores.get(ent.id, 0.0)

            # Combined base score multiplied by temporal decay
            base = (self.w_lex * lex) + (self.w_sem * sem) + (self.w_graph * grp)
            comp = base * dec

            # 1-hop or 2-hop neighborhood expansion if requested
            related: List[Dict[str, Any]] = []
            if query.include_neighbors:
                neigh = self.engine.get_neighborhood(
                    ent.id,
                    max_hops=min(query.max_hops, 2),
                    as_of_valid_time=query.as_of_valid_time,
                )
                related = [
                    {"id": n["id"], "name": n.get("name"), "type": n.get("entity_type")}
                    for n in neigh.get("nodes", [])
                    if n["id"] != ent.id
                ][:5]

            ranked_results.append(
                MemorySearchResult(
                    entity=ent,
                    composite_score=round(float(comp), 4),
                    lexical_score=round(float(lex), 4),
                    semantic_score=round(float(sem), 4),
                    temporal_decay_factor=round(float(dec), 4),
                    graph_proximity_score=round(float(grp), 4),
                    related_entities=related,
                )
            )

        ranked_results.sort(key=lambda r: r.composite_score, reverse=True)
        return ranked_results[: query.top_k]

    def _fetch_candidates(self, query: AssociativeQuery) -> List[TemporalEntity]:
        all_active = self.engine.get_all_active_entities()
        candidates: List[TemporalEntity] = []

        for ent in all_active:
            # Check entity type filter
            if query.entity_types and ent.entity_type not in query.entity_types:
                continue

            # Check transaction time perspective
            if query.as_of_transaction_time is not None:
                if not ent.was_recorded_by(query.as_of_transaction_time):
                    continue

            # Check valid time perspective
            if query.as_of_valid_time is not None:
                if not ent.is_valid_at(query.as_of_valid_time):
                    continue

            candidates.append(ent)

        return candidates

    def _compute_bm25(self, query_text: str, candidates: List[TemporalEntity]) -> Dict[str, float]:
        """Calculates normalized Okapi BM25 scores for candidates."""
        q_tokens = _tokenize(query_text)
        if not q_tokens or not candidates:
            return {c.id: 0.0 for c in candidates}

        doc_tokens_map = {
            c.id: _tokenize(f"{c.name} {c.content} {' '.join(c.tags)}")
            for c in candidates
        }

        # Corpus metrics
        N = len(candidates)
        avgdl = np.mean([len(tokens) for tokens in doc_tokens_map.values()]) or 1.0

        # Document frequency for query terms
        df: Dict[str, int] = {}
        for q in q_tokens:
            df[q] = sum(1 for tokens in doc_tokens_map.values() if q in tokens)

        # IDF with smoothing
        idf = {
            q: math.log((N - df[q] + 0.5) / (df[q] + 0.5) + 1.0)
            for q in q_tokens
        }

        raw_scores: Dict[str, float] = {}
        for c in candidates:
            doc_tokens = doc_tokens_map[c.id]
            doc_len = len(doc_tokens)
            score = 0.0
            term_counts: Dict[str, int] = {}
            for t in doc_tokens:
                term_counts[t] = term_counts.get(t, 0) + 1

            for q in q_tokens:
                if q in term_counts:
                    tf = term_counts[q]
                    numerator = idf[q] * tf * (self.k1 + 1.0)
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / avgdl))
                    score += numerator / (denominator or 1.0)
            raw_scores[c.id] = max(0.0, score)

        # Normalize to [0, 1]
        max_s = max(raw_scores.values()) if raw_scores else 0.0
        if max_s > 0.0:
            return {cid: score / max_s for cid, score in raw_scores.items()}
        return {c.id: 0.0 for c in candidates}

    def _compute_semantic(self, query_text: str, candidates: List[TemporalEntity]) -> Dict[str, float]:
        """Calculates dense vector cosine similarity for candidates."""
        if not candidates or not query_text.strip():
            return {c.id: 0.0 for c in candidates}

        q_emb = self.encoder.encode(query_text)
        # Ensure 1D array
        if q_emb.ndim > 1:
            q_emb = q_emb[0]
        q_norm = np.linalg.norm(q_emb) or 1.0

        doc_texts = [f"{c.name}: {c.content}" for c in candidates]
        doc_embs = self.encoder.encode(doc_texts)
        if doc_embs.ndim == 1:
            doc_embs = np.expand_dims(doc_embs, 0)

        scores: Dict[str, float] = {}
        for i, c in enumerate(candidates):
            d_emb = doc_embs[i]
            d_norm = np.linalg.norm(d_emb) or 1.0
            cos = float(np.dot(q_emb, d_emb) / (q_norm * d_norm))
            # Rescale [-1, 1] to [0, 1]
            scores[c.id] = max(0.0, min(1.0, (cos + 1.0) / 2.0))

        return scores

    def _compute_temporal_decay(
        self,
        candidates: List[TemporalEntity],
        reference_time: float,
        half_life_days: float,
    ) -> Dict[str, float]:
        """Calculates exponential time-decay factor based on valid time distance."""
        decay_lambda = math.log(2.0) / (half_life_days * 86400.0)
        factors: Dict[str, float] = {}
        for c in candidates:
            delta_seconds = abs(reference_time - c.valid_from)
            # Factor in [0, 1]
            decay = math.exp(-decay_lambda * delta_seconds)
            factors[c.id] = max(0.01, min(1.0, decay))
        return factors

    def _compute_graph_scores(self, candidates: List[TemporalEntity]) -> Dict[str, float]:
        """Computes network graph centrality score for candidates."""
        scores: Dict[str, float] = {}
        total_nodes = len(self.engine.graph.nodes)
        if total_nodes <= 1:
            return {c.id: 0.5 for c in candidates}

        for c in candidates:
            if c.id in self.engine.graph:
                degree = self.engine.graph.degree(c.id)
                # Degree normalized against max possible degrees in sub-universe
                score = min(1.0, degree / max(1, min(total_nodes - 1, 10)))
                scores[c.id] = float(score)
            else:
                scores[c.id] = 0.0

        return scores
