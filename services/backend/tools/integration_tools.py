"""
Phenom Phase 5 Integration Tools
Registered behind the Safety Layer:
- Tier 0: get_mode, list_scheduled_jobs, get_weather, get_tech_news, get_market_quote, get_financial_watchlist, get_mutual_fund_quote, get_sports_score, search_research_papers, lookup_doi_citation, gmail_search_emails, gmail_read_email, calendar_list_events
- Tier 1: set_mode, schedule_reminder, cancel_scheduled_job, add_to_financial_watchlist, remove_from_financial_watchlist, gmail_create_draft, generate_document
- Tier 2: calendar_create_event
- Tier 3: send_email (BLOCKED), calendar_delete_event (BLOCKED), calendar_edit_event (BLOCKED), place_trade (BLOCKED), suggest_trade (BLOCKED)
"""

import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry
from services.backend.modes.mode_manager import mode_manager, AssistantMode
from services.backend.scheduler.cron import background_scheduler
from services.backend.integrations.finance import financial_engine, TradingProhibitedError
from services.backend.integrations.google_workspace import google_workspace, EmailSendingProhibitedError, CalendarModificationProhibitedError
from services.backend.integrations.live_data import live_data_pipeline
from services.backend.integrations.news_briefing import tech_news
from services.backend.integrations.research import research_engine
from services.backend.integrations.doc_generator import doc_generator

# ==========================================
# 1. MODES TOOLS
# ==========================================

class GetModeArgs(BaseModel):
    pass

@registry.register(
    name="get_mode",
    tier=0,
    description="Gets the current assistant operating mode (Work, Study, or Chill) and active profile.",
    args_schema=GetModeArgs,
    preview_fn=lambda a: "Inspect current operating mode and profile"
)
def get_mode() -> Dict[str, Any]:
    curr = mode_manager.get_current_mode()
    return mode_manager.get_mode_profile(curr)

class SetModeArgs(BaseModel):
    mode: str = Field(description="Mode name to switch to: 'work', 'study', or 'chill'")

@registry.register(
    name="set_mode",
    tier=1,
    description="Changes the assistant operating mode (Work, Study, Chill) which alters enabled tools, tone, and notification policy.",
    args_schema=SetModeArgs,
    preview_fn=lambda a: f"Switch assistant mode to '{a.get('mode')}'"
)
def set_mode(mode: str) -> Dict[str, Any]:
    return mode_manager.set_mode(mode)

# ==========================================
# 2. SCHEDULER TOOLS
# ==========================================

class ListScheduledJobsArgs(BaseModel):
    include_disabled: bool = Field(default=False, description="Whether to include disabled or completed jobs")

@registry.register(
    name="list_scheduled_jobs",
    tier=0,
    description="Lists all scheduled tasks, recurring jobs, and reminders.",
    args_schema=ListScheduledJobsArgs,
    preview_fn=lambda a: "List scheduled tasks and reminders"
)
def list_scheduled_jobs(include_disabled: bool = False) -> List[Dict[str, Any]]:
    return background_scheduler.list_jobs(include_disabled=include_disabled)

class ScheduleReminderArgs(BaseModel):
    title: str = Field(description="Title or content of the reminder")
    delay_seconds: Optional[int] = Field(default=None, description="Delay in seconds before reminder fires")
    due_at: Optional[str] = Field(default=None, description="ISO timestamp for when reminder fires")
    note: Optional[str] = Field(default=None, description="Optional extra notes")

@registry.register(
    name="schedule_reminder",
    tier=1,
    description="Schedules a one-time reminder or recurring task.",
    args_schema=ScheduleReminderArgs,
    preview_fn=lambda a: f"Schedule reminder '{a.get('title')}' (delay: {a.get('delay_seconds')}s, due_at: {a.get('due_at')})"
)
def schedule_reminder(title: str, delay_seconds: Optional[int] = None, due_at: Optional[str] = None, note: Optional[str] = None) -> Dict[str, Any]:
    payload = {"note": note} if note else {}
    return background_scheduler.add_reminder(title, delay_seconds=delay_seconds, due_at=due_at, payload=payload)

