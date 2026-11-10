"""
Unit & Integration Test Suite for Obsidian Cross-Vault Bidirectional Graph Copilot & Dev Canvas.
Validates multi-vault indexing, cross-vault wikilink resolution, bidirectional backlink graph,
ADR/concept crystallization, Tool Registry safety, and Guardian SLA.

Part of Phenom 20.0 Sovereign Autonomous Developer (KNG-02.1, KNG-02.2, UI-02.1, SAF-01, SAF-02).
"""

import os
import time
from pathlib import Path
import pytest

from services.backend.obsidian.cross_vault_sync import CrossVaultManager, VaultNote, CrossVaultGraph
from services.backend.obsidian.concept_synthesizer import ConceptSynthesizer, ADRDraftRequest, ConceptDraftRequest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.obsidian_cross_vault_tools  # Register tools


# ==========================================
# 1. Multi-Vault Synchronizer Indexing Tests
# ==========================================

def test_multi_vault_synchronizer_indexing(tmp_path):
    mgr = CrossVaultManager(base_dir=str(tmp_path))
    dev_dir = tmp_path / "vault" / "developer"
    res_dir = tmp_path / "vault" / "research"
    daily_dir = tmp_path / "vault" / "daily"

    dev_dir.mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)
    daily_dir.mkdir(parents=True, exist_ok=True)

    # 1. Note in dev vault
    (dev_dir / "ADR-001_ast_indexer.md").write_text(
        "---\ntitle: 'ADR-001: AST Indexer'\nstatus: 'Accepted'\ntags:\n  - adr\n  - ast\n---\n\n"
        "# ADR-001\n\nImplements AST parsing with [[research:BM25_Lexical_Retriever]].\n",
        encoding="utf-8"
    )

    # 2. Note in research vault
    (res_dir / "BM25_Lexical_Retriever.md").write_text(
        "---\ntitle: 'BM25 Lexical Retriever'\ndomain: 'information-retrieval'\ntags:\n  - concept\n  - bm25\n---\n\n"
        "# BM25\n\nOkapi BM25 algorithm paired with [[dev:ADR-001_ast_indexer]] and [[daily:2026-11-11]].\n",
        encoding="utf-8"
    )

    # 3. Note in daily vault
    (daily_dir / "2026-11-11.md").write_text(
        "---\ntitle: '2026-11-11 Debrief'\ntags:\n  - daily\n---\n\n"
        "# Daily Debrief\n\nReviewed [[dev:ADR-001_ast_indexer]] performance.\n",
        encoding="utf-8"
    )

    graph: CrossVaultGraph = mgr.sync_all_vaults()
    assert graph.total_notes == 3
    assert graph.total_links >= 3

    # Check node details
    dev_note = mgr.get_note("dev:ADR-001_ast_indexer")
    assert dev_note is not None
    assert dev_note.title == "ADR-001_ast_indexer"
    assert "adr" in dev_note.tags
    assert "research:BM25_Lexical_Retriever" in dev_note.outgoing_links

    # Check bidirectional backlinks
    assert "research:BM25_Lexical_Retriever" in dev_note.backlinks
    assert "daily:2026-11-11" in dev_note.backlinks


# ==========================================
# 2. Concept Synthesizer ADR Generation
# ==========================================

def test_concept_synthesizer_create_adr(tmp_path):
    mgr = CrossVaultManager(base_dir=str(tmp_path))
    synthesizer = ConceptSynthesizer(manager=mgr)

    req = ADRDraftRequest(
        title="Offline Reciprocal Rank Fusion",
        context="Single channel vector search misses exact variable names.",
        decision="Combine Okapi BM25 with 384d vector embeddings via RRF (k=60).",
        consequences=[
            "Sub-5ms lexical retrieval latency",
            "Zero GPU VRAM consumption on CPU runtime"
        ],
        tags=["rag", "hybrid"],
        related_notes=["research:MiniLM_Embedding"]
    )

    note: VaultNote = synthesizer.create_adr(req)
    assert note.vault == "dev"
    assert note.node_id.startswith("dev:ADR-001")
    assert Path(note.absolute_path).exists()
    assert "adr" in note.tags
    assert "rag" in note.tags

    # Read content from disk to verify Markdown format
    content = Path(note.absolute_path).read_text(encoding="utf-8")
    assert "title: 'ADR-001: Offline Reciprocal Rank Fusion'" in content
    assert "## Context" in content
    assert "## Decision" in content
    assert "## Consequences & Trade-Offs" in content
    assert "[[research:MiniLM_Embedding]]" in content


# ==========================================
# 3. Concept Synthesizer Concept Note Generation
# ==========================================

