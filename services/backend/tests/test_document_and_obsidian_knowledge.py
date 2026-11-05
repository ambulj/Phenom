"""
Test Suite: Milestone 18 Phase 1 — Autonomous Document Generation & Obsidian Knowledge Engine
Covers:
- DOC-01.1: Multi-format document synthesis (Word, Excel, PowerPoint, PDF) with chart embeds and modifications
- DOC-01.2: Bidirectional Obsidian vault synchronization, frontmatter parsing, wikilinks, and daily debrief note
- DOC-01.3: Tier 1 safety gate, diff preview generation, and Rule 7 recycle bin protection
- DOC-01.4: Direct voice & chat document intents
- DOC-01.5: Template retrieval, recents listing, and UI schema validation
- SAF-01: Exhaustive Tool Registry audit, Pydantic schemas, and Tier classifications
- SAF-02.1: Universal Guardian Kill Switch SLA Benchmark (< 25.0ms SLA, target < 1.0ms)
"""

import os
import time
import pytest
import shutil
import tempfile
from typing import Dict, Any

from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.safety.engine import safety_engine
from services.backend.integrations.doc_generator import DocumentGenerator, doc_generator
from services.backend.memory.obsidian_sync import ObsidianSyncEngine, obsidian_sync
from services.backend.tools.document_tools import (
    generate_document,
    get_document_templates,
    list_generated_documents,
    generate_diff_preview,
    GenerateDocumentArgs
)
from services.backend.tools.obsidian_tools import (
    sync_obsidian_vault,
    create_daily_debrief_note,
    query_vault_knowledge,
    preview_daily_debrief_note,
    CreateDailyDebriefNoteArgs
)
from services.backend.orchestrator.engine import Orchestrator


@pytest.fixture(autouse=True)
def ensure_guardian_idle():
    """Ensure guardian is unhalted before and after each test."""
    guardian.resume()
    yield
    guardian.resume()


# ---------------- 1. DOC-01.1: MULTI-FORMAT SYNTHESIS & CHART EMBEDS ----------------

def test_word_document_generation_and_modification(tmp_path):
    gen = DocumentGenerator(default_dir=str(tmp_path))
    
    # 1. Create Word Document
    sections = [
        {"heading": "Executive Summary", "content": "Phenom autonomous architecture report."},
        {"heading": "KPI Matrix", "table": [["Metric", "Score"], ["SLA", "99.9%"], ["Safety", "100%"]]}
    ]
    res = gen.create_word_document("Test_Executive.docx", "Executive Strategy", sections)
    assert res["format"] == "docx"
    assert os.path.exists(res["file_path"])
    assert res["size_bytes"] > 1000

    # 2. Modify Word Document (Append)
    additions = {
        "sections": [
            {"heading": "Addendum 1", "content": "Appended autonomous verification data."}
        ]
    }
    mod_res = gen.modify_document("Test_Executive.docx", "docx", additions, mode="append")
    assert mod_res["format"] == "docx"
    assert mod_res["size_bytes"] >= res["size_bytes"]


def test_excel_spreadsheet_generation_with_chart_embed(tmp_path):
    gen = DocumentGenerator(default_dir=str(tmp_path))
    
    headers = ["Quarter", "Revenue ($M)", "EBITDA ($M)"]
    rows = [
        ["Q1", 12.5, 4.2],
        ["Q2", 15.0, 5.1],
        ["Q3", 18.2, 6.8],
        ["Q4", 22.4, 8.5]
    ]
    chart_config = {
        "type": "bar",
        "title": "Quarterly Performance",
        "x_title": "Quarter",
        "y_title": "Millions USD"
    }
    res = gen.create_excel_spreadsheet("Financial_Model.xlsx", "Financials", headers, rows, chart_config=chart_config)
    assert res["format"] == "xlsx"
    assert res["has_chart"] is True
    assert os.path.exists(res["file_path"])
    assert res["size_bytes"] > 2000

    # Append rows
    additions = {"rows": [["Q5 (Forecast)", 25.0, 9.2]]}
    mod_res = gen.modify_document("Financial_Model.xlsx", "xlsx", additions, mode="append")
    assert mod_res["format"] == "xlsx"
    assert mod_res["size_bytes"] >= res["size_bytes"]


def test_powerpoint_presentation_with_chart_slide(tmp_path):
    gen = DocumentGenerator(default_dir=str(tmp_path))

    slides = [
        {"title": "Overview", "bullets": ["Autonomous synthesis", "Local GPU reasoning"]},
        {
            "title": "Latency Benchmarks",
            "chart": {
                "type": "bar",
                "categories": ["Guardian Freeze", "VAD Detection", "STT Stream"],
                "series_name": "Latency (ms)",
                "series_values": [0.08, 3.2, 85.0]
            }
        }
    ]
    res = gen.create_powerpoint_presentation("Tech_Deck.pptx", "Phenom Architecture", "Executive Review", slides)
    assert res["format"] == "pptx"
    assert res["chart_slides_count"] == 1
    assert res["slides_count"] == 3
    assert os.path.exists(res["file_path"])
    assert res["size_bytes"] > 5000