class CancelScheduledJobArgs(BaseModel):
    job_id: str = Field(description="ID of the scheduled job or reminder to cancel")

@registry.register(
    name="cancel_scheduled_job",
    tier=1,
    description="Cancels or disables an active scheduled job or reminder.",
    args_schema=CancelScheduledJobArgs,
    preview_fn=lambda a: f"Cancel scheduled job ID '{a.get('job_id')}'"
)
def cancel_scheduled_job(job_id: str) -> Dict[str, Any]:
    success = background_scheduler.cancel_job(job_id)
    return {"job_id": job_id, "cancelled": success}

# ==========================================
# 3. LIVE DATA & NEWS TOOLS
# ==========================================

class GetWeatherArgs(BaseModel):
    city: str = Field(default="New York", description="Name of the city to get weather for")

@registry.register(
    name="get_weather",
    tier=0,
    description="Gets live weather via official API first, falling back to web scraping if API is unavailable.",
    args_schema=GetWeatherArgs,
    preview_fn=lambda a: f"Get live weather for '{a.get('city')}'"
)
def get_weather(city: str = "New York") -> Dict[str, Any]:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(live_data_pipeline.get_weather(city))
        return asyncio.run(live_data_pipeline.get_weather(city))
    except Exception:
        # synchronous helper
        return asyncio.run(live_data_pipeline.get_weather(city))

class GetTechNewsArgs(BaseModel):
    items_per_source: int = Field(default=3, description="Articles per outlet (Hacker News, TechCrunch, The Verge)")

@registry.register(
    name="get_tech_news",
    tier=0,
    description="Gets aggregated tech news briefing from Hacker News, TechCrunch, and The Verge RSS feeds.",
    args_schema=GetTechNewsArgs,
    preview_fn=lambda a: "Fetch tech news briefing from Hacker News, TechCrunch, and The Verge"
)
def get_tech_news(items_per_source: int = 3) -> Dict[str, Any]:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(tech_news.get_briefing(items_per_source))
        return asyncio.run(tech_news.get_briefing(items_per_source))
    except Exception:
        return asyncio.run(tech_news.get_briefing(items_per_source))

class GetMutualFundArgs(BaseModel):
    query: str = Field(default="HDFC", description="Mutual fund scheme name or code")

@registry.register(
    name="get_mutual_fund_quote",
    tier=0,
    description="Gets mutual fund NAV info via official API first, fallback to scraping.",
    args_schema=GetMutualFundArgs,
    preview_fn=lambda a: f"Get mutual fund quote for '{a.get('query')}'"
)
def get_mutual_fund_quote(query: str = "HDFC") -> Dict[str, Any]:
    return asyncio.run(live_data_pipeline.get_mutual_fund(query))

class GetSportsScoreArgs(BaseModel):
    sport: str = Field(default="football", description="Sport name (e.g. football, basketball, cricket)")
    match_query: str = Field(default="", description="Optional match or team name")

@registry.register(
    name="get_sports_score",
    tier=0,
    description="Gets live sports scores via API first, fallback to scraping.",
    args_schema=GetSportsScoreArgs,
    preview_fn=lambda a: f"Get sports score for '{a.get('sport')}' ({a.get('match_query')})"
)
def get_sports_score(sport: str = "football", match_query: str = "") -> Dict[str, Any]:
    return asyncio.run(live_data_pipeline.get_sports_score(sport, match_query))

# ==========================================
# 4. FINANCE & WATCHLIST TOOLS
# ==========================================

class GetMarketQuoteArgs(BaseModel):
    symbol: str = Field(description="Stock or crypto ticker symbol (e.g. AAPL, NVDA, BTC, ETH)")
    asset_type: Optional[str] = Field(default=None, description="Asset type: 'stock' or 'crypto'")

