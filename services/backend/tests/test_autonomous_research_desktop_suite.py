"""
Comprehensive Unit Test Battery for Phase 47-03:
Deep Research Crawler, Obsidian Vault Synthesizer & Multi-App Desktop Coordinator.
Verifies requirements: EXEC-04, EXEC-05, EXEC-06.
"""

import os
import tempfile
import time
import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from services.backend.research.deep_research_crawler import (
    DeepResearchCrawler,
    CrawlResult,
    ResearchPaper,
    WebSnippet,
    deep_research_crawler
)
from services.backend.research.obsidian_synthesizer import (
    ObsidianSynthesizer,
    SynthesizedReportResult,
    obsidian_synthesizer
)
from services.backend.automation.multi_app_coordinator import (
    MultiAppCoordinator,
    AppActionStep,
    MultiAppFlowReport,
    multi_app_coordinator
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.autonomous_research_desktop_tools as tools


@pytest.fixture(autouse=True)
def reset_guardian():
    """Ensure Guardian kill switch is clear before and after each test."""
    guardian.resume()
    yield
    guardian.resume()


# ============================================================================
# 1. Deep Research Crawler & Anti-CAPTCHA Defense (EXEC-04)
# ============================================================================

def test_query_decomposition():
    """Verifies that research topics decompose into orthogonal subqueries."""
    crawler = DeepResearchCrawler()
    subs = crawler.decompose_query("Quantum Error Correction")
    assert len(subs) >= 2
    assert "Quantum Error Correction" in subs[0]
    assert any("benchmarks" in s or "state of the art" in s for s in subs)


def test_anti_captcha_defense():
    """
    Verifies that anti-bot challenges and CAPTCHA gates are strictly detected
    and flagged as blocked without attempting bypass.
    """
    crawler = DeepResearchCrawler()

    # Cloudflare Turnstile Challenge HTML
    challenge_html = """
    <html>
      <head><title>Just a moment...</title></head>
      <body>
        <div id="cf-turnstile"></div>
        <p>Please verify you are human to continue.</p>
      </body>
    </html>
    """
    assert crawler.detect_captcha(challenge_html) is True

    # Clean HTML
    clean_html = "<html><head><title>Vector DBs</title></head><body><h1>HNSW Index</h1></body></html>"
    assert crawler.detect_captcha(clean_html) is False


@pytest.mark.asyncio
async def test_arxiv_crawl_parsing():
    """Verifies parsing of official arXiv Atom XML export responses."""
    crawler = DeepResearchCrawler()

    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2401.12345v1</id>
        <title>Sovereign Agentic Workflows on Edge Hardware</title>
        <summary>We introduce a decentralized framework for local LLM orchestration.</summary>
        <published>2026-01-15T12:00:00Z</published>
        <author><name>Dr. Alex Turing</name></author>
        <author><name>Ada Lovelace</name></author>
        <arxiv:doi>10.1000/182</arxiv:doi>
      </entry>
    </feed>
    """

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_xml

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        papers = await crawler.crawl_arxiv("sovereign agents", max_results=2)
        assert len(papers) == 1
        paper = papers[0]
        assert paper.title == "Sovereign Agentic Workflows on Edge Hardware"
        assert "Dr. Alex Turing" in paper.authors
        assert paper.url == "http://arxiv.org/abs/2401.12345v1"
        assert paper.published_date == "2026-01-15"
        assert paper.doi == "10.1000/182"


# ============================================================================
# 2. Obsidian Vault Report Synthesis (EXEC-05)
# ============================================================================

def test_obsidian_markdown_synthesis():
    """
    Verifies that research results compile into Obsidian-compliant Markdown
    with YAML frontmatter, executive summary, comparative table, and citations.
    """
    with tempfile.TemporaryDirectory() as temp_vault:
        synthesizer = ObsidianSynthesizer(vault_root=temp_vault)

        paper = ResearchPaper(
            title="Local Speculative Decoding with 8B Models",
            authors=["Linus Torvalds", "Claude Shannon"],
            abstract="Speeding up token generation by 2.4x via speculative draft tokens.",
            url="https://arxiv.org/abs/2602.99999",
            published_date="2026-02-20",
            source="arxiv"
        )

        web = WebSnippet(
            title="vLLM Speculative Decoding Documentation",
            url="https://docs.vllm.ai/en/latest/models/speculative_decoding.html",
            domain="docs.vllm.ai",
            content="Speculative decoding uses a draft model to propose candidates."
        )

        crawl_result = CrawlResult(
            query="Speculative Decoding 8B",
            sub_queries=["Speculative Decoding 8B", "benchmarks"],
            papers=[paper],
            web_snippets=[web],
            synthesis_summary="Speculative decoding achieves 2.4x latency speedups on 8GB VRAM GPUs."
        )

        res = synthesizer.synthesize_and_save(crawl_result, custom_filename="speculative_decoding.md")

        assert os.path.exists(res.vault_file_path)
        assert res.sources_count == 2

        with open(res.vault_file_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # Verify YAML frontmatter
        assert md_content.startswith("---\n")
        assert 'title: "Deep Research: Speculative Decoding 8B"' in md_content
        assert "sources_count: 2" in md_content
        assert "academic_papers: 1" in md_content
        assert "web_sources: 1" in md_content

        # Verify sections
        assert "## 1. Executive Summary" in md_content
        assert "## 2. Academic Discoveries & Methodologies" in md_content
        assert "## 4. Comparative Synthesis Matrix" in md_content
        assert "## 5. Verified Citations & References" in md_content

        # Verify non-hallucinated citations
        assert "Local Speculative Decoding with 8B Models" in md_content
        assert "https://arxiv.org/abs/2602.99999" in md_content


# ============================================================================
# 3. Multi-App Desktop Workflow Coordinator (EXEC-06)
# ============================================================================

def test_multi_app_coordinator_flow_execution():
    """
    Verifies that multi-app coordinator executes multi-step sequences across
    browser, desktop, and CLI with active window tracking.
    """
    coordinator = MultiAppCoordinator()

    steps = [
        AppActionStep(
            step_id="step_1_browser_nav",
            app_type="browser",
            action="navigate",
            target="https://arxiv.org"
        ),
        AppActionStep(
            step_id="step_2_browser_read",
            app_type="browser",
            action="read_text",
            target="#main-title"
        ),
        AppActionStep(
            step_id="step_3_desktop_focus",
            app_type="desktop",
            action="focus_window",
            target="Obsidian"
        ),
        AppActionStep(
            step_id="step_4_desktop_type",
            app_type="desktop",
            action="type",
            value="## Notes from Research"
        ),
        AppActionStep(
            step_id="step_5_cli_echo",
            app_type="cli",
            action="run_cmd",
            value="echo multi_app_flow_verified"
        )
    ]

    report = coordinator.execute_flow(flow_id="flow_test_001", steps=steps)

    assert report.success is True
    assert report.total_steps == 5
    assert report.completed_steps == 5
    assert len(report.step_results) == 5
    assert report.active_window == "Obsidian"


def test_multi_app_coordinator_guardian_kill_switch_halt():
    """
    Verifies that when Guardian kill switch is active,
    multi-app coordinator immediately halts execution with status='halted' (< 25ms SLA).
    """
    guardian.trigger()
    coordinator = MultiAppCoordinator()

    steps = [
        AppActionStep(
            step_id="step_halt_check",
            app_type="browser",
            action="navigate",
            target="https://example.com"
        )
    ]

    t_start = time.perf_counter()
    report = coordinator.execute_flow(flow_id="flow_halt_test", steps=steps)
    t_ms = (time.perf_counter() - t_start) * 1000.0

    assert report.success is False
    assert report.completed_steps == 0
    assert report.step_results[0].status == "halted"
    assert "Guardian kill switch is active" in report.step_results[0].error
    assert t_ms < 25.0, f"Halt check exceeded 25ms SLA: {t_ms:.2f}ms"


# ============================================================================
# 4. Autonomous Research & Desktop Tool Registry Declarations (EXEC-04, 05, 06)
# ============================================================================

def test_autonomous_research_desktop_tools_registry():
    """Verifies that research and multi-app tools are properly registered with strict safety tiers."""
    tool_names = [
        "deep_research_crawl",
        "synthesize_obsidian_report",
        "execute_multi_app_flow"
    ]

    for name in tool_names:
        tool_def = registry.get(name)
        assert tool_def is not None, f"Tool '{name}' must be registered"
        assert callable(tool_def.preview_fn)
        assert tool_def.args_schema is not None

    # Tier invariants
    assert registry.get("deep_research_crawl").tier == 0  # Read-only
    assert registry.get("synthesize_obsidian_report").tier == 1  # Reversible file write
    assert registry.get("execute_multi_app_flow").tier == 1  # Sandboxed UI coordination

    # Test tool handler invocation
    flow_steps = [
        {"step_id": "s1", "app_type": "cli", "action": "run_cmd", "value": "echo tool_handler_test"}
    ]
    res = tools.handle_execute_multi_app_flow(flow_id="test_tool", steps=flow_steps)
    assert res["success"] is True
    assert res["completed_steps"] == 1
