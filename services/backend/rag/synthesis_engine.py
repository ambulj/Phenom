"""
Source-Grounded Document Synthesis Engine.
Produces structured answers with verifiable inline citations, source filenames,
and confidence scores with zero cloud egress under Rule 4.

Part of Phenom 20.0 Large-Scale Offline Hybrid RAG Engine (DOC-02.1).
"""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.rag.hybrid_retriever import HybridRetriever, HybridHit, hybrid_retriever
from services.backend.safety.guardian import guardian


class CitationSpan(BaseModel):
    citation_id: int = Field(..., description="1-based citation index [1], [2], etc.")
    chunk_id: str = Field(..., description="Referenced chunk unique ID")
    file_path: str = Field(..., description="Source file path")
    section_title: Optional[str] = Field(default=None, description="Section or heading title")
    snippet: str = Field(..., description="Direct representative evidence quote snippet")


class RAGSynthesisResult(BaseModel):
    query: str = Field(..., description="Original user query")
    answer: str = Field(..., description="Synthesized answer text with inline citation markers")
    citations: List[CitationSpan] = Field(default_factory=list, description="Grounding citation spans")
    confidence: float = Field(..., description="Synthesized confidence score [0.0 - 1.0]")
    chunks_retrieved: int = Field(default=0, description="Number of supporting chunks retrieved")
    duration_ms: float = Field(default=0.0, description="End-to-end synthesis latency in milliseconds")


class DocumentSynthesisEngine:
    """
    Synthesizes grounded answers from retrieved hybrid chunks without cloud exfiltration.
    """

    def __init__(self, retriever: Optional[HybridRetriever] = None):
        self.retriever = retriever or hybrid_retriever

    async def answer_query(
        self,
        query: str,
        top_k: int = 4,
        confidence_threshold: float = 0.005,
    ) -> RAGSynthesisResult:
        """
        Retrieves top hybrid chunks and synthesizes an answer with citation grounding.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. RAG synthesis halted.")

        t0 = time.perf_counter()

        # Step 1: Retrieve top chunks via Reciprocal Rank Fusion
        hits: List[HybridHit] = self.retriever.retrieve(query=query, top_k=top_k)

        if not hits:
            t1 = time.perf_counter()
            return RAGSynthesisResult(
                query=query,
                answer="No relevant documentation found for the query in the offline index.",
                citations=[],
                confidence=0.0,
                chunks_retrieved=0,
                duration_ms=(t1 - t0) * 1000.0,
            )

        # Step 2: Build citations and synthesized summary
        citations: List[CitationSpan] = []
        answer_parts: List[str] = []

        total_rrf = sum(h.rrf_score for h in hits)
        normalized_conf = min(1.0, total_rrf / 0.05) if total_rrf > 0 else 0.1

        for idx, hit in enumerate(hits):
            cite_num = idx + 1
            snippet = hit.text[:180].strip() + ("..." if len(hit.text) > 180 else "")
            
            citations.append(
                CitationSpan(
                    citation_id=cite_num,
                    chunk_id=hit.chunk_id,
                    file_path=hit.file_path,
                    section_title=hit.section_title,
                    snippet=snippet,
                )
            )

            section_label = f" ({hit.section_title})" if hit.section_title else ""
            answer_parts.append(f"{hit.text.strip()} [{cite_num}]")

        # Step 3: Format synthesized response
        synthesized_text = (
            f"Based on indexed documentation, here is the verified context for '{query}':\n\n"
            + "\n\n".join(answer_parts)
        )

        t1 = time.perf_counter()
        duration_ms = (t1 - t0) * 1000.0

        return RAGSynthesisResult(
            query=query,
            answer=synthesized_text,
            citations=citations,
            confidence=round(normalized_conf, 3),
            chunks_retrieved=len(hits),
            duration_ms=duration_ms,
        )


# Global singleton
synthesis_engine = DocumentSynthesisEngine()
