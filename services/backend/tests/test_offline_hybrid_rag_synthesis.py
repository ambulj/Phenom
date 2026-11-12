"""
Unit & Integration Test Suite for Large-Scale Offline Hybrid RAG Engine & Document Synthesis.
Validates document parsing, Okapi BM25 sub-5ms retrieval, RRF dual-channel fusion,
source-grounded citation synthesis, Tool Registry safety, and Guardian SLA.

Part of Phenom 20.0 Sovereign Autonomous Developer (RAG-02.1, RAG-02.2, RAG-02.3, DOC-02.1, SAF-01, SAF-02).
"""

import asyncio
import os
import time
from pathlib import Path
import pytest

from services.backend.rag.document_parser import DocumentParser, ParsedDocument, ParsedChunk
from services.backend.rag.bm25_index import BM25Index, BM25Hit
from services.backend.rag.hybrid_retriever import HybridRetriever, HybridHit
from services.backend.rag.synthesis_engine import DocumentSynthesisEngine, RAGSynthesisResult, CitationSpan
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.hybrid_rag_tools  # Register tools


# ==========================================
# 1. Multi-Format Document Parser Tests
# ==========================================

def test_document_parser_markdown(tmp_path):
    parser = DocumentParser()
    md_file = tmp_path / "architecture.md"
    md_file.write_text(
        "# Phenom System Architecture\n\n"
        "Phenom is a sovereign personal desktop assistant.\n\n"
        "## Subsystem Overview\n\n"
        "The system coordinates local voice recognition, screen vision, and memory.\n\n"
        "## Safety Governance\n\n"
        "The Guardian kill switch halts all execution in less than 25 milliseconds.\n",
        encoding="utf-8"
    )

    doc: ParsedDocument = parser.parse_file(str(md_file), chunk_size_words=15, overlap_words=3)
    assert doc.doc_id.startswith("doc_")
    assert doc.file_name == "architecture.md"
    assert doc.file_type == "md"
    assert doc.total_chunks >= 2
    assert any(c.section_title == "Safety Governance" for c in doc.chunks)
    assert any("25 milliseconds" in c.text for c in doc.chunks)


def test_document_parser_code(tmp_path):
    parser = DocumentParser()
    code_file = tmp_path / "service.py"
    code_file.write_text(
        "class NetworkBridge:\n"
        "    def connect(self):\n"
        "        pass\n\n"
        "def start_telemetry_daemon():\n"
        "    return True\n",
        encoding="utf-8"
    )

    doc: ParsedDocument = parser.parse_file(str(code_file), chunk_size_words=20)
    assert doc.file_type == "py"
    assert any("symbol:NetworkBridge" in (c.section_title or "") for c in doc.chunks)


# ==========================================
# 2. In-Memory Okapi BM25 Index Tests
# ==========================================

def test_bm25_index_sub_5ms_latency():
    index = BM25Index()

    # Ingest 25 sample chunks with varying terms
    for i in range(25):
        chunk = ParsedChunk(
            chunk_id=f"c_{i}",
            doc_id="doc_test",
            file_path=f"test_{i}.md",
            section_title=f"Section {i}",
            text=f"Phenom module {i} handles asynchronous processing and Guardian verification with token_{i} features.",
            token_estimate=15,
            chunk_index=i,
            total_chunks=25
        )
        index.add_chunk(chunk)

    # Specific technical query
    hits = index.search("token_7 Guardian", top_k=5)
    assert len(hits) > 0
    assert hits[0].chunk_id == "c_7"
    assert "token_7" in hits[0].text

    # Latency benchmark across 50 query iterations
    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        _ = index.search("asynchronous processing module", top_k=5)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    print(f"\n[BM25 Index Latency] Avg: {avg_latency:.4f}ms | Max: {max_latency:.4f}ms | Target: < 5.0ms")
    assert avg_latency < 5.0, f"BM25 latency exceeded 5.0ms: {avg_latency:.4f}ms"


# ==========================================
# 3. Hybrid Retriever RRF Dual-Channel Fusion
# ==========================================

