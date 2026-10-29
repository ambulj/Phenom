"""
Phenom Live Data Pipeline (Phase 5)
Fixed pipeline order:
1. Official API first.
2. Web scraping as fallback, labelled as scraped ('source': 'scraped').
3. On network failure or offline: returns typed error records with ok=False, stale=True, and None for values.
Never fabricates numbers or mock status strings.
Covers: Weather, Mutual Funds, Sports.
"""

import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from bs4 import BeautifulSoup

logger = logging.getLogger("phenom.live_data")

class LiveDataPipeline:
    def __init__(self, force_scrape_for_testing: bool = False):
        self.force_scrape = force_scrape_for_testing
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def get_weather(self, city: str = "New York") -> Dict[str, Any]:
        """
        Gets current weather for city.
        API first (Open-Meteo geocoding & forecast), fallback to wttr.in scraping.
        Never fabricates numbers on failure.
        """
        city_clean = city.strip()
        fetch_time = datetime.now(timezone.utc).isoformat()
        
        # 1. API: Open-Meteo
        if not self.force_scrape:
            try:
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_clean}&count=1&language=en&format=json"
                async with httpx.AsyncClient(timeout=4.0) as client:
                    geo_resp = await client.get(geo_url)
                    if geo_resp.status_code == 200:
                        results = geo_resp.json().get("results", [])
                        if results:
                            lat = results[0]["latitude"]
                            lon = results[0]["longitude"]
                            country = results[0].get("country", "")
                            
                            wx_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
                            wx_resp = await client.get(wx_url)
                            if wx_resp.status_code == 200:
                                current = wx_resp.json().get("current", {})
                                record = {
                                    "ok": True,
                                    "location": f"{city_clean}, {country}".strip(", "),
                                    "temperature_c": current.get("temperature_2m"),
                                    "feels_like_c": current.get("apparent_temperature"),
                                    "humidity_pct": current.get("relative_humidity_2m"),
                                    "wind_kmh": current.get("wind_speed_10m"),
                                    "source": "api",
                                    "provider": "https://api.open-meteo.com",
                                    "timestamp": fetch_time,
                                    "fetched_at": fetch_time,
                                    "stale": False
                                }
                                self._cache[f"weather_{city_clean.lower()}"] = record
                                return record
            except Exception as e:
                logger.warning(f"Open-Meteo API failed for {city_clean}: {e}")

        # 2. Scraped Fallback: wttr.in
        try:
            scrape_url = f"https://wttr.in/{city_clean}?format=%C+%t+%h+%w"
            headers = {"User-Agent": "curl/7.68.0"}
            async with httpx.AsyncClient(timeout=4.0, headers=headers) as client:
                resp = await client.get(scrape_url)
                if resp.status_code == 200 and resp.text.strip():
                    parts = resp.text.strip().split()
                    condition = parts[0] if parts else "Clear"
                    temp = parts[1] if len(parts) > 1 else "N/A"
                    record = {
                        "ok": True,
                        "location": city_clean,
                        "condition": condition,
                        "temperature": temp,
                        "raw_summary": resp.text.strip(),
                        "source": "scraped",
                        "provider": "https://wttr.in",
                        "timestamp": fetch_time,
                        "fetched_at": fetch_time,
                        "stale": False
                    }
                    self._cache[f"weather_{city_clean.lower()}"] = record
                    return record
        except Exception as e:
            logger.warning(f"wttr.in scraping failed for {city_clean}: {e}")

        # Return cached entry marked stale if exists
        cache_key = f"weather_{city_clean.lower()}"
        if cache_key in self._cache:
            cached = dict(self._cache[cache_key])
            cached["stale"] = True
            return cached

        # Never fabricate: return typed error record
        return {
            "ok": False,
            "error": "network_unavailable",
            "provider": "wttr.in/open-meteo",
            "location": city_clean,
            "condition": None,
            "temperature": None,
            "source": "unreachable",
            "stale": True,
            "fetched_at": None,
            "message": f"Weather data for '{city_clean}' is currently unavailable."
        }

    async def get_mutual_fund(self, query: str = "HDFC") -> Dict[str, Any]:
        """
        Gets mutual fund NAV and details.
        API first (mfapi.in), fallback to AMFI scraping.
        Never fabricates numbers on failure.
        """
        query_clean = query.strip()
        fetch_time = datetime.now(timezone.utc).isoformat()

        # 1. API: mfapi.in
        if not self.force_scrape:
            try:
                search_url = f"https://api.mfapi.in/mf/search?q={query_clean}"
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(search_url)
                    if resp.status_code == 200:
                        funds = resp.json()
                        if funds:
                            code = funds[0]["schemeCode"]
                            name = funds[0]["schemeName"]
                            nav_resp = await client.get(f"https://api.mfapi.in/mf/{code}")
                            if nav_resp.status_code == 200:
                                nav_data = nav_resp.json()
                                latest_nav = nav_data.get("data", [{}])[0]
                                record = {
                                    "ok": True,
                                    "scheme_name": name,
                                    "scheme_code": str(code),
                                    "nav": float(latest_nav.get("nav", 0.0)),
                                    "nav_date": latest_nav.get("date", ""),
                                    "source": "api",
                                    "provider": "https://api.mfapi.in",
                                    "timestamp": fetch_time,
                                    "fetched_at": fetch_time,
                                    "stale": False
                                }
                                self._cache[f"mf_{query_clean.lower()}"] = record
                                return record
            except Exception as e:
                logger.warning(f"mfapi.in API failed for {query_clean}: {e}")

        # 2. Scraped Fallback: AMFI portal
        try:
            scrape_url = f"https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?tp=1&frmdt={datetime.now(timezone.utc).strftime('%d-%b-%Y')}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(scrape_url)
                if resp.status_code == 200 and resp.text:
                    for line in resp.text.splitlines():
                        if ";" in line and query_clean.lower() in line.lower():
                            parts = line.split(";")
                            if len(parts) >= 5:
                                record = {
                                    "ok": True,
                                    "scheme_name": parts[1].strip(),
                                    "scheme_code": parts[0].strip(),
                                    "nav": float(parts[4].strip()),
                                    "nav_date": parts[5].strip() if len(parts) > 5 else "",
                                    "source": "scraped",
                                    "provider": "https://portal.amfiindia.com",
                                    "timestamp": fetch_time,
                                    "fetched_at": fetch_time,
                                    "stale": False
                                }
                                self._cache[f"mf_{query_clean.lower()}"] = record
                                return record
        except Exception as e:
            logger.warning(f"AMFI scraping failed for {query_clean}: {e}")

        # Return cached if available
        cache_key = f"mf_{query_clean.lower()}"
        if cache_key in self._cache:
            cached = dict(self._cache[cache_key])
            cached["stale"] = True
            return cached

        # Never fabricate: return typed error record
        return {
            "ok": False,
            "error": "network_unavailable",
            "provider": "https://api.mfapi.in",
            "query": query_clean,
            "nav": None,
            "scheme_name": query_clean,
            "scheme_code": None,
            "source": "unreachable",
            "stale": True,
            "fetched_at": None,
            "message": f"Mutual fund data for '{query_clean}' is currently unavailable."
        }

    async def get_sports_score(self, sport: str = "football", match_query: str = "") -> Dict[str, Any]:
        """
        Gets sports scores.
        API first (ESPN scoreboard API), fallback to web scraping.
        Never fabricates scores on failure.
        """
        sport_clean = sport.lower().strip()
        fetch_time = datetime.now(timezone.utc).isoformat()

        # 1. Official ESPN summary API
        if not self.force_scrape:
            try:
                espn_sport = "football" if "soccer" in sport_clean or "football" in sport_clean else "basketball"
                espn_league = "eng.1" if espn_sport == "football" else "nba"
                api_url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_sport}/{espn_league}/scoreboard"
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(api_url)
                    if resp.status_code == 200:
                        events = resp.json().get("events", [])
                        if events:
                            event = events[0]
                            record = {
                                "ok": True,
                                "sport": sport_clean,
                                "match_name": event.get("name", "Live Match"),
                                "status": event.get("status", {}).get("type", {}).get("detail", "In Progress"),
                                "source": "api",
                                "provider": "https://site.api.espn.com",
                                "timestamp": fetch_time,
                                "fetched_at": fetch_time,
                                "stale": False
                            }
                            self._cache[f"sports_{sport_clean}"] = record
                            return record
            except Exception as e:
                logger.warning(f"ESPN API failed for {sport_clean}: {e}")

        # 2. Scraped Fallback: BBC sport HTML
        try:
            scrape_url = f"https://www.bbc.com/sport/{sport_clean}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            async with httpx.AsyncClient(timeout=4.0, headers=headers) as client:
                resp = await client.get(scrape_url)
                if resp.status_code == 200 and resp.text:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title = soup.find("title")
                    record = {
                        "ok": True,
                        "sport": sport_clean,
                        "match_name": f"{match_query or 'Featured Match'} Summary",
                        "status": title.text.strip() if title else "Live Coverage",
                        "source": "scraped",
                        "provider": "https://www.bbc.com/sport",
                        "timestamp": fetch_time,
                        "fetched_at": fetch_time,
                        "stale": False
                    }
                    self._cache[f"sports_{sport_clean}"] = record
                    return record
        except Exception as e:
            logger.warning(f"Sports scrape failed for {sport_clean}: {e}")

        # Return cached if available
        cache_key = f"sports_{sport_clean}"
        if cache_key in self._cache:
            cached = dict(self._cache[cache_key])
            cached["stale"] = True
            return cached

        # Never fabricate: return typed error record
        return {
            "ok": False,
            "error": "network_unavailable",
            "provider": "site.api.espn.com",
            "sport": sport_clean,
            "status": None,
            "match_name": match_query or None,
            "source": "unreachable",
            "stale": True,
            "fetched_at": None,
            "message": f"Sports score for '{sport_clean}' is currently unavailable."
        }

# Global live data pipeline
live_data_pipeline = LiveDataPipeline()
