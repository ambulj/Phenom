"""
Autonomous Research & Multi-App Desktop Tools Registration (Phase 47-03, EXEC-04, EXEC-05, EXEC-06).
Exposes deep academic crawling, Obsidian vault report synthesis, and synchronized multi-app coordination
to Phenom's Mission Orchestrator and ToolRegistry.
"""

import asyncio
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.research.deep_research_crawler import (
    deep_research_crawler,
    CrawlResult,
    ResearchPaper,
    WebSnippet
)
from services.backend.research.obsidian_synthesizer import obsidian_synthesizer
from services.backend.automation.multi_app_coordinator import (
    multi_app_coordinator,
    AppActionStep
)


# ============================================================================
# 1. deep_research_crawl (Tier 0 - Read Only)
# ============================================================================

class DeepResearchCrawlArgs(BaseModel):
    topic: str = Field(..., description="Research topic or scientific domain to explore")
    max_papers: Optional[int] = Field(default=5, description="Maximum number of arXiv papers to retrieve")
    web_urls: Optional[List[str]] = Field(default=None, description="Optional list of documentation URLs to scrape")

def deep_research_crawl_preview(args: Dict[str, Any]) -> str:
    topic = args.get("topic", "")
    return f"Perform multi-source deep research on '{topic}' across arXiv and web documentation."

@registry.register(
    name="deep_research_crawl",
    tier=0,
    description="Curls official arXiv export API and documentation pages for deep technical research without triggering bot blocks.",
    args_schema=DeepResearchCrawlArgs,
    preview_fn=deep_research_crawl_preview
)
def handle_deep_research_crawl(
    topic: str,
    max_papers: Optional[int] = 5,
    web_urls: Optional[List[str]] = None
) -> Dict[str, Any]:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # Running in existing event loop
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                asyncio.run,
                deep_research_crawler.research_topic(
                    topic=topic,
                    max_papers=max_papers or 5,
                    web_urls=web_urls
                )
            )
            result = future.result()
    else:
        result = loop.run_until_complete(
            deep_research_crawler.research_topic(
                topic=topic,
                max_papers=max_papers or 5,
                web_urls=web_urls
            )
        )

    return result.model_dump()


# ============================================================================
# 2. synthesize_obsidian_report (Tier 1 - Reversible Write)
# ============================================================================

class SynthesizeObsidianReportArgs(BaseModel):
    topic: str = Field(..., description="Topic of the synthesized report")
    papers: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="List of paper metadata dictionaries")
    web_snippets: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="List of web snippet dictionaries")
    summary: Optional[str] = Field(default=None, description="Optional custom summary")
    custom_filename: Optional[str] = Field(default=None, description="Optional custom markdown filename")

def synthesize_obsidian_report_preview(args: Dict[str, Any]) -> str:
    topic = args.get("topic", "")
    return f"Synthesize and write verified research briefing note for '{topic}' to Obsidian vault Research folder."

@registry.register(
    name="synthesize_obsidian_report",
    tier=1,
    description="Formats and writes a comprehensive research report into the Obsidian vault with verified citations and YAML metadata.",
    args_schema=SynthesizeObsidianReportArgs,
    preview_fn=synthesize_obsidian_report_preview,
    can_remember_per_folder=True
)
def handle_synthesize_obsidian_report(
    topic: str,
    papers: Optional[List[Dict[str, Any]]] = None,
    web_snippets: Optional[List[Dict[str, Any]]] = None,
    summary: Optional[str] = None,
    custom_filename: Optional[str] = None
) -> Dict[str, Any]:
    paper_objs = [ResearchPaper.model_validate(p) for p in (papers or [])]
    web_objs = [WebSnippet.model_validate(w) for w in (web_snippets or [])]

    crawl_data = CrawlResult(
        query=topic,
        sub_queries=[topic],
        papers=paper_objs,
        web_snippets=web_objs,
        synthesis_summary=summary or f"Research briefing compiled for {topic}."
    )

    res = obsidian_synthesizer.synthesize_and_save(crawl_data, custom_filename=custom_filename)
    return res.model_dump()


# ============================================================================
# 3. execute_multi_app_flow (Tier 1 - Sandboxed UI Coordination)
# ============================================================================

class ExecuteMultiAppFlowArgs(BaseModel):
    flow_id: str = Field(..., description="Identifier for this coordinated multi-app workflow")
    steps: List[Dict[str, Any]] = Field(..., description="Ordered list of AppActionStep parameter dictionaries")

def execute_multi_app_flow_preview(args: Dict[str, Any]) -> str:
    steps_len = len(args.get("steps", []))
    fid = args.get("flow_id", "")
    return f"Execute coordinated multi-app flow '{fid}' across {steps_len} browser and desktop steps."

@registry.register(
    name="execute_multi_app_flow",
    tier=1,
    description="Executes a coordinated sequence of browser and Windows desktop steps under Guardian kill switch protection.",
    args_schema=ExecuteMultiAppFlowArgs,
    preview_fn=execute_multi_app_flow_preview,
    can_remember_per_folder=True
)
def handle_execute_multi_app_flow(
    flow_id: str,
    steps: List[Dict[str, Any]]
) -> Dict[str, Any]:
    step_objs = [AppActionStep.model_validate(s) for s in steps]
    res = multi_app_coordinator.execute_flow(flow_id, step_objs)
    return res.model_dump()
