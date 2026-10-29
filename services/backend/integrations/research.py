"""
Phenom Academic & Research Sources Integration (Phase 5)
Covers:
- arXiv API (official export API)
- Semantic Scholar API (paper search & abstracts)
- Crossref API (citations and DOI lookup)
- Google Scholar (web scraping fallback, explicitly marked as less reliable)
Never fabricates citations or fake papers on network failure.
"""

import httpx
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import urllib.parse

logger = logging.getLogger("phenom.research")

class ResearchEngine:
    def __init__(self):
        self._headers = {"User-Agent": "PhenomAssistant/1.0 (academic research assistant; mailto:user@phenom.local)"}

    async def search_arxiv(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Searches arXiv official API."""
        encoded_q = urllib.parse.quote(query)
        url = f"https://export.arxiv.org/api/query?search_query=all:{encoded_q}&start=0&max_results={max_results}"
        papers = []
        try:
            async with httpx.AsyncClient(timeout=6.0, headers=self._headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    for entry in root.findall("atom:entry", ns):
                        title = entry.find("atom:title", ns)
                        summary = entry.find("atom:summary", ns)
                        id_elem = entry.find("atom:id", ns)
                        published = entry.find("atom:published", ns)
                        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns) if a.find("atom:name", ns) is not None]
                        
                        papers.append({
                            "title": title.text.strip().replace("\n", " ") if title is not None and title.text else "Untitled",
                            "authors": authors,
                            "abstract": summary.text.strip().replace("\n", " ") if summary is not None and summary.text else "",
                            "link": id_elem.text.strip() if id_elem is not None and id_elem.text else "",
                            "published": published.text[:10] if published is not None and published.text else "",
                            "source": "arxiv",
                            "reliability": "high"
                        })
        except Exception as e:
            logger.warning(f"arXiv search error: {e}")
        return papers

    async def search_semantic_scholar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Searches Semantic Scholar API."""
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote(query)}&limit={limit}&fields=title,authors,year,abstract,citationCount,url,externalIds"
        papers = []
        try:
            async with httpx.AsyncClient(timeout=6.0, headers=self._headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("data", []):
                        authors = [a.get("name", "") for a in item.get("authors", [])]
                        papers.append({
                            "title": item.get("title", ""),
                            "authors": authors,
                            "year": item.get("year"),
                            "abstract": item.get("abstract", "") or "",
                            "citations": item.get("citationCount", 0),
                            "link": item.get("url", ""),
                            "doi": item.get("externalIds", {}).get("DOI", ""),
                            "source": "semantic_scholar",
                            "reliability": "high"
                        })
        except Exception as e:
            logger.warning(f"Semantic Scholar error: {e}")
        return papers

    async def lookup_doi_crossref(self, doi_or_query: str) -> Dict[str, Any]:
        """Looks up citations and publication metadata from Crossref."""
        is_doi = "10." in doi_or_query
        if is_doi:
            clean_doi = doi_or_query.strip().split("doi.org/")[-1]
            url = f"https://api.crossref.org/works/{urllib.parse.quote(clean_doi)}"
        else:
            url = f"https://api.crossref.org/works?query={urllib.parse.quote(doi_or_query)}&rows=1"

        try:
            async with httpx.AsyncClient(timeout=6.0, headers=self._headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    message = resp.json().get("message", {})
                    item = message if is_doi else (message.get("items", [{}])[0] if message.get("items") else {})
                    authors = []
                    for a in item.get("author", []):
                        name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                        if name:
                            authors.append(name)

                    return {
                        "ok": True,
                        "title": (item.get("title", [""])[0] if item.get("title") else "Unknown"),
                        "authors": authors,
                        "doi": item.get("DOI", ""),
                        "publisher": item.get("publisher", ""),
                        "citations_count": item.get("is-referenced-by-count", 0),
                        "url": item.get("URL", ""),
                        "source": "crossref",
                        "reliability": "official",
                        "stale": False
                    }
        except Exception as e:
            logger.warning(f"Crossref lookup error: {e}")

        # On network failure or error: return typed error record, never fabricate citation
        return {
            "ok": False,
            "error": "network_unavailable",
            "provider": "crossref",
            "doi": doi_or_query,
            "title": None,
            "authors": [],
            "citations_count": None,
            "source": "unreachable",
            "stale": True
        }

    async def search_google_scholar_scraped(self, query: str) -> List[Dict[str, Any]]:
        """
        Scrapes Google Scholar.
        Explicitly marked with reliability="less_reliable" and source="scraped".
        Returns empty list on failure, never fabricates papers.
        """
        url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        papers = []
        try:
            async with httpx.AsyncClient(timeout=6.0, headers=headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for el in soup.select(".gs_r.gs_or.gs_scl")[:5]:
                        h3 = el.select_one(".gs_rt")
                        title = h3.text if h3 else "Untitled"
                        link = h3.find("a")["href"] if h3 and h3.find("a") else ""
                        snippet = el.select_one(".gs_rs")
                        desc = snippet.text if snippet else ""
                        papers.append({
                            "title": title,
                            "link": link,
                            "abstract": desc,
                            "source": "scraped",
                            "reliability": "less_reliable"
                        })
        except Exception as e:
            logger.warning(f"Google scholar scraping error: {e}")

        # Returns empty list on failure: no fake paper entries
        return papers

    async def unified_search(self, query: str, limit_per_source: int = 3) -> Dict[str, Any]:
        """Performs search across arXiv, Semantic Scholar, and Google Scholar fallback."""
        arxiv_res = await self.search_arxiv(query, max_results=limit_per_source)
        semantic_res = await self.search_semantic_scholar(query, limit=limit_per_source)
        
        all_results = arxiv_res + semantic_res
        if not all_results:
            # Fallback to Google Scholar scraping
            scraped_res = await self.search_google_scholar_scraped(query)
            all_results.extend(scraped_res)

        now_str = datetime.now(timezone.utc).isoformat()
        if not all_results:
            return {
                "ok": False,
                "error": "no_results_or_network_unavailable",
                "query": query,
                "total_found": 0,
                "results": [],
                "stale": True,
                "timestamp": now_str
            }

        return {
            "ok": True,
            "query": query,
            "total_found": len(all_results),
            "results": all_results,
            "stale": False,
            "timestamp": now_str
        }

# Global research engine
research_engine = ResearchEngine()
