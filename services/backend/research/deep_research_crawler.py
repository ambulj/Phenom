"""
Deep Research Crawler with Academic arXiv Integration & Anti-CAPTCHA Defense (Phase 47-03, EXEC-04).
Coordinates multi-query searches across arXiv academic exports and safe web scraping.
Invariants:
1. Never attempts to solve, bypass, or click through CAPTCHAs or bot challenges (Rule of Engagement).
2. Never fabricates citations, DOIs, or author lists on network failure (Rule 5).
3. Graceful degradation: surfaces clean block warnings if anti-bot walls are encountered.
"""

import re
import urllib.parse
import xml.etree.ElementTree as ET
import html
from typing import List, Dict, Any, Optional
import httpx
from pydantic import BaseModel, Field


class ResearchPaper(BaseModel):
    """Structured representation of an academic research paper."""
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(default_factory=list, description="Author list")
    abstract: str = Field(default="", description="Paper abstract / executive summary")
    url: str = Field(default="", description="Official paper link or DOI URL")
    published_date: str = Field(default="", description="Publication date string (YYYY-MM-DD)")
    source: str = Field(default="arxiv", description="Primary repository source")
    doi: Optional[str] = Field(default=None, description="Document Object Identifier if available")


class WebSnippet(BaseModel):
    """Extracted text snippet from an external web documentation source."""
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Source URL")
    domain: str = Field(..., description="Target domain")
    content: str = Field(..., description="Sanitized, tag-stripped text summary")


class CrawlResult(BaseModel):
    """Aggregate result from a multi-source deep research crawl."""
    query: str = Field(..., description="Original user research prompt")
    sub_queries: List[str] = Field(default_factory=list, description="Decomposed research subqueries")
    papers: List[ResearchPaper] = Field(default_factory=list, description="Academic papers retrieved")
    web_snippets: List[WebSnippet] = Field(default_factory=list, description="Web articles or documentation retrieved")
    blocked_targets: List[str] = Field(default_factory=list, description="URLs blocked by bot challenges / CAPTCHAs")
    synthesis_summary: str = Field(default="", description="Brief synthesis of key findings")