def test_concept_synthesizer_create_concept_note(tmp_path):
    mgr = CrossVaultManager(base_dir=str(tmp_path))
    synthesizer = ConceptSynthesizer(manager=mgr)

    req = ConceptDraftRequest(
        title="Sentence Boundary Chunking",
        summary="Splits long prose on sentence boundaries with token overlap.",
        mechanisms="Uses regex boundary detection (?<=[.!?])\\s+(?=[A-Z0-9]) with configurable token overlap.",
        domain="nlp",
        tags=["chunking", "preprocessing"],
        related_notes=["dev:ADR-001_rag_engine"]
    )

    note: VaultNote = synthesizer.create_concept_note(req)
    assert note.vault == "research"
    assert note.title == "sentence_boundary_chunking"
    assert "concept" in note.tags
    assert "nlp" in note.tags

    content = Path(note.absolute_path).read_text(encoding="utf-8")
    assert "## Overview & Definition" in content
    assert "## Core Mechanisms & Architecture" in content
    assert "[[dev:ADR-001_rag_engine]]" in content


# ==========================================
# 4. Search and Visualization Data Payload
# ==========================================

def test_cross_vault_graph_search_and_visualization(tmp_path):
    mgr = CrossVaultManager(base_dir=str(tmp_path))
    dev_dir = tmp_path / "vault" / "developer"
    dev_dir.mkdir(parents=True, exist_ok=True)

    (dev_dir / "ADR-001_guardian.md").write_text(
        "---\ntitle: 'ADR-001'\ntags: ['guardian', 'safety']\n---\n# Note\n[[dev:ADR-002_hotkey]]",
        encoding="utf-8"
    )
    (dev_dir / "ADR-002_hotkey.md").write_text(
        "---\ntitle: 'ADR-002'\ntags: ['hotkey', 'input']\n---\n# Note\nContent",
        encoding="utf-8"
    )

    mgr.sync_all_vaults()

    # Search by tag
    safety_notes = mgr.search_graph(tag="safety")
    assert len(safety_notes) == 1
    assert safety_notes[0].title == "ADR-001_guardian"

    # Search by query
    hotkey_notes = mgr.search_graph(query="hotkey")
    assert len(hotkey_notes) >= 1

    # Visualization payload for frontend SVG
    viz = mgr.get_visualization_data(limit=10)
    assert "nodes" in viz
    assert "links" in viz
    assert len(viz["nodes"]) == 2
    assert len(viz["links"]) == 1
    assert viz["links"][0]["source"] == "dev:ADR-001_guardian"
    assert viz["links"][0]["target"] == "dev:ADR-002_hotkey"


# ==========================================
# 5. Tool Registry Safety Audit
# ==========================================

def test_obsidian_cross_vault_tool_registry_audit():
    expected_tools = [
        ("sync_cross_vaults", 0),
        ("generate_architectural_decision_record", 1),
        ("synthesize_concept_note", 1),
        ("query_cross_vault_graph", 0),
    ]

    for tool_name, expected_tier in expected_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered in ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch: expected {expected_tier}, got {tool_def.tier}"
        assert tool_def.preview_fn is not None
        assert callable(tool_def.preview_fn)

    # Preview checks
    adr_prev = registry.get("generate_architectural_decision_record").preview_fn({"title": "RRF Retrieval Engine"})
    assert "RRF Retrieval Engine" in adr_prev
    assert "Developer Obsidian Vault" in adr_prev

    concept_prev = registry.get("synthesize_concept_note").preview_fn({"title": "Inverted Index Saturation"})
    assert "Inverted Index Saturation" in concept_prev
    assert "Research Obsidian Vault" in concept_prev


# ==========================================
# 6. Universal Guardian Kill Switch SLA Benchmark
# ==========================================

def test_guardian_kill_switch_cross_vault_sla(tmp_path):
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

    print(f"\n[Guardian SLA Phase 4 Benchmark] Max: {max_latency:.4f}ms | Avg: {avg_latency:.4f}ms | SLA Target: < 25.0ms")
    assert max_latency < 25.0, f"Guardian SLA breached: max latency {max_latency:.4f}ms exceeds 25.0ms threshold"

    # Trigger halt and verify synchronous block
    guardian.trigger(reason="Cross-vault safety test halt")
    assert guardian.is_halted is True

    mgr = CrossVaultManager(base_dir=str(tmp_path))
    synthesizer = ConceptSynthesizer(manager=mgr)

    with pytest.raises(PermissionError, match="halted"):
        mgr.sync_all_vaults()

    with pytest.raises(PermissionError, match="halted"):
        mgr.search_graph("query")

    with pytest.raises(PermissionError, match="halted"):
        synthesizer.create_adr(ADRDraftRequest(title="Test", context="Ctx", decision="Dec"))

    with pytest.raises(PermissionError, match="halted"):
        synthesizer.create_concept_note(ConceptDraftRequest(title="Concept", summary="Sum", mechanisms="Mec"))

    # Resume kill switch
    guardian.resume()
    assert guardian.is_halted is False
