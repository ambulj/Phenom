# HANDOFF.md

Updated at the conclusion of Phase 6 (Telegram Remote Control and Approvals).

## Current phase
Phase 6: Telegram Remote Control and Approvals (COMPLETE)

## How to run
```bash
# 1. Run all backend tests (52 tests across safety, router, tools, memory, voice, automation, RAG, modes, scheduler, integrations, and Telegram)
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
  - `src/App.tsx`: Central coordinator managing WebSocket link, voice amplitude, live view frames, takeover prompts, active modes, scheduled reminders, watchlist alerts, and remote lock status.
  - `src/components/Orb.tsx`: 3D Three.js particle orb with calm, listening, thinking, speaking, and halted states.
  - `src/components/HeaderBar.tsx`: Fluent UI header with connection indicator, microphone mute toggle, listening badge indicator, Guardian Kill Switch / Resume button, live view launcher, one-click Mode cycle badge (`Work` / `Study` / `Chill`), Dashboard button, and Mini Overlay toggle.
  - `src/components/MiniOverlay.tsx`: Compact floating widget displaying current task state, next scheduled item, active mode badge with one-click cycle, and immediate Guardian Kill Switch.
  - `src/components/panels/`:
    - `SettingsPanel.tsx`: Wake phrase selector, mic privacy toggle, global hotkeys editor, and **Telegram Remote Control configuration section** (token and owner ID management in Credential Manager, remote lock/unlock controls).
    - `DashboardPanel.tsx`: 4-tab command center: Scheduler & Reminders (quick add, active items, run logs), Financial Watchlist (informational alerts, prices, conditions), Live Safety Action Logs, and Tech News Briefing (HN, TechCrunch, The Verge).
    - `LiveViewPanel.tsx`: Live viewport frame stream, human takeover alert banner with "Continue" and "Stop" actions, and execution step list overlay.
    - `HistoryPanel.tsx`: View persisted conversation turns.
    - `ActionLogPanel.tsx`: Security audit trail showing tier, tool, decision, and redacted arguments.
    - `LearnedRulesPanel.tsx`: View, edit, and delete learned rules.
    - `ApprovalsPanel.tsx`: View and manage remembered folder approvals.
- `services/backend/`:
  - `remote/`:
    - `credentials.py`: Secure storage and retrieval of Telegram bot token and owner user ID using Windows Credential Manager (`Phenom/telegram-token`, `Phenom/telegram-owner-id`). Manages remote lock state.
    - `telegram_client.py`: Asynchronous HTTP client for the official Telegram Bot API via `httpx`. Handles message delivery, markdown formatting, inline confirmation buttons, and callback queries.
    - `telegram_bot.py`: Telegram remote controller with strict sender whitelisting (owner ID only; non-whitelisted senders silently ignored and logged). Dispatches `/lock` (disables remote control until re-enabled at desktop), `/halt` and `/kill` (remote Guardian kill switch), `/status`, `/tasks`, and `/logs` (with redacted content). Executes conversation turns through the orchestrator with `source="telegram"`.
  - `safety/`:
    - `engine.py`: SafetyExecutionEngine with remote confirmation handler hook. Enforces that Tier 3 tools (`send_email`, `place_trade`, etc.) cannot be approved remotely and are permanently refused with clear error messages.
  - `modes/`:
    - `mode_manager.py`: Three assistant modes (`Work`, `Study`, `Chill` / Gaming).
  - `scheduler/`:
    - `cron.py`: BackgroundScheduler for recurring tasks and reminders.
  - `integrations/`:
    - `finance.py`: Market quotes, price alerts that trigger once, hard code prohibitions against trading and suggestions.
    - `google_workspace.py`: Gmail and Google Calendar integration. Drafts only (never send), event creation only (never delete/edit).
    - `live_data.py`: Multi-source live data pipeline (Weather, Mutual Funds, Sports) with fallback to scraping labelled `source="scraped"`.
    - `news_briefing.py`: Tech news briefing aggregating Hacker News, TechCrunch, and The Verge.
    - `research.py`: Academic research sources (arXiv, Semantic Scholar, Crossref, Google Scholar fallback).
    - `doc_generator.py`: Document generation for Word, Excel, PowerPoint, and PDF.
  - `tools/`:
    - `integration_tools.py`, `memory_tools.py`, `automation_tools.py`, `file_tools.py`, `app_tools.py`.
  - `tests/`:
    - 52 passed unit and integration tests under `services/backend/tests/` (100% pass rate).

## Phase 6 Verification Results
| Requirement / Done Criterion | Specification | Empirical Evidence | Status |
| :--- | :--- | :--- | :---: |
| **Strict Sender Whitelisting** | Only owner Telegram user ID accepted; others silently ignored & logged | Message and callback from non-whitelisted sender `999999999` received zero replies and were recorded in `ignored_messages_log` | PASS |
| **Safety Engine Integration** | Remote commands run through Safety layer with `source="telegram"` | Actions executed with `source="telegram"`, recorded in action log, and governed by Risk Tiers | PASS |
| **Remote Approvals for Tier 1 & 2** | Previews sent with inline buttons; callback resolves confirmation | Approval message sent to owner; clicking inline "Approve" button resolved pending safety confirmation with exact preview | PASS |
| **Tier 3 Remote Prohibition** | Tier 3 cannot be approved remotely; requires physical typed desktop confirmation | Remote execution of Tier 3 actions raises `PermissionError("cannot be approved remotely")` and logs decision as blocked | PASS |
| **Remote Kill Switch** | `/halt` and `/kill` immediately trigger Guardian kill switch and confirm | Sending `/halt` triggered `guardian.trigger()`, halting tasks; bot replied with immediate halt confirmation; `/resume` restored operation | PASS |
| **Status, Tasks, & Logs Summaries** | Summaries provided on request with private content redacted | `/status`, `/tasks`, and `/logs` return structured summaries with sensitive arguments redacted | PASS |
| **Remote Lockout (`/lock`)** | Disables remote control until re-enabled at the desktop | `/lock` set `is_remote_locked()=True`; subsequent commands and `/unlock` from Telegram were refused; re-enabled only via physical desktop UI | PASS |
| **Credential Manager Security** | Bot token and owner ID stored in Windows Credential Manager | Stored under `Phenom/telegram-token` and `Phenom/telegram-owner-id` with zero plaintext secrets in code or git | PASS |

## Dependencies added
- None (uses existing `httpx` and `win32cred`).

## Known issues
- None. All Phase 6 done criteria met.

## Open questions for the user
- None for Phase 6.

## Next
Phase 7: Packaging, Polish, and Production Readiness. Installer, auto-start, tray icon, offline documentation, and final system integration verification.
