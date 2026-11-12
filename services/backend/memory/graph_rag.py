"""
Phenom Hybrid GraphRAG Retrieval & Query Router
Coordinates:
1. Lexical Keyword Matching (In-memory BM25 / Inverted Index)
2. Dense Vector Semantic Retrieval (LocalEmbeddingPipeline 384-d embeddings)
3. Hybrid Score Fusion (0.4 * lexical + 0.6 * vector)
4. Graph Relational Expansion (1-hop / 2-hop traversal with distance attenuation)
5. Cross-Domain Context Synthesis & Explicit URI Citation Generation
6. Natural Language Query Intent Router
7. Zero-Cloud Leakage Invariant: 100% on-device local execution
"""

from __future__ import annotations

import logging
import math
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from services.backend.memory.embeddings import embedding_pipeline
from services.backend.memory.multi_source_graph import MultiSourceKnowledgeGraph, multi_source_graph
from services.backend.safety.guardian import guardian
from services.backend.schemas.graph_rag import (
    GraphEdge,
    GraphNode,
    GraphQueryResult,
)

logger = logging.getLogger("phenom.graph_rag")

TOKEN_SPLIT_REGEX = re.compile(r"[^a-zA-Z0-9_\-\.]+")


def tokenize(text: str) -> List[str]:
    """Tokenizes text into normalized lower-case terms."""
    if not text:
        return []
    tokens = TOKEN_SPLIT_REGEX.split(text.lower())
    return [t for t in tokens if len(t) > 1]


