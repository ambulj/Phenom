# HANDOFF.md

Updated at the conclusion of Phase 4 (Long-Term Memory and File Search).

## Current phase
Phase 4: Long-Term Memory and File Search (COMPLETE)

## How to run
```bash
# 1. Run all backend tests (38 tests across safety, router, tools, memory, voice, automation, RAG)
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
    - `LiveViewPanel.tsx`: Live viewport frame stream, human takeover alert banner with "Continue" and "Stop" actions, and execution step list overlay.
    - `HistoryPanel.tsx`: View persisted conversation turns.
    - `ActionLogPanel.tsx`: Security audit trail showing tier, tool, decision, and redacted arguments.
    - `LearnedRulesPanel.tsx`: View, edit, and delete learned rules.
    - `ApprovalsPanel.tsx`: View and manage remembered folder approvals.
    - `SettingsPanel.tsx`: Wake phrase selector (`hey_jarvis`, `alexa`), mic privacy toggle, and global hotkeys editor (`alt+space`, `ctrl+alt+p`, `ctrl+alt+pause`) with real-time conflict error reporting.
- `services/backend/`:
  - `memory/`:
    - `db.py`: Encrypted SQLCipher database manager using 256-bit key from Windows Credential Manager. Stores `messages`, `facts`, `learned_rules`, `settings`, `embeddings`, and `photo_index`.
    - `doc_reader.py`: Multi-format document parser supporting PDF (`pypdf`), Word (`docx`), PowerPoint (`pptx`), Excel (`openpyxl`), Markdown, and plain text with overlap chunking.
    - `vector_store.py`: Local `all-MiniLM-L6-v2` dense embeddings, incremental indexing tracking `mtime`, encrypted storage in SQLCipher, and cosine similarity search with exact source attribution.
    - `vault.py`: Obsidian vault reader, writer, and daily log manager operating inside `vault/`.
    - `photo_indexer.py`: Photo metadata, EXIF properties, and descriptive tag indexing; hard prohibition preventing photo modifications.
    - `cleanup_organizer.py`: Downloads file categorization, duplicate detection via SHA-256, dry-run preview, and 100% reversible undo ledger.
    - `rules.py`: Learned rules manager supporting add, list, edit, and delete.
  - `orchestrator/`:
    - `engine.py`: Conversational loop with Jarvis personality, automatic user-correction rule extraction, RAG memory context injection with source citations, safety wrapping, and automatic persistence.
  - `tools/`:
    - `memory_tools.py`: `search_memory` (Tier 0), `search_photos` (Tier 0), `index_folder_documents` (Tier 0), `vault_read_note` (Tier 0), `summarize_long_document` (Tier 0), `organize_downloads_dry_run` (Tier 0), `vault_write_note` (Tier 1), `vault_append_daily_log` (Tier 1), `organize_downloads_apply` (Tier 1), `undo_cleanup` (Tier 1), `modify_photo` (Tier 3 - BLOCKED), `delete_photo` (Tier 3 - BLOCKED).
    - `automation_tools.py`: Browser and desktop automation tools.
    - `file_tools.py` & `app_tools.py`: Core file and application tools.
  - `automation/`:
    - `human_takeover.py`, `limits.py`, `desktop_controller.py`.
  - `browser/`:
    - `browser_controller.py`, `cart_automator.py`, `youtube_summarizer.py`.
  - `voice/`:
    - `wake_word.py`, `stt.py`, `tts.py`, `hotkeys.py`, `voice_coordinator.py`.
  - `safety/`:
    - `registry.py`, `engine.py`, `guardian.py`, `approvals.py`, `action_log.py`.
  - `tests/`:
    - 38 passed unit and integration tests under `services/backend/tests/` (100% pass rate).

## Phase 4 Verification Results
| Requirement / Test | Requirement | Empirical Result | Status |
| :--- | :--- | :--- | :---: |
| **Vector Index & Retrieval Quality** | Dense embeddings, sources cited | Returns exact filename, snippet, and cosine score for quantum & baking docs | PASS |
| **Incremental Indexing** | Skip unmodified files based on mtime | Re-indexing unmodified folder skips 100% of unchanged files | PASS |
| **Obsidian Vault Integration** | Markdown notes & daily logs in `vault/` | Notes written with frontmatter, read cleanly, daily logs appended with timestamps | PASS |
| **Photo Immutability Rule** | Move, rename, edit, delete blocked | `modify_photo`, `delete_photo`, and code methods throw `PhotoModificationProhibited` | PASS |
| **Photo Indexing & Search** | Local EXIF/tag extraction & search | Search by natural language description returns matching photo with metadata | PASS |
| **Downloads Cleanup & Dry Run** | Categorization, duplicate check, preview | Generates dry-run plan without moving files; detects exact SHA-256 duplicates | PASS |
| **100% Reversible Cleanup Undo** | Rollback moves using undo token | `undo_cleanup` restores 100% of moved files back to original locations | PASS |
| **Learned Rules Auto-Extraction** | Extract rules from user corrections | Automatically extracts rules from "Never ...", "Always ...", and saves to DB | PASS |
| **Multi-Format Document Parsing** | PDF, DOCX, PPTX, XLSX, TXT, MD | All 6 document formats parsed into text and chunked with overlap | PASS |

## Dependencies added
- `python-docx` (1.2.0): Word document parsing.
- `python-pptx` (1.0.2): PowerPoint presentation parsing.
- `sentence-transformers` (6.2.0): Dense local vector embeddings (`all-MiniLM-L6-v2`).

## Known issues
- None. All Phase 4 done criteria met.

## Open questions for the user
- None for Phase 4.

## Next
Phase 5: Modes, Scheduler, and Integrations. Three assistant operating modes (Work, Study, Chill), background scheduler for recurring tasks and reminders, Gmail/Google Calendar integrations, and financial watchlist tracking.