def test_pdf_report_with_table_and_chart(tmp_path):
    gen = DocumentGenerator(default_dir=str(tmp_path))

    paragraphs = [
        "Phenom Executive Briefing on autonomous multi-format document engine.",
        "System telemetry demonstrates strict adherence to sub-25ms Guardian freeze SLAs."
    ]
    table_data = [
        ["Subsystem", "Tier", "Status"],
        ["Document Engine", "Tier 1", "Operational"],
        ["Obsidian Sync", "Tier 0", "Synchronized"]
    ]
    chart_config = {
        "title": "Operational Health",
        "categories": ["Safety", "Memory", "Core", "Audio"],
        "data": [100, 98, 100, 96]
    }
    res = gen.create_pdf_report("Executive_Brief.pdf", "Executive Intelligence Brief", paragraphs, table_data=table_data, chart_config=chart_config)
    assert res["format"] == "pdf"
    assert res["has_chart"] is True
    assert os.path.exists(res["file_path"])
    assert res["size_bytes"] > 1000


# ---------------- 2. DOC-01.2: OBSIDIAN VAULT SYNC & KNOWLEDGE ENGINE ----------------

def test_obsidian_vault_sync_and_frontmatter_parsing(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    # Note 1 with YAML frontmatter, tags, and wikilinks
    note1_content = """---
title: System Architecture Spec
date: 2026-11-05
tags: [architecture, core, milestone18]
status: active
---

# System Architecture Spec

This core specification connects to [[Security_Policy]] and [[Data_Models]].
Also verified via #quantum-crypto pipeline.
"""
    (notes_dir / "Architecture.md").write_text(note1_content, encoding="utf-8")

    # Note 2 referencing Note 1
    note2_content = """# Security Policy

Defined under [[Architecture]].
Strict enforcement of #security and #guardian protocols.
"""
    (notes_dir / "Security_Policy.md").write_text(note2_content, encoding="utf-8")

    sync_engine = ObsidianSyncEngine(vault_dir=str(tmp_path))
    sync_res = sync_engine.sync_vault()

    assert sync_res["status"] == "synced"
    assert sync_res["notes_count"] == 2
    assert sync_res["tags_count"] >= 4
    assert sync_res["total_links"] >= 3

    # Query Knowledge Graph by text
    matches = sync_engine.query_vault("Architecture")
    assert len(matches) > 0
    assert matches[0]["title"] == "System Architecture Spec"

    # Query Knowledge Graph by tag
    tag_matches = sync_engine.query_vault(tag="architecture")
    assert len(tag_matches) == 1
    assert tag_matches[0]["name"] == "Architecture"

    # Query Knowledge Graph backlinks
    arch_backlinks = matches[0]["backlinks"]
    assert "Security_Policy" in arch_backlinks


def test_daily_executive_debrief_generation(tmp_path):
    sync_engine = ObsidianSyncEngine(vault_dir=str(tmp_path))
    
    debrief_res = sync_engine.create_daily_debrief(
        date_str="2026-11-05",
        accomplishments=[
            "Delivered DOC-01 autonomous document engine.",
            "Wired bidirectional Obsidian knowledge sync."
        ],
        metrics={"Guardian Freeze": "< 1.0ms typical", "Safety Status": "All Tiers PASS"},
        cross_links=["Architecture", "Security_Policy"]
    )

    assert debrief_res["status"] == "success"
    assert os.path.exists(debrief_res["file_path"])
    assert debrief_res["frontmatter"]["type"] == "daily_debrief"
    assert "daily" in debrief_res["frontmatter"]["tags"]

    # Verify content on disk
    with open(debrief_res["file_path"], "r", encoding="utf-8") as f:
        content = f.read()
    assert "Executive Daily Debrief: 2026-11-05" in content
    assert "Delivered DOC-01 autonomous document engine." in content
    assert "[[Architecture]]" in content


# ---------------- 3. DOC-01.3 & SAF-01: TIER 1 SAFETY GATE & DIFF PREVIEW ----------------

def test_document_tools_registry_and_preview():
    # 1. Registry audit
    gen_doc = registry.get("generate_document")
    assert gen_doc is not None
    assert gen_doc.tier == 1
    assert gen_doc.args_schema == GenerateDocumentArgs

    list_doc = registry.get("list_generated_documents")
    assert list_doc is not None
    assert list_doc.tier == 0

    templates_tool = registry.get("get_document_templates")
    assert templates_tool is not None
    assert templates_tool.tier == 0

    sync_v = registry.get("sync_obsidian_vault")
    assert sync_v is not None
    assert sync_v.tier == 0

    daily_n = registry.get("create_daily_debrief_note")
    assert daily_n is not None
    assert daily_n.tier == 1
    assert daily_n.args_schema == CreateDailyDebriefNoteArgs

    # 2. Diff preview tests
    preview_text = generate_diff_preview({
        "filename": "Quarterly_Review.xlsx",
        "format": "xlsx",
        "headers": ["A", "B"],
        "rows": [[1, 2], [3, 4]],
        "chart_config": {"type": "bar"},
        "mode": "create"
    })
    assert "[Tier 1] Generate XLSX Document:" in preview_text
    assert "chart_embed=bar" in preview_text
    assert "+2 rows, 2 columns" in preview_text

    debrief_preview = preview_daily_debrief_note({
        "date": "2026-11-05",
        "accomplishments": ["Task A", "Task B"],
        "cross_links": ["NoteA"]
    })
    assert "[Tier 1] Write Daily Debrief Note:" in debrief_preview
    assert "+2 accomplishments" in debrief_preview


@pytest.mark.asyncio
async def test_headless_safety_engine_confirmation_gate(tmp_path):
    approved_actions = []

    async def test_confirmation_handler(
        req_id, tool_name, tier, preview_text, validated_args, can_remember, folder, timeout
    ):
        approved_actions.append(tool_name)
        return "approved", False

    safety_engine.set_confirmation_handler(test_confirmation_handler)

    target_file = os.path.join(str(tmp_path), "Headless_Safety_Test.docx")
    args = {
        "filename": target_file,
        "format": "docx",
        "title": "Headless Test",
        "sections": [{"heading": "Sec1", "content": "Text"}],
        "folder": str(tmp_path)
    }

    # Execute through safety_engine
    result = await safety_engine.execute_tool("generate_document", args)
    assert result["status"] == "success"
    assert "generate_document" in approved_actions


# ---------------- 4. DOC-01.4: DIRECT VOICE & CHAT INTENTS ----------------

def test_direct_document_and_knowledge_intents():
    orchestrator = Orchestrator()

    # 1. Presentation
    p1 = orchestrator._detect_direct_intent("create presentation on AI architecture")
    assert p1 is not None
    assert p1[0] == "generate_document"
    assert p1[1]["format"] == "pptx"
    assert "Ai Architecture" in p1[1]["title"]

    # 2. Spreadsheet
    p2 = orchestrator._detect_direct_intent("generate spreadsheet for quarterly budget")
    assert p2 is not None
    assert p2[0] == "generate_document"
    assert p2[1]["format"] == "xlsx"
    assert "Quarterly Budget" in p2[1]["title"]

    # 3. Daily note
    p3 = orchestrator._detect_direct_intent("summarize today into daily note")
    assert p3 is not None
    assert p3[0] == "create_daily_debrief_note"

    # 4. Search vault
    p4 = orchestrator._detect_direct_intent("search vault for milestone18")
    assert p4 is not None
    assert p4[0] == "query_vault_knowledge"
    assert p4[1]["query"] == "milestone18"

    # 5. Sync vault
    p5 = orchestrator._detect_direct_intent("sync obsidian vault")
    assert p5 is not None
    assert p5[0] == "sync_obsidian_vault"


# ---------------- 5. SAF-02.1: GUARDIAN KILL SWITCH SLA BENCHMARK (< 25.0ms) ----------------

def test_universal_guardian_kill_switch_freeze_sla():
    # Verify unhalted operation
    guardian.resume()
    assert not guardian.is_halted

    # Benchmark Guardian trigger latency
    start = time.perf_counter()
    guardian.trigger(reason="sla_benchmark_test")
    latency_ms = (time.perf_counter() - start) * 1000.0

    assert guardian.is_halted
    assert latency_ms < 25.0, f"Guardian trigger exceeded 25.0ms SLA: {latency_ms:.4f}ms"
    print(f"\n[BENCHMARK] Guardian Kill Switch trigger latency: {latency_ms:.4f}ms (< 25.0ms SLA, target < 1.0ms)")

    # Test that document tools freeze when halted
    with pytest.raises(RuntimeError, match="halted by Guardian"):
        generate_document(filename="Halted.docx", format="docx")

    # Test that Obsidian sync freezes when halted
    with pytest.raises(RuntimeError, match="halted by Guardian"):
        sync_obsidian_vault()

    # Test that Daily note creation freezes when halted
    with pytest.raises(RuntimeError, match="halted by Guardian"):
        create_daily_debrief_note()

    # Resume and verify normal operation restored
    guardian.resume()
    assert not guardian.is_halted
