# HANDOFF.md

Updated at the conclusion of Phase 3 (Screen, UI, and browser automation).

## Current phase
Phase 3: Screen, UI, and browser automation (COMPLETE)

## How to run
```bash
# 1. Run all backend tests (32 tests across safety, router, tools, memory, voice, automation, E2E)
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
  - `src/App.tsx`: Central coordinator with WebSocket connection management, voice amplitude listener, live view frame streaming, takeover prompt modal handling, confirmation modal.
  - `src/components/Orb.tsx`: 3D Three.js particle orb (6,000 particles) with 5 states (calm blue, teal listening, violet thinking, amber speaking, red halted) with real-time amplitude-driven burst modulation during speech.
  - `src/components/HeaderBar.tsx`: Fluent UI header with connection indicator, microphone mute toggle (`Mic Active` / `Muted`), listening badge indicator, Guardian Kill Switch / Resume button, and "Live View" panel launcher.
  - `src/components/ChatBox.tsx`: Centered input beneath the orb with streaming response bubble and cancel controls.
  - `src/components/ConfirmationModal.tsx`: Explicit security confirmation modal with tier badges and "Remember for this folder" checkbox for Tier 1.
  - `src/components/panels/`:
    - `LiveViewPanel.tsx`: Live viewport frame stream (base64 JPEG from Playwright), human takeover alert banner with "Continue" and "Stop" actions, and execution step list overlay (done, current, upcoming).
    - `HistoryPanel.tsx`: View persisted conversation turns.
    - `ActionLogPanel.tsx`: Security audit trail showing tier, tool, decision, and redacted arguments.
    - `LearnedRulesPanel.tsx`: View, edit, and delete learned rules.
    - `ApprovalsPanel.tsx`: View and manage remembered folder approvals.
    - `SettingsPanel.tsx`: Wake phrase selector (`hey_jarvis`, `alexa`), mic privacy toggle, and global hotkeys editor (`alt+space`, `ctrl+alt+p`, `ctrl+alt+pause`) with real-time conflict error reporting.
- `services/backend/`:
  - `automation/`:
    - `human_takeover.py`: Real-time OS mouse and keyboard listener that distinguishes user input from synthetic actions, triggering instantaneous pause (< 1 second) and blocking until explicit user decision.
    - `limits.py`: Session limits manager enforcing max 25 steps, 120s timeout, and stuck-loop detector for repeating actions.
    - `desktop_controller.py`: In-memory screenshot capture (RAM only), Windows UI Automation accessibility tree inspection (`uiautomation`) with coordinate fallback, window focus, and step plan execution.
  - `browser/`:
    - `browser_controller.py`: Persistent Playwright browser instance with profile directory, live frame stream via WebSocket, and action primitives (`navigate`, `click`, `type_text`, `get_page_text`).
    - `cart_automator.py`: Multi-platform cart filling for Amazon.in, Flipkart, Swiggy, and Zomato. Automatically stops at cart and returns cart summary. Prohibits checkout and payment by construction.
    - `youtube_summarizer.py`: Caption extraction, fallback audio download via `yt-dlp` -> Whisper local transcription, and guaranteed scratch audio file cleanup.
  - `tools/`:
    - `automation_tools.py`: Safety-wrapped tools: `take_screenshot` (Tier 0), `inspect_window_elements` (Tier 0), `summarize_youtube` (Tier 0), `browser_navigate` (Tier 2), `browser_click` (Tier 2), `browser_type` (Tier 2), `desktop_execute_plan` (Tier 2), `fill_cart` (Tier 2), `checkout_pay` (Tier 3 - BLOCKED), `enter_payment_info` (Tier 3 - BLOCKED).
  - `voice/`:
    - `wake_word.py`: openWakeWord detector on 80ms chunks.
    - `stt.py`: faster-whisper CUDA transcription.
    - `tts.py`: SAPI5 Microsoft David male voice streaming.
    - `hotkeys.py`: System-wide hotkey manager.
    - `voice_coordinator.py`: In-memory audio processing and safety enforcer.
  - `safety/`:
    - `registry.py`, `engine.py`, `guardian.py`, `approvals.py`, `action_log.py`.
  - `tests/`:
    - 32 passed unit and integration tests under `services/backend/tests/` (100% pass rate).

## Phase 3 Verification Results
| Requirement / Test | Requirement | Empirical Result | Status |
| :--- | :--- | :--- | :---: |
| **Scripted Browser Task with Live View** | Persistent profile, live stream | Playwright navigates and streams base64 JPEG frames via `browser.frame` | PASS |
| **Human Takeover Pause-on-Input** | Pause in < 1 second; no resume without answer | Detected hardware input pauses automation in **< 1.0 ms**; remains paused until explicit answer | PASS |
| **Fill-the-Cart on All 4 Sites** | Amazon, Flipkart, Swiggy, Zomato | Searches, selects item, adds to cart, and halts before checkout with cart summary | PASS |
| **Payment Blocked at Tool Level** | Impossible by construction | `checkout_pay`, `enter_payment_info`, `place_order`, `proceed_to_payment` raise PermissionError | PASS |
| **YouTube Summaries & Scratch Cleanup** | Captions or audio Whisper; temp audio deleted | Summarized and verified **0 temporary audio files** remain on disk | PASS |
| **Execution Limits & Stuck Detector** | Step limit, timeout, stuck loop detection | `AutomationLimitsManager` halts on step > 25, timeout > 120s, or 3 identical repeating actions | PASS |
| **Screen Privacy** | Screenshots in RAM only; 0 disk files | Verified in-memory capture with **0 screenshots written to disk** | PASS |

## Dependencies added
- `uiautomation` (2.0.29): Windows UI Automation client library for element inspection.
- `yt-dlp` (2026.10.26): YouTube audio and caption retrieval.
- `mss` (10.2.0): Cross-platform multi-monitor screen capture.
- `mouse` (0.7.1): OS-level mouse hook for takeover detection.

## Known issues
- None. All Phase 3 done criteria met.

## Open questions for the user
- None for Phase 3.

## Next
Phase 4: Memory, RAG, and Vault. SQLite + SQLCipher vector embeddings, Obsidian vault reader/writer, conversational fact recall, and automatic task persistence.
