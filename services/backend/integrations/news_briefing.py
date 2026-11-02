"""
Phenom Tech News Briefing (Phase 5)
Aggregates and formats tech briefings from Hacker News, TechCrunch, and The Verge RSS feeds.
Never fabricates articles on network failure.
"""

import feedparser
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone

FEED_SOURCES = {
    "Hacker News": "https://news.ycombinator.com/rss",
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://theverge.com/rss/index.xml",
    "BBC World News": "https://feeds.bbci.co.uk/news/world/rss.xml"
}

class TechNewsBriefing:
    def __init__(self):
        pass

    def _fetch_feed_sync(self, source_name: str, url: str, limit: int = 3) -> List[Dict[str, Any]]:
        items = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                items.append({
                    "source": source_name,
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", entry.get("updated", "")),
                    "summary": entry.get("summary", "")[:200].replace("\n", " ") + "..." if entry.get("summary") else ""
                })
        except Exception as e:
            pass
        return items

    async def get_briefing(self, items_per_source: int = 3) -> Dict[str, Any]:
        """Fetches top items across all three sources asynchronously."""
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(None, self._fetch_feed_sync, name, url, items_per_source)
            for name, url in FEED_SOURCES.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles: List[Dict[str, Any]] = []
        for res in results:
            if isinstance(res, list):
                all_articles.extend(res)

        # On network failure or offline: return typed error record with 0 articles, never fabricate
        if not all_articles:
            return {
                "ok": False,
                "error": "network_unavailable",
                "provider": "rss_feeds",
                "articles_count": 0,
                "articles": [],
                "briefing_markdown": "Tech news briefing unavailable: network offline.",
                "stale": True,
                "fetched_at": None,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        # Formatted briefing text
        lines = ["**Phenom Tech Briefing:**\n"]
        for art in all_articles:
            lines.append(f"• **[{art['source']}]** [{art['title']}]({art['link']})")
            if art['summary']:
                lines.append(f"  _{art['summary']}_")

        return {
            "ok": True,
            "articles_count": len(all_articles),
            "articles": all_articles,
            "briefing_markdown": "\n".join(lines),
            "stale": False,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    async def get_morning_briefing(self) -> Dict[str, Any]:
        """
        Produces full morning briefing:
        1. Tech news briefing.
        2. Unread email summary if Gmail is authenticated.
        If Gmail is not authenticated, appends:
        'Email summary skipped: Gmail integration is not connected or authenticated.'
        """
        from services.backend.integrations.google_workspace import google_workspace

        news_res = await self.get_briefing()
        briefing_parts = []
        if news_res.get("ok", True) and news_res.get("briefing_markdown"):
            briefing_parts.append(news_res["briefing_markdown"])
        else:
            briefing_parts.append("Tech news briefing unavailable: network offline.")

        briefing_parts.append("\n**Email Updates:**")
        if not google_workspace.is_gmail_configured():
            briefing_parts.append("Email summary skipped: Gmail integration is not connected or authenticated.")
        else:
            try:
                unread = google_workspace.search_emails(query="UNSEEN", max_results=5)
                if unread:
                    briefing_parts.append(f"You have {len(unread)} recent unread email(s):")
                    for m in unread:
                        briefing_parts.append(f"• From: {m.get('from', 'Unknown')} - {m.get('subject', 'No Subject')}")
                else:
                    briefing_parts.append("Inbox clean: no unread emails.")
            except Exception as e:
                briefing_parts.append(f"Could not retrieve unread emails: {e}")

        full_markdown = "\n".join(briefing_parts)
        return {
            "ok": True,
            "briefing_markdown": full_markdown,
            "news": news_res,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

# Global tech news briefing instance
tech_news = TechNewsBriefing()
