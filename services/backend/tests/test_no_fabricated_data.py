"""
Tests proving:
1. All integrations (finance, live_data, news_briefing, research) return typed error records with ok=False, stale=True, and None for values on network failure.
2. No fabricated numbers exist in production code (grep assertion for 65000.0, 185.50, 142.85, 'Partly Cloudy', 'MF-SCRAPED-001').
3. Stale or failed quotes NEVER trigger watchlist alerts.
4. Morning briefing handles unauthenticated Gmail gracefully with exact message.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from services.backend.integrations.finance import FinancialEngine
from services.backend.integrations.live_data import LiveDataPipeline
from services.backend.integrations.news_briefing import TechNewsBriefing
from services.backend.integrations.research import ResearchEngine
from services.backend.memory.db import EncryptedDatabaseManager

@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_no_fab.db")
    return EncryptedDatabaseManager(db_path=db_file, encryption_key="0123456789abcdef0123456789abcdef")

def test_codebase_contains_no_fabricated_constants():
    """Grep-level verification that forbidden fabricated constants were completely removed from integrations."""
    integrations_dir = os.path.join(os.path.dirname(__file__), "..", "integrations")
    forbidden = [
        "65000.0",
        "185.50",
        "142.85",
        "Partly Cloudy",
        "MF-SCRAPED-001",
        "msg_001",
        "event_sample_1"
    ]
    for root, _, files in os.walk(integrations_dir):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as fh:
                    content = fh.read()
                    for term in forbidden:
                        assert term not in content, f"Forbidden fabricated term '{term}' found in {f}!"

@pytest.mark.asyncio
async def test_finance_returns_typed_error_without_fabrication():
    """Verifies crypto and stock quotes return typed error records with None on failure."""
    engine = FinancialEngine()
    # Mock network failure
    with patch("httpx.AsyncClient.get", side_effect=Exception("Network unreachable")):
        # Crypto
        res_crypto = await engine.get_market_quote("BTC", "crypto")
        assert res_crypto["ok"] is False
        assert res_crypto["stale"] is True
        assert res_crypto["price"] is None
        assert res_crypto["source"] == "unreachable"

        # Stock
        res_stock = await engine.get_market_quote("AAPL", "stock")
        assert res_stock["ok"] is False
        assert res_stock["stale"] is True
        assert res_stock["price"] is None
        assert res_stock["source"] == "unreachable"

@pytest.mark.asyncio
async def test_stale_or_failed_quote_never_triggers_alert(temp_db):
    """Verifies that if a quote is stale or unavailable, price alerts do not fire."""
    engine = FinancialEngine(db_manager=temp_db)
    engine.add_to_watchlist("BTC", target_price=50000.0, condition="above", asset_type="crypto")

    # 1. When network is down, get_market_quote returns ok=False, price=None
    with patch("httpx.AsyncClient.get", side_effect=Exception("Offline")):
        alerts = await engine.check_alerts()
        # MUST NOT fire alert even though user set condition "above 50000"
        assert len(alerts) == 0

    # 2. When quote is explicitly marked stale or older than 15 minutes
    fake_old_record = {
        "ok": True,
        "symbol": "BTC",
        "price": 90000.0,
        "stale": True,
        "fetched_at": (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    }
    with patch.object(engine, "get_market_quote", return_value=fake_old_record):
        alerts = await engine.check_alerts()
        assert len(alerts) == 0

@pytest.mark.asyncio
async def test_live_data_returns_typed_error_on_network_failure():
    """Verifies weather, mutual fund, and sports return typed error records on complete network failure."""
    pipeline = LiveDataPipeline()
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        # Weather
        wx = await pipeline.get_weather("Seattle")
        assert wx["ok"] is False
        assert wx["stale"] is True
        assert wx["temperature"] is None
        assert wx["condition"] is None
        assert wx["source"] == "unreachable"

        # Mutual fund
        mf = await pipeline.get_mutual_fund("SBI Magnum")
        assert mf["ok"] is False
        assert mf["stale"] is True
        assert mf["nav"] is None
        assert mf["source"] == "unreachable"

        # Sports
        sports = await pipeline.get_sports_score("basketball", "Lakers vs Warriors")
        assert sports["ok"] is False
        assert sports["stale"] is True
        assert sports["status"] is None
        assert sports["source"] == "unreachable"

@pytest.mark.asyncio
async def test_news_briefing_returns_typed_error_when_offline():
    """Verifies tech news returns 0 articles and error record on feed failure."""
    briefing = TechNewsBriefing()
    with patch("feedparser.parse", side_effect=Exception("Feed unreachable")):
        res = await briefing.get_briefing()
        assert res["ok"] is False
        assert res["articles_count"] == 0
        assert res["articles"] == []
        assert "unavailable: network offline" in res["briefing_markdown"]
        assert res["stale"] is True

@pytest.mark.asyncio
async def test_morning_briefing_skips_unauthenticated_email():
    """Verifies morning briefing explicitly states Gmail is not connected when unauthenticated."""
    briefing = TechNewsBriefing()
    with patch("services.backend.integrations.google_workspace.google_workspace.is_gmail_configured", return_value=False):
        res = await briefing.get_morning_briefing()
        assert res["ok"] is True
        assert "Email summary skipped: Gmail integration is not connected or authenticated." in res["briefing_markdown"]

@pytest.mark.asyncio
async def test_research_returns_typed_error_without_fake_citations():
    """Verifies research engine returns typed error records and empty lists on network failure."""
    engine = ResearchEngine()
    with patch("httpx.AsyncClient.get", side_effect=Exception("Offline")):
        # DOI Crossref
        doi_res = await engine.lookup_doi_crossref("10.1234/test")
        assert doi_res["ok"] is False
        assert doi_res["stale"] is True
        assert doi_res["citations_count"] is None
        assert doi_res["title"] is None

        # Google scholar scrape
        scraped = await engine.search_google_scholar_scraped("quantum computing")
        assert scraped == []

        # Unified search
        unified = await engine.unified_search("artificial intelligence")
        assert unified["ok"] is False
        assert unified["total_found"] == 0
        assert unified["results"] == []