class DeepResearchCrawler:
    """Orchestrates multi-source academic and web research without triggering bot defenses."""

    USER_AGENT = "PhenomAssistant/1.0 (academic research & desktop assistant; mailto:user@phenom.local)"

    CAPTCHA_INDICATORS = [
        "cf-turnstile",
        "hcaptcha",
        "g-recaptcha",
        "recaptcha",
        "verify you are human",
        "checking your browser",
        "just a moment...",
        "access denied | www.cloudflare.com",
        "ddos protection by cloudflare",
        "perimeterx",
        "captcha",
    ]

    def __init__(self, http_timeout: float = 8.0):
        self.http_timeout = http_timeout
        self.headers = {"User-Agent": self.USER_AGENT}

    @staticmethod
    def decompose_query(topic: str) -> List[str]:
        """Decomposes a broad research topic into focused technical subqueries."""
        clean = topic.strip()
        if not clean:
            return []

        # Generate orthogonal research facets
        sub_queries = [
            clean,
            f"{clean} state of the art architecture benchmarks",
            f"{clean} practical implementation and limitations"
        ]
        return sub_queries

    def detect_captcha(self, html_content: str) -> bool:
        """
        Inspects raw HTML response to detect CAPTCHA gates or anti-bot challenge pages.
        Safety Invariant: Phenom NEVER attempts to solve or bypass CAPTCHAs.
        """
        lower = html_content.lower()
        return any(indicator in lower for indicator in self.CAPTCHA_INDICATORS)

    async def crawl_arxiv(self, query: str, max_results: int = 5) -> List[ResearchPaper]:
        """
        Queries official arXiv export API (export.arxiv.org) and parses Atom XML entries.
        Never fabricates papers or citations.
        """
        encoded_q = urllib.parse.quote(query)
        url = f"https://export.arxiv.org/api/query?search_query=all:{encoded_q}&start=0&max_results={max_results}"
        papers: List[ResearchPaper] = []

        try:
            async with httpx.AsyncClient(timeout=self.http_timeout, headers=self.headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

                    for entry in root.findall("atom:entry", ns):
                        title_el = entry.find("atom:title", ns)
                        summary_el = entry.find("atom:summary", ns)
                        id_el = entry.find("atom:id", ns)
                        pub_el = entry.find("atom:published", ns)
                        doi_el = entry.find("arxiv:doi", ns)

                        authors = [
                            a.find("atom:name", ns).text
                            for a in entry.findall("atom:author", ns)
                            if a.find("atom:name", ns) is not None and a.find("atom:name", ns).text
                        ]

                        title_text = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else "Untitled"
                        summary_text = summary_el.text.strip().replace("\n", " ") if summary_el is not None and summary_el.text else ""
                        link_text = id_el.text.strip() if id_el is not None and id_el.text else ""
                        pub_text = pub_el.text[:10] if pub_el is not None and pub_el.text else ""
                        doi_text = doi_el.text.strip() if doi_el is not None and doi_el.text else None

                        # Clean arXiv abstract
                        summary_text = re.sub(r"\s+", " ", summary_text)

                        papers.append(ResearchPaper(
                            title=title_text,
                            authors=authors,
                            abstract=summary_text,
                            url=link_text,
                            published_date=pub_text,
                            source="arxiv",
                            doi=doi_text
                        ))
        except Exception:
            # Safe network failure handling: return empty list, never fabricate
            return []

        return papers

    def clean_html_text(self, raw_html: str, max_chars: int = 1500) -> str:
        """Strips scripts, styles, and tags, returning clean readable prose."""
        # Strip script and style blocks
        no_scripts = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
        # Strip tags
        no_tags = re.sub(r"<[^>]+>", " ", no_scripts)
        # Unescape HTML entities
        unescaped = html.unescape(no_tags)
        # Normalize whitespace
        clean = re.sub(r"\s+", " ", unescaped).strip()
        return clean[:max_chars]

    async def scrape_web_page(self, url: str) -> (Optional[WebSnippet], bool):
        """
        Safely fetches web page.
        Returns (WebSnippet or None, is_blocked_by_captcha: bool).
        """
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc or "web"

        try:
            async with httpx.AsyncClient(timeout=self.http_timeout, headers=self.headers, follow_redirects=True) as client:
                resp = await client.get(url)
                body = resp.text

                # Check anti-bot challenges
                if self.detect_captcha(body) or resp.status_code in (403, 429):
                    return None, True

                if resp.status_code == 200:
                    # Extract page title
                    title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
                    page_title = title_match.group(1).strip() if title_match else domain
                    page_title = html.unescape(page_title)

                    cleaned_content = self.clean_html_text(body)
                    if cleaned_content:
                        return WebSnippet(
                            title=page_title,
                            url=url,
                            domain=domain,
                            content=cleaned_content
                        ), False

        except Exception:
            return None, False

        return None, False

    async def research_topic(
        self,
        topic: str,
        max_papers: int = 5,
        web_urls: Optional[List[str]] = None
    ) -> CrawlResult:
        """Executes full deep research workflow across academic and web sources."""
        sub_queries = self.decompose_query(topic)
        all_papers: List[ResearchPaper] = []
        web_snippets: List[WebSnippet] = []
        blocked_targets: List[str] = []

        # 1. Academic crawl
        seen_titles = set()
        for q in sub_queries[:2]:
            papers = await self.crawl_arxiv(q, max_results=max_papers)
            for p in papers:
                if p.title.lower() not in seen_titles:
                    seen_titles.add(p.title.lower())
                    all_papers.append(p)
                    if len(all_papers) >= max_papers:
                        break
            if len(all_papers) >= max_papers:
                break

        # 2. Web crawl if URLs provided
        if web_urls:
            for url in web_urls:
                snippet, is_blocked = await self.scrape_web_page(url)
                if is_blocked:
                    blocked_targets.append(url)
                elif snippet:
                    web_snippets.append(snippet)

        # 3. Formulate synthesis summary
        paper_count = len(all_papers)
        web_count = len(web_snippets)
        summary = (
            f"Retrieved {paper_count} academic publications from arXiv and {web_count} web documentation sources "
            f"for research topic: '{topic}'."
        )

        return CrawlResult(
            query=topic,
            sub_queries=sub_queries,
            papers=all_papers,
            web_snippets=web_snippets,
            blocked_targets=blocked_targets,
            synthesis_summary=summary
        )


# Global singleton instance
deep_research_crawler = DeepResearchCrawler()