class BM25Index:
    """In-memory BM25 inverted index for lexical keyword search."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_len: Dict[str, int] = {}
        self.avg_doc_len: float = 0.0
        self.doc_count: int = 0
        self.inverted_index: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def build(self, documents: Dict[str, str]) -> None:
        """Builds inverted index from a dict of {node_id: text}."""
        self.doc_len.clear()
        self.inverted_index.clear()
        self.doc_count = len(documents)

        if self.doc_count == 0:
            self.avg_doc_len = 0.0
            return

        total_len = 0
        for doc_id, text in documents.items():
            tokens = tokenize(text)
            self.doc_len[doc_id] = len(tokens)
            total_len += len(tokens)
            for token in tokens:
                self.inverted_index[token][doc_id] += 1

        self.avg_doc_len = total_len / float(self.doc_count)

    def score(self, query: str) -> Dict[str, float]:
        """Calculates BM25 score for all matching documents."""
        query_tokens = tokenize(query)
        scores: Dict[str, float] = defaultdict(float)

        if not query_tokens or self.doc_count == 0 or self.avg_doc_len == 0.0:
            return scores

        for q in query_tokens:
            if q not in self.inverted_index:
                continue

            postings = self.inverted_index[q]
            n_q = len(postings)
            # Standard BM25 IDF formula
            idf = math.log(1.0 + (self.doc_count - n_q + 0.5) / (n_q + 0.5))

            for doc_id, freq in postings.items():
                d_len = self.doc_len.get(doc_id, 1)
                tf_component = (freq * (self.k1 + 1.0)) / (
                    freq + self.k1 * (1.0 - self.b + self.b * (d_len / self.avg_doc_len))
                )
                scores[doc_id] += idf * tf_component

        return scores


class HybridGraphRAGEngine:
    """
    Hybrid GraphRAG search engine combining lexical matching, dense semantic vectors,
    relational sub-graph traversal, and zero-cloud context synthesis.
    """

    def __init__(self, graph: Optional[MultiSourceKnowledgeGraph] = None):
        self.graph = graph or multi_source_graph
        self.bm25_index = BM25Index()
        self._vector_cache: Dict[str, np.ndarray] = {}
        self._index_version: int = 0
        self._halted: bool = False

    @property
    def is_halted(self) -> bool:
        return self._halted or self.graph.is_halted or getattr(guardian, "is_halted", False)

    def halt(self) -> None:
        """Halts the search engine synchronously."""
        self._halted = True
        logger.warning("HybridGraphRAGEngine halted by Guardian kill switch.")

    def reset(self) -> None:
        """Resets halted status."""
        self._halted = False
        logger.info("HybridGraphRAGEngine reset.")

    def refresh_indices(self) -> None:
        """Rebuilds BM25 index and updates dense vector embeddings in RAM."""
        if self.is_halted:
            raise PermissionError("HybridGraphRAGEngine is halted by Guardian.")

        all_nodes = self.graph.list_nodes()
        corpus: Dict[str, str] = {}
        nodes_to_embed: List[Tuple[str, str]] = []

        for node in all_nodes:
            text = f"{node.title} {node.summary} {' '.join(node.tags)} {node.entity_type} {node.domain}"
            corpus[node.node_id] = text

            if node.node_id not in self._vector_cache:
                nodes_to_embed.append((node.node_id, text))

        self.bm25_index.build(corpus)

        # Compute embeddings for new nodes
        if nodes_to_embed:
            texts = [item[1] for item in nodes_to_embed]
            vectors = embedding_pipeline.embed_texts(texts)
            for (node_id, _), vec in zip(nodes_to_embed, vectors):
                self._vector_cache[node_id] = vec

        # Purge stale nodes from vector cache
        current_ids = set(corpus.keys())
        stale_ids = [nid for nid in self._vector_cache if nid not in current_ids]
        for sid in stale_ids:
            self._vector_cache.pop(sid, None)

        self._index_version += 1
        logger.debug(f"GraphRAG indices refreshed. Total nodes indexed: {len(corpus)}")

    def classify_intent(self, query: str) -> Dict[str, float]:
        """
        Classifies user query intent and determines domain affinity weights.
        Returns domain weight multipliers.
        """
        q_lower = query.lower()
        weights = {
            "vault": 1.0,
            "code": 1.0,
            "doc": 1.0,
            "meeting": 1.0,
            "email": 1.0
        }

        # Code keywords
        if any(w in q_lower for w in ["code", "function", "class", "method", "ast", "commit", "bug", "repo", "implement", "pr"]):
            weights["code"] = 1.8

        # Meeting keywords
        if any(w in q_lower for w in ["meeting", "calendar", "agenda", "attendees", "sync", "call", "discuss"]):
            weights["meeting"] = 1.8

        # Vault keywords
        if any(w in q_lower for w in ["note", "vault", "second brain", "idea", "spec", "journal", "wikilink"]):
            weights["vault"] = 1.8

        # Document keywords
        if any(w in q_lower for w in ["pdf", "docx", "document", "sheet", "slide", "section", "doc"]):
            weights["doc"] = 1.8

        # Email keywords
        if any(w in q_lower for w in ["email", "gmail", "inbox", "sent", "thread", "message"]):
            weights["email"] = 1.8

        return weights

    def search_hybrid(
        self,
        query: str,
        top_k: int = 5,
        domain_filter: Optional[str] = None
    ) -> List[Tuple[GraphNode, float]]:
        """
        Executes hybrid BM25 + dense vector semantic search.
        Score = 0.4 * lexical_score + 0.6 * vector_score, multiplied by domain affinity.
        """
        if self.is_halted:
            raise PermissionError("HybridGraphRAGEngine is halted by Guardian.")

        self.refresh_indices()

        all_nodes = self.graph.list_nodes(domain=domain_filter)
        if not all_nodes:
            return []

        # 1. Lexical Scoring
        bm25_scores = self.bm25_index.score(query)
        max_bm25 = max(bm25_scores.values()) if bm25_scores else 1.0
        if max_bm25 <= 0.0:
            max_bm25 = 1.0

        # 2. Dense Vector Scoring
        query_vec = embedding_pipeline.embed_query(query)  # shape (384,)
        domain_weights = self.classify_intent(query)

        candidates: List[Tuple[GraphNode, float]] = []

        for node in all_nodes:
            # Lexical score normalized [0, 1]
            lex_score = (bm25_scores.get(node.node_id, 0.0) / max_bm25) if node.node_id in bm25_scores else 0.0

            # Dense cosine similarity normalized [0, 1]
            node_vec = self._vector_cache.get(node.node_id)
            if node_vec is not None:
                cos_sim = float(np.dot(query_vec, node_vec))
                vec_score = max(0.0, min(1.0, (cos_sim + 1.0) / 2.0))
            else:
                vec_score = 0.0

            # Hybrid score fusion
            fused_score = (0.4 * lex_score) + (0.6 * vec_score)

            # Apply domain affinity multiplier
            dom_mult = domain_weights.get(node.domain, 1.0)
            final_score = fused_score * dom_mult

            candidates.append((node, final_score))

        # Sort descending by final score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]

    def query(
        self,
        query: str,
        hops: int = 1,
        domain_filter: Optional[str] = None,
        top_k: int = 5
    ) -> GraphQueryResult:
        """
        Executes complete GraphRAG pipeline:
        1. Hybrid search retrieval to identify Top-K seed nodes.
        2. Relational graph traversal (1-hop or 2-hop) with distance decay attenuation.
        3. Cross-domain sub-graph synthesis with explicit URI citations.
        """
        if self.is_halted:
            raise PermissionError("HybridGraphRAGEngine is halted by Guardian.")

        seeds = self.search_hybrid(query, top_k=top_k, domain_filter=domain_filter)
        if not seeds:
            return GraphQueryResult(
                query=query,
                seed_nodes=[],
                expanded_nodes=[],
                edges=[],
                context_synthesis=f"No relevant knowledge graph entities found for query: '{query}'.",
                citations=[],
                traversal_depth=hops
            )

        seed_ids = [s[0].node_id for s in seeds]
        seed_scores = {s[0].node_id: s[1] for s in seeds}

        # Relational Expansion
        expanded_nodes_dict: Dict[str, Tuple[GraphNode, float, str]] = {}  # id -> (node, score, via_relation)
        traversed_edges: Set[GraphEdge] = set()
        visited: Set[str] = set(seed_ids)

        frontier = list(seed_ids)
        for h in range(1, hops + 1):
            next_frontier: List[str] = []
            attenuation = 0.7 ** h

            for curr_id in frontier:
                # Neighbors
                neighbors = self.graph.get_neighbors(curr_id, direction="both")
                curr_score = seed_scores.get(curr_id, 0.5)

                for neighbor_node, edge in neighbors:
                    traversed_edges.add(edge)
                    if neighbor_node.node_id not in visited:
                        visited.add(neighbor_node.node_id)
                        next_frontier.append(neighbor_node.node_id)
                        decayed_score = curr_score * edge.weight * attenuation
                        expanded_nodes_dict[neighbor_node.node_id] = (
                            neighbor_node,
                            decayed_score,
                            edge.relation
                        )

            frontier = next_frontier
            if not frontier:
                break

        # Convert to result models
        seed_dicts = [
            {
                "node_id": s[0].node_id,
                "title": s[0].title,
                "domain": s[0].domain,
                "entity_type": s[0].entity_type,
                "summary": s[0].summary,
                "score": round(s[1], 4),
            }
            for s in seeds
        ]

        expanded_dicts = [
            {
                "node_id": item[0].node_id,
                "title": item[0].title,
                "domain": item[0].domain,
                "entity_type": item[0].entity_type,
                "summary": item[0].summary,
                "attenuated_score": round(item[1], 4),
                "relation": item[2],
            }
            for item in sorted(expanded_nodes_dict.values(), key=lambda x: x[1], reverse=True)
        ]

        edge_dicts = [
            {
                "source": e.source_id,
                "target": e.target_id,
                "relation": e.relation,
                "weight": e.weight
            }
            for e in traversed_edges
        ]

        # Collect citations
        all_uris = list(seed_ids) + list(expanded_nodes_dict.keys())
        citations = sorted(list(set(all_uris)))

        # Synthesize prompt context
        synthesis_lines = [
            f"# Multi-Source Knowledge Graph Context: \"{query}\"",
            "",
            "## Core Seed Entities (Primary Matches):"
        ]

        for s in seed_dicts:
            synthesis_lines.append(
                f"- **[{s['node_id']}]** ({s['domain']}/{s['entity_type']}): {s['title']}\n"
                f"  Summary: {s['summary']}"
            )

        if expanded_dicts:
            synthesis_lines.append("")
            synthesis_lines.append(f"## Connected Cross-Domain Graph Context ({hops}-Hop Expansion):")
            for exp in expanded_dicts[:10]:
                synthesis_lines.append(
                    f"- **[{exp['node_id']}]** ({exp['domain']}/{exp['relation']}): {exp['title']}\n"
                    f"  Summary: {exp['summary']}"
                )

        synthesis_lines.append("")
        synthesis_lines.append("## Deterministic URI Citations:")
        for c in citations:
            synthesis_lines.append(f"- {c}")

        context_synthesis = "\n".join(synthesis_lines)

        return GraphQueryResult(
            query=query,
            seed_nodes=seed_dicts,
            expanded_nodes=expanded_dicts,
            edges=edge_dicts,
            context_synthesis=context_synthesis,
            citations=citations,
            traversal_depth=hops
        )


# Global singleton instance
graph_rag_engine = HybridGraphRAGEngine()
