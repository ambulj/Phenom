# HANDOFF.md

Updated at the conclusion of Phase 5 (Modes, Scheduler, and Integrations).

## Current phase
Phase 5: Modes, Scheduler, and Integrations (COMPLETE)

## How to run
```bash
# 1. Run all backend tests (46 tests across safety, router, tools, memory, voice, automation, RAG, modes, scheduler, integrations)
python -m pytest services/backend/tests/ -v

# 2. Run voice benchmarks
python services/backend/voice/benchmark_voice.py

# 3. Typecheck and build the desktop UI
cd apps/desktop
npm run build
cd ../..

# 4. Start backend and desktop app together with a single command
npm run dev
```

## What exists
- `apps/desktop/`:
  - `electron/main.cjs`: Electron window host with global shortcut registration (`Ctrl+Alt+Pause` Guardian kill switch).
  - `src/App.tsx`: Central coordinator managing WebSocket link, voice amplitude, live view frames, takeover prompts, active modes, scheduled reminders, and watchlist alerts.
  - `src/components/Orb.tsx`: 3D Three.js particle orb with calm, listening, thinking, speaking, and halted states.
  - `src/components/HeaderBar.tsx`: Fluent UI header with connection indicator, microphone mute toggle, listening badge indicator, Guardian Kill Switch / Resume button, live view launcher, one-click Mode cycle badge (`Work` / `Study` / `Chill`), Dashboard button, and Mini Overlay toggle.
  - `src/components/MiniOverlay.tsx`: Compact floating widget displaying current task state, next scheduled item, active mode badge with one-click cycle, and immediate Guardian Kill Switch.
  - `src/components/panels/`:
    - `DashboardPanel.tsx`: 4-tab command center: Scheduler & Reminders (quick add, active items, run logs), Financial Watchlist (informational alerts, prices, conditions), Live Safety Action Logs, and Tech News Briefing (HN, TechCrunch, The Verge).
    - `LiveViewPanel.tsx`: Live viewport frame stream, human takeover alert banner with "Continue" and "Stop" actions, and execution step list overlay.
    - `HistoryPanel.tsx`: View persisted conversation turns.
    - `ActionLogPanel.tsx`: Security audit trail showing tier, tool, decision, and redacted arguments.
    - `LearnedRulesPanel.tsx`: View, edit, and delete learned rules.
    - `ApprovalsPanel.tsx`: View and manage remembered folder approvals.
    - `SettingsPanel.tsx`: Wake phrase selector, mic privacy toggle, and global hotkeys editor with real-time conflict error reporting.
- `services/backend/`:
  - `modes/`:
    - `mode_manager.py`: Three assistant modes (`Work`, `Study`, `Chill` / Gaming). Controls enabled tools, system prompt tone modifier, and notification policy (standard, quiet, minimal). Switchable by voice, hotkey, or UI; persisted in encrypted SQLCipher DB.
  - `scheduler/`:
    - `cron.py`: BackgroundScheduler for recurring tasks and reminders. Persisted in SQLCipher (`scheduled_jobs`, `job_run_logs`), survives application restarts, fires on time, logs every run with status, duration, and summary.
  - `integrations/`:
    - `finance.py`: Market quotes for stocks and crypto. Watchlist price alerts that trigger once without duplicate spamming. Hard code prohibitions blocking trading (`place_trade`) and buy/sell recommendations (`suggest_trade`).
    - `google_workspace.py`: Gmail and Google Calendar integration. Search/read emails, save Gmail drafts (never send). List calendar events, create calendar events (never delete or edit). Hard code prohibitions throwing `EmailSendingProhibitedError` and `CalendarModificationProhibitedError`.
    - `live_data.py`: Multi-source live data pipeline (Weather, Mutual Funds, Sports). Fixed order: Official API first, fallback to web scraping, explicitly labelled `source="scraped"`.
    - `news_briefing.py`: Tech news briefing aggregating Hacker News, TechCrunch, and The Verge RSS feeds.
    - `research.py`: Academic research sources: arXiv official API, Semantic Scholar API, Crossref DOI/citation lookup, and Google Scholar scraped fallback (labelled `less_reliable`).
    - `doc_generator.py`: Generates documents across 4 formats: Word (.docx via python-docx), Excel (.xlsx via openpyxl), PowerPoint (.pptx via python-pptx), and PDF (.pdf via reportlab). All verified to open and parse cleanly.
  - `tools/`:
    - `integration_tools.py`: 13 Tier 0 tools, 7 Tier 1 tools, 1 Tier 2 tool, and 5 Tier 3 blocked tools registered behind the Safety Layer.
    - `memory_tools.py`, `automation_tools.py`, `file_tools.py`, `app_tools.py`.
  - `memory/`:
    - `db.py`: Encrypted SQLCipher database manager storing messages, facts, rules, settings, embeddings, photo index, scheduled jobs, job logs, and financial watchlist.
    - `doc_reader.py`, `vector_store.py`, `vault.py`, `photo_indexer.py`, `cleanup_organizer.py`, `rules.py`.
  - `orchestrator/`:
    - `engine.py`: Conversational loop with Jarvis personality, dynamic mode tone modifier injection, RAG memory context injection, safety wrapping, and automatic persistence.
  - `tests/`:
    - 46 passed unit and integration tests under `services/backend/tests/` (100% pass rate).