@registry.register(
    name="get_market_quote",
    tier=0,
    description="Gets current market quote for stock or crypto. Informational only, not financial advice.",
    args_schema=GetMarketQuoteArgs,
    preview_fn=lambda a: f"Get informational market quote for '{a.get('symbol')}'"
)
def get_market_quote(symbol: str, asset_type: Optional[str] = None) -> Dict[str, Any]:
    return asyncio.run(financial_engine.get_market_quote(symbol, asset_type))

class GetFinancialWatchlistArgs(BaseModel):
    pass

@registry.register(
    name="get_financial_watchlist",
    tier=0,
    description="Lists all tracked symbols and active price alerts in the financial watchlist.",
    args_schema=GetFinancialWatchlistArgs,
    preview_fn=lambda a: "Inspect financial watchlist and price alerts"
)
def get_financial_watchlist() -> List[Dict[str, Any]]:
    return financial_engine.list_watchlist()

class AddToFinancialWatchlistArgs(BaseModel):
    symbol: str = Field(description="Ticker symbol to watch (e.g. AAPL, BTC)")
    target_price: float = Field(description="Target price to trigger alert")
    condition: str = Field(default="above", description="Condition: 'above' or 'below'")
    asset_type: str = Field(default="stock", description="Asset type: 'stock' or 'crypto'")

@registry.register(
    name="add_to_financial_watchlist",
    tier=1,
    description="Adds a price alert for a ticker symbol to the user watchlist (triggers once). Informational only.",
    args_schema=AddToFinancialWatchlistArgs,
    preview_fn=lambda a: f"Add alert to watchlist: {a.get('symbol')} {a.get('condition')} ${a.get('target_price')}"
)
def add_to_financial_watchlist(symbol: str, target_price: float, condition: str = "above", asset_type: str = "stock") -> Dict[str, Any]:
    return financial_engine.add_to_watchlist(symbol, target_price, condition, asset_type)

class RemoveFromFinancialWatchlistArgs(BaseModel):
    symbol: str = Field(description="Ticker symbol to remove from watchlist")

@registry.register(
    name="remove_from_financial_watchlist",
    tier=1,
    description="Removes a symbol from the financial watchlist.",
    args_schema=RemoveFromFinancialWatchlistArgs,
    preview_fn=lambda a: f"Remove '{a.get('symbol')}' from financial watchlist"
)
def remove_from_financial_watchlist(symbol: str) -> Dict[str, Any]:
    success = financial_engine.remove_from_watchlist(symbol)
    return {"symbol": symbol, "removed": success}

# Prohibited Finance Tools (Tier 3 - Blocked)
class PlaceTradeArgs(BaseModel):
    symbol: str
    action: str
    quantity: float

@registry.register(
    name="place_trade",
    tier=3,
    description="BLOCKED: Placing financial trades or executing orders is permanently prohibited.",
    args_schema=PlaceTradeArgs,
    preview_fn=lambda a: f"Attempted trade: {a.get('action')} {a.get('quantity')} {a.get('symbol')}"
)
def place_trade(symbol: str, action: str, quantity: float) -> None:
    financial_engine.place_trade(symbol, action, quantity)

class SuggestTradeArgs(BaseModel):
    symbol: str

@registry.register(
    name="suggest_trade",
    tier=3,
    description="BLOCKED: Recommending buy, sell, or trade actions is permanently prohibited.",
    args_schema=SuggestTradeArgs,
    preview_fn=lambda a: f"Attempted trade suggestion for: {a.get('symbol')}"
)
def suggest_trade(symbol: str) -> None:
    financial_engine.suggest_trade(symbol)

# ==========================================
# 5. GOOGLE WORKSPACE TOOLS
# ==========================================

class GmailSearchArgs(BaseModel):
    query: str = Field(default="", description="Search query or keyword for emails")
    max_results: int = Field(default=5, description="Maximum emails to return")

@registry.register(
    name="gmail_search_emails",
    tier=0,
    description="Searches Gmail inbox and messages. Read-only.",
    args_schema=GmailSearchArgs,
    preview_fn=lambda a: f"Search Gmail for: '{a.get('query')}'"
)
def gmail_search_emails(query: str = "", max_results: int = 5) -> List[Dict[str, Any]]:
    return google_workspace.search_emails(query, max_results)

