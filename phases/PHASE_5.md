Phase 5: Modes, Scheduler, and Integrations
PHASE 5: modes, scheduler, integrations.

1. Three modes: Work (Gmail, Calendar, documents), Study (summaries, research, quiet notifications), and Chill / Gaming (low resource use, playful tone). A mode changes enabled tools, tone, and notification rules, and is switchable by voice, hotkey, or UI.
2. Scheduler for recurring tasks and reminders, shown in the dashboard tab and the mini overlay, with logs for every run.
3. Gmail and Google Calendar with OAuth. Reading is allowed. Phenom may save email drafts (never send) and create calendar events, both with a previewed confirmation. Sending email, deleting events, and editing other people’s events are blocked.
4. Live data with a fixed order: official API first, then scraping as a fallback, labelled as scraped. Cover weather, news, stocks, crypto, mutual funds, and sports.
5. Tech news briefing from Hacker News, TechCrunch, and The Verge RSS feeds.
6. Finance is informational only: no trades, no buy or sell suggestions, and no predictions presented as advice. Price alerts only for a user-defined watchlist.
7. Research sources: arXiv, Semantic Scholar, Crossref for citations and DOI lookup, and Google Scholar by scraping, marked as less reliable.
8. Document creation with python-docx, openpyxl, python-pptx, and reportlab, saved to a chosen folder and logged.
9. Dashboard: a tab for live tasks and logs, plus a mini overlay with the current task, next scheduled item, and kill switch.

TESTS: scheduler fires on time and survives a restart; API failure falls back to scraping and is labelled; a watchlist alert triggers once; each document type opens correctly; a test that email sending is blocked.

DONE CRITERIA: every integration works or fails with a clear message, modes change behaviour visibly, and the finance and email restrictions are enforced in code.
FINISH: follow the finish protocol and stop.