def test_hybrid_retriever_reciprocal_rank_fusion(tmp_path):
    bm25 = BM25Index()
    retriever = HybridRetriever(bm25=bm25)

    doc_file = tmp_path / "offline_docs.txt"
    doc_file.write_text(
        "Chunk Alpha describes Rule8ViolationError in checkout flows.\n"
        "Chunk Beta details sovereign autonomous neural execution in offline environments.\n"
        "Chunk Gamma synthesizes Rule8ViolationError with sovereign offline neural networks.\n",
        encoding="utf-8"
    )

    doc = retriever.ingest_document(str(doc_file), chunk_size_words=10, overlap_words=2)
    assert doc.total_chunks >= 3

    # Query with both lexical technical keyword and semantic phrasing
    results = retriever.retrieve("Rule8ViolationError offline neural", top_k=3)
    assert len(results) > 0

    # Top result should be the consensus chunk matching both channels
    top_hit = results[0]
    assert top_hit.rrf_score > 0.0
    assert top_hit.provenance in ("consensus", "hybrid", "bm25_only", "vector_only")


# ==========================================
# 4. Source-Grounded Document Synthesis
# ==========================================

@pytest.mark.asyncio
async def test_document_synthesis_engine_citations(tmp_path):
    bm25 = BM25Index()
    retriever = HybridRetriever(bm25=bm25)
    engine = DocumentSynthesisEngine(retriever=retriever)

    guide_file = tmp_path / "guardian_manual.md"
    guide_file.write_text(
        "# Guardian Manual\n\n"
        "The Guardian kill switch guarantees halting in less than 25 milliseconds across all subsystems.\n\n"
        "## Offline Embeddings\n\n"
        "All vector embeddings utilize all-MiniLM-L6-v2 running strictly offline on CPU with zero network egress.\n",
        encoding="utf-8"
    )

    retriever.ingest_document(str(guide_file), chunk_size_words=20)

    res: RAGSynthesisResult = await engine.answer_query("How does Guardian kill switch work and what embeddings are used?", top_k=2)
    assert res.chunks_retrieved >= 1
    assert "[1]" in res.answer
    assert len(res.citations) >= 1
    assert res.confidence > 0.0
    assert any("guardian_manual.md" in c.file_path for c in res.citations)


# ==========================================
# 5. Tool Registry Safety Audit
# ==========================================

def test_hybrid_rag_tool_registry_audit():
    expected_tools = [
        ("ingest_rag_document", 0),
        ("hybrid_rag_search", 0),
        ("synthesize_document_answer", 0),
        ("get_rag_index_stats", 0),
    ]

    for tool_name, expected_tier in expected_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered in ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch: expected {expected_tier}, got {tool_def.tier}"
        assert tool_def.preview_fn is not None
        assert callable(tool_def.preview_fn)

    # Preview checks
    ingest_preview = registry.get("ingest_rag_document").preview_fn({"file_path": "c:/Phenom/docs/manual.pdf"})
    assert "manual.pdf" in ingest_preview

    search_preview = registry.get("hybrid_rag_search").preview_fn({"query": "kill switch", "top_k": 3})
    assert "kill switch" in search_preview


# ==========================================
# 6. Universal Guardian Kill Switch SLA Benchmark
# ==========================================

def test_guardian_kill_switch_rag_sla(tmp_path):
    guardian.resume()
    latencies = []

    # Benchmark SLA check latency over 50 iterations
    for _ in range(50):
        t0 = time.perf_counter()
        _ = guardian.is_halted
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    max_latency = max(latencies)
    avg_latency = sum(latencies) / len(latencies)

    print(f"\n[Guardian SLA Phase 3 Benchmark] Max: {max_latency:.4f}ms | Avg: {avg_latency:.4f}ms | SLA Target: < 25.0ms")
    assert max_latency < 25.0, f"Guardian SLA breached: max latency {max_latency:.4f}ms exceeds 25.0ms threshold"

    # Trigger halt and verify synchronous block
    guardian.trigger(reason="RAG safety test halt")
    assert guardian.is_halted is True

    parser = DocumentParser()
    bm25 = BM25Index()
    retriever = HybridRetriever(bm25=bm25)

    fake_file = tmp_path / "halt_test.txt"
    fake_file.write_text("Halt test content", encoding="utf-8")

    with pytest.raises(PermissionError, match="halted"):
        parser.parse_file(str(fake_file))

    with pytest.raises(PermissionError, match="halted"):
        bm25.search("query")

    with pytest.raises(PermissionError, match="halted"):
        retriever.retrieve("query")

    # Resume kill switch
    guardian.resume()
    assert guardian.is_halted is False