class GmailReadEmailArgs(BaseModel):
    email_id: str = Field(description="ID of the email message to read")

@registry.register(
    name="gmail_read_email",
    tier=0,
    description="Reads full content of a specific email message.",
    args_schema=GmailReadEmailArgs,
    preview_fn=lambda a: f"Read email ID '{a.get('email_id')}'"
)
def gmail_read_email(email_id: str) -> Optional[Dict[str, Any]]:
    return google_workspace.read_email(email_id)

class GmailCreateDraftArgs(BaseModel):
    to: str = Field(description="Recipient email address")
    subject: str = Field(description="Subject line")
    body: str = Field(description="Draft message body")

@registry.register(
    name="gmail_create_draft",
    tier=1,
    description="Creates an email draft in Gmail for user review. Never sends.",
    args_schema=GmailCreateDraftArgs,
    preview_fn=lambda a: f"Create Gmail draft to '{a.get('to')}' with subject '{a.get('subject')}'"
)
def gmail_create_draft(to: str, subject: str, body: str) -> Dict[str, Any]:
    return google_workspace.create_draft(to, subject, body)

class CalendarListEventsArgs(BaseModel):
    max_results: int = Field(default=10, description="Max calendar events to return")

@registry.register(
    name="calendar_list_events",
    tier=0,
    description="Lists upcoming events on Google Calendar. Read-only.",
    args_schema=CalendarListEventsArgs,
    preview_fn=lambda a: "List upcoming calendar events"
)
def calendar_list_events(max_results: int = 10) -> List[Dict[str, Any]]:
    return google_workspace.list_events(max_results)

class CalendarCreateEventArgs(BaseModel):
    summary: str = Field(description="Title or summary of the calendar event")
    start_time: str = Field(description="Start time (ISO format, e.g. 2026-10-29T14:00:00Z)")
    end_time: str = Field(description="End time (ISO format, e.g. 2026-10-29T15:00:00Z)")
    description: str = Field(default="", description="Optional description of the event")

@registry.register(
    name="calendar_create_event",
    tier=2,
    description="Creates a new event on Google Calendar. Requires explicit previewed confirmation.",
    args_schema=CalendarCreateEventArgs,
    preview_fn=lambda a: f"Create calendar event '{a.get('summary')}' from {a.get('start_time')} to {a.get('end_time')}"
)
def calendar_create_event(summary: str, start_time: str, end_time: str, description: str = "") -> Dict[str, Any]:
    return google_workspace.create_event(summary, start_time, end_time, description)

# Prohibited Google Workspace Tools (Tier 3 - Blocked)
class SendEmailArgs(BaseModel):
    to: str
    subject: str
    body: str

@registry.register(
    name="send_email",
    tier=3,
    description="BLOCKED: Sending emails is permanently prohibited by Phenom safety rules. Drafts only.",
    args_schema=SendEmailArgs,
    preview_fn=lambda a: f"Attempted send email to '{a.get('to')}'"
)
def send_email(to: str, subject: str, body: str) -> None:
    google_workspace.send_email(to, subject, body)

class CalendarDeleteEventArgs(BaseModel):
    event_id: str

@registry.register(
    name="calendar_delete_event",
    tier=3,
    description="BLOCKED: Deleting calendar events is permanently prohibited.",
    args_schema=CalendarDeleteEventArgs,
    preview_fn=lambda a: f"Attempted calendar delete for event '{a.get('event_id')}'"
)
def calendar_delete_event(event_id: str) -> None:
    google_workspace.delete_calendar_event(event_id)

class CalendarEditEventArgs(BaseModel):
    event_id: str
    updates: Dict[str, Any]

@registry.register(
    name="calendar_edit_event",
    tier=3,
    description="BLOCKED: Editing calendar events is permanently prohibited.",
    args_schema=CalendarEditEventArgs,
    preview_fn=lambda a: f"Attempted calendar edit for event '{a.get('event_id')}'"
)
def calendar_edit_event(event_id: str, updates: Dict[str, Any]) -> None:
    google_workspace.edit_calendar_event(event_id, updates)

