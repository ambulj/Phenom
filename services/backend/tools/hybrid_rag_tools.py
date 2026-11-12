"""
Safety-Wrapped Offline Hybrid RAG Tools.
Registers tools with ToolRegistry for document ingestion, hybrid BM25 + vector search,
and source-grounded citation synthesis under Rule 4 (Phase 20-03 RAG-02.1 / RAG-02.2 / DOC-02.1).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.rag.hybrid_retriever import hybrid_retriever
from services.backend.rag.synthesis_engine import synthesis_engine


# ==========================================
# 1. Ingest RAG Document (Tier 0)
# ==========================================

class IngestRAGDocumentArgs(BaseModel):
    file_path: str = Field(..., description="Absolute path to document (PDF, DOCX, MD, Code, TXT).")
    chunk_size_words: Optional[int] = Field(default=250, description="Word count per chunk.")
    overlap_words: Optional[int] = Field(default=40, description="Overlap words between consecutive chunks.")

def ingest_rag_document_preview(args: Dict[str, Any]) -> str:
    path = args.get("file_path", "")
    return f"Parse and index document '{path}' into offline hybrid BM25 and vector stores."

@registry.register(
    name="ingest_rag_document",
    tier=0,
    description="Parses and indexes a document into offline BM25 and 384d vector stores.",
    args_schema=IngestRAGDocumentArgs,
    preview_fn=ingest_rag_document_preview,
    can_remember_per_folder=False
)
def handle_ingest_rag_document(
    file_path: str,
    chunk_size_words: int = 250,
    overlap_words: int = 40
) -> Dict[str, Any]:
    doc = hybrid_retriever.ingest_document(
        file_path=file_path,
        chunk_size_words=chunk_size_words,
        overlap_words=overlap_words,
    )
    return {
        "doc_id": doc.doc_id,
        "file_name": doc.file_name,
        "file_type": doc.file_type,
        "total_chunks": doc.total_chunks,
        "raw_char_count": doc.raw_char_count,
    }


# ==========================================
# 2. Hybrid RAG Search (Tier 0)
# ==========================================

class HybridRAGSearchArgs(BaseModel):
    query: str = Field(..., description="Search query string.")
    top_k: Optional[int] = Field(default=5, description="Number of top hits to return.")
    rrf_k: Optional[int] = Field(default=60, description="Reciprocal Rank Fusion constant.")

def hybrid_rag_search_preview(args: Dict[str, Any]) -> str:
    query = args.get("query", "")
    top_k = args.get("top_k", 5)
    return f"Execute hybrid BM25 + dense vector search for '{query}' (top {top_k} results)."

@registry.register(
    name="hybrid_rag_search",
    tier=0,
    description="Performs dual-channel BM25 and dense vector search fused via Reciprocal Rank Fusion.",
    args_schema=HybridRAGSearchArgs,
    preview_fn=hybrid_rag_search_preview,
    can_remember_per_folder=False
)
def handle_hybrid_rag_search(
    query: str,
    top_k: int = 5,
    rrf_k: int = 60
) -> List[Dict[str, Any]]:
    hits = hybrid_retriever.retrieve(query=query, top_k=top_k, rrf_k=rrf_k)
    return [hit.model_dump() for hit in hits]


# ==========================================
# 3. Synthesize Document Answer (Tier 0)
# ==========================================

class SynthesizeDocumentAnswerArgs(BaseModel):
    query: str = Field(..., description="Question to answer using indexed documents.")
    top_k: Optional[int] = Field(default=4, description="Number of supporting chunks to fuse.")

def synthesize_document_answer_preview(args: Dict[str, Any]) -> str:
    query = args.get("query", "")
    return f"Synthesize source-grounded answer with inline citations for query '{query}'."

@registry.register(
    name="synthesize_document_answer",
    tier=0,
    description="Synthesizes source-grounded answer with inline citations from offline documents.",
    args_schema=SynthesizeDocumentAnswerArgs,
    preview_fn=synthesize_document_answer_preview,
    can_remember_per_folder=False
)
async def handle_synthesize_document_answer(
    query: str,
    top_k: int = 4
) -> Dict[str, Any]:
    result = await synthesis_engine.answer_query(query=query, top_k=top_k)
    return result.model_dump()


# ==========================================
# 4. Get RAG Index Stats (Tier 0)
# ==========================================

class GetRAGIndexStatsArgs(BaseModel):
    pass

def get_rag_index_stats_preview(args: Dict[str, Any]) -> str:
    return "Retrieve offline hybrid RAG index metrics, vocabulary size, and chunk counts."

@registry.register(
    name="get_rag_index_stats",
    tier=0,
    description="Returns metrics on indexed RAG documents, chunks, and vocabulary.",
    args_schema=GetRAGIndexStatsArgs,
    preview_fn=get_rag_index_stats_preview,
    can_remember_per_folder=False
)
def handle_get_rag_index_stats() -> Dict[str, Any]:
    return hybrid_retriever.get_stats()