## Phase 5 Verification Results
| Requirement / Done Criterion | Specification | Empirical Evidence | Status |
| :--- | :--- | :--- | :---: |
| **Three Assistant Modes** | Work, Study, Chill modify tone, tools & notifications | Work (standard), Study (quiet/DND), Chill (minimal/low resource) switch cleanly and persist in DB | PASS |
| **Scheduler Persistence & Execution** | Fires on time, survives restart, logs runs | Job created in DB, surviving reload in fresh scheduler instance, executed and logged in `job_run_logs` | PASS |
| **Live Data API Fallback & Labelling** | Official API first, fallback to scraping with label | When API is unavailable, fallback triggers and returns `source="scraped"` for weather, mutual funds, sports | PASS |
| **Watchlist Single-Trigger Alert** | Informational alert triggers once when condition met | AAPL alert above $180 triggers once at $185, marks `triggered=1`, ignores subsequent checks at $190 | PASS |
| **Finance Hard Prohibitions** | No trades, no buy/sell suggestions | `place_trade` and `suggest_trade` throw `TradingProhibitedError` and are registered as Tier 3 | PASS |
| **Email Hard Prohibitions** | Drafts allowed, sending email permanently blocked | `create_draft` creates Gmail draft; `send_email` throws `EmailSendingProhibitedError` (Tier 3) | PASS |
| **Calendar Hard Prohibitions** | Creation allowed, delete and edit blocked | `create_event` creates event; `delete_calendar_event` and `edit_calendar_event` throw `CalendarModificationProhibitedError` | PASS |
| **Document Generation & Parsing** | Word, Excel, PowerPoint, PDF created & open correctly | All 4 formats generated and verified to open cleanly with `python-docx`, `openpyxl`, `python-pptx`, `pypdf` | PASS |
| **Tech News Briefing** | Hacker News, TechCrunch, The Verge RSS feeds | `tech_news.get_briefing` parses feeds and formats Markdown briefing with article titles and links | PASS |
| **Academic Research Sources** | arXiv, Semantic Scholar, Crossref, Google Scholar | Unified search across arXiv, Semantic Scholar, Crossref citations, and Google Scholar scraped fallback | PASS |
| **Dashboard & Mini Overlay** | Live tasks, scheduled jobs, watchlist, and kill switch | `DashboardPanel.tsx` (4 tabs) and floating `MiniOverlay.tsx` with one-click mode cycle and HALT switch | PASS |

## Dependencies added
- `beautifulsoup4` (4.15.0): HTML parsing and live data web scraping fallback.
- `feedparser` (6.0.14): RSS feed parser for tech news briefing (Hacker News, TechCrunch, The Verge).

## Known issues
- None. All Phase 5 done criteria met.

## Open questions for the user
- None for Phase 5.

## Next
Phase 6: Remote Control via Telegram. Bot whitelisted to owner user ID only, push notifications for approvals, remote chat, status queries, remote kill switch, and safe remote file transfer.