# ==========================================
# 6. RESEARCH TOOLS
# ==========================================

class SearchResearchPapersArgs(BaseModel):
    query: str = Field(description="Research topic or keyword (searches arXiv, Semantic Scholar, Google Scholar)")
    limit: int = Field(default=5, description="Number of papers to retrieve")

@registry.register(
    name="search_research_papers",
    tier=0,
    description="Searches academic papers across arXiv, Semantic Scholar, and Google Scholar.",
    args_schema=SearchResearchPapersArgs,
    preview_fn=lambda a: f"Search academic research papers for '{a.get('query')}'"
)
def search_research_papers(query: str, limit: int = 5) -> Dict[str, Any]:
    return asyncio.run(research_engine.unified_search(query, limit_per_source=limit))

class LookupDoiCitationArgs(BaseModel):
    doi_or_query: str = Field(description="DOI identifier or publication title for Crossref citation lookup")

@registry.register(
    name="lookup_doi_citation",
    tier=0,
    description="Looks up official publication metadata and citation counts via Crossref.",
    args_schema=LookupDoiCitationArgs,
    preview_fn=lambda a: f"Lookup DOI or publication citation for '{a.get('doi_or_query')}'"
)
def lookup_doi_citation(doi_or_query: str) -> Dict[str, Any]:
    return asyncio.run(research_engine.lookup_doi_crossref(doi_or_query))

# ==========================================
# 7. DOCUMENT CREATION TOOLS
# ==========================================

class GenerateDocumentArgs(BaseModel):
    doc_type: str = Field(description="Document format: 'word' (.docx), 'excel' (.xlsx), 'powerpoint' (.pptx), or 'pdf' (.pdf)")
    filename: str = Field(description="Target filename (e.g. 'ProjectPlan.docx', 'Budget.xlsx')")
    title: str = Field(description="Main document title")
    content_spec: Dict[str, Any] = Field(description="Structured content payload (sections, headers, rows, slides, etc.)")
    folder: Optional[str] = Field(default=None, description="Optional target directory")

@registry.register(
    name="generate_document",
    tier=1,
    description="Creates a formatted document (Word, Excel, PowerPoint, or PDF) and saves to a folder.",
    args_schema=GenerateDocumentArgs,
    preview_fn=lambda a: f"Generate {a.get('doc_type')} document '{a.get('filename')}' in {a.get('folder') or 'vault/documents'}"
)
def generate_document(doc_type: str, filename: str, title: str, content_spec: Dict[str, Any], folder: Optional[str] = None) -> Dict[str, Any]:
    dtype = doc_type.lower().strip()
    if "word" in dtype or "docx" in dtype:
        sections = content_spec.get("sections", [{"heading": "Overview", "content": content_spec.get("text", "")}])
        return doc_generator.create_word_document(filename, title, sections, folder=folder)
    elif "excel" in dtype or "sheet" in dtype or "xlsx" in dtype:
        headers = content_spec.get("headers", ["Column 1", "Column 2"])
        rows = content_spec.get("rows", [["Data 1", "Data 2"]])
        sheet_title = content_spec.get("sheet_title", "Sheet1")
        return doc_generator.create_excel_spreadsheet(filename, sheet_title, headers, rows, folder=folder)
    elif "ppt" in dtype or "powerpoint" in dtype or "presentation" in dtype:
        subtitle = content_spec.get("subtitle", "Created by Phenom")
        slides = content_spec.get("slides", [{"title": "Introduction", "bullets": ["First point", "Second point"]}])
        return doc_generator.create_powerpoint_presentation(filename, title, subtitle, slides, folder=folder)
    elif "pdf" in dtype:
        paragraphs = content_spec.get("paragraphs", [content_spec.get("text", "Report content")])
        table_data = content_spec.get("table_data", None)
        return doc_generator.create_pdf_report(filename, title, paragraphs, table_data=table_data, folder=folder)
    else:
        raise ValueError(f"Unsupported doc_type '{doc_type}'. Allowed: word, excel, powerpoint, pdf.")
