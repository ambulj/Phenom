# HANDOFF.md

Updated at the conclusion of Phase 1 (Core).

## Current phase
Phase 1: Core (COMPLETE)

## How to run
```bash
# 1. Run all tests (unit, safety, router, tools, memory, E2E WebSocket)
npm run test:backend

# 2. Typecheck and build the desktop UI
cd apps/desktop
npm run build
cd ../..

# 3. Start backend and desktop app together with a single command
npm run dev
```

## What exists
- `apps/desktop/`:
  - `electron/main.cjs`: Electron window host with global shortcut registration (`Ctrl+Alt+Pause` Guardian kill switch).
  - `src/App.tsx`: Central coordinator with WebSocket connection management, slide panel state, confirmation modal.
  - `src/components/Orb.tsx`: 3D Three.js particle orb (6,000 particles) with 5 states (calm blue, teal, violet, amber, red) and smooth corner shrink transition (< 450 ms).
  - `src/components/HeaderBar.tsx`: Fluent UI header with connection indicator, Guardian Kill Switch / Resume button, and navigation.
  - `src/components/ChatBox.tsx`: Centered input beneath the orb with streaming response bubble and cancel controls.
  - `src/components/ConfirmationModal.tsx`: Explicit security confirmation modal with tier badges and "Remember for this folder" checkbox for Tier 1.
  - `src/components/panels/`:
    - `HistoryPanel.tsx`: View persisted conversation turns.
    - `ActionLogPanel.tsx`: Security audit trail showing tier, tool, decision, and redacted arguments.
    - `LearnedRulesPanel.tsx`: View, edit, and delete learned rules.
    - `ApprovalsPanel.tsx`: View and manage remembered folder approvals.
    - `SettingsPanel.tsx`: Non-secret system settings, model architecture, and hotkey overview.
- `services/backend/`:
  - `main.py`: FastAPI server with typed WebSocket endpoint on `/ws`, confirmation Future resolver, and REST audit endpoints.
  - `schemas/protocol.py`: Typed Pydantic models for all messages and payloads.
  - `scripts/generate_types.py`: Automatic generator translating Pydantic schemas to TypeScript interfaces in `apps/desktop/src/types/protocol.ts`.
  - `safety/`:
    - `registry.py`: Strict tool registry requiring tier (0-3), preview function, and Pydantic schema.
    - `engine.py`: Central gateway enforcing the 4 security tiers, timeouts, confirmation flow, and blocking.
    - `guardian.py`: Guardian kill switch with process termination and halted state enforcement.
    - `approvals.py`: Persistent per-folder remembered approvals for Tier 1.
    - `action_log.py`: Action log with automatic redaction of confidential argument values.
  - `router/`:
    - `privacy.py`: Privacy classifier defaulting to private and inspecting paths/content.
    - `router.py`: Model routing engine directing private input to Local 8B and long shareable input to Cloud Nemotron after preview approval.
  - `tools/`:
    - `file_tools.py`: `list_files` (Tier 0), `read_file` (Tier 0), `search_files_by_name` (Tier 0), `create_file` (Tier 1), `copy_file` (Tier 1), `move_file` (Tier 1), `create_folder` (Tier 1), `recycle_delete` (Tier 2, send2trash).
    - `app_tools.py`: `list_apps` (Tier 0), `open_app` (Tier 1), `close_app` (Tier 1).
  - `memory/`:
    - `db.py`: Encrypted SQLCipher database manager using 256-bit key from Windows Credential Manager.
    - `rules.py`: Learned rules manager supporting add, list, edit, and delete.
  - `orchestrator/`:
    - `engine.py`: Conversational loop with Jarvis personality, tool-call interception, safety wrapping, and automatic persistence.
  - `tests/`:
    - `test_safety.py`: 5 safety layer unit tests.
    - `test_router.py`: 7 router & privacy classifier unit tests.
    - `test_tools.py`: 4 tool & safety bypass prevention tests.
    - `test_memory.py`: 2 encrypted memory and learned rules tests.
    - `test_e2e_chat.py`: 2 E2E WebSocket chat and kill switch tests.

## Decisions made
- **Safety First**: Implemented and verified the complete Safety layer and Guardian kill switch before implementing any tool.
- **Strict Typing**: Enforced bidirectional type parity by auto-generating `apps/desktop/src/types/protocol.ts` directly from `services/backend/schemas/protocol.py`.
- **Delete Means Recycle**: Used `send2trash` for all deletions so permanent deletes are impossible by construction.

## Dependencies added
- `@fluentui/react-components` (9.56.0) & `@fluentui/react-icons` (2.0.260): Microsoft Windows Fluent UI system for desktop app.
- `send2trash` (2.1.0): Native Windows recycle bin integration.
- `keyboard` (0.13.5): Global Windows hotkey hook for Guardian kill switch.
- `pytest-asyncio` (1.4.1): Async test runner for FastAPI WebSocket endpoints.

## Known issues
- Cloud model (Nemotron) awaits `NVIDIA_API_KEY` for live cloud streaming; local 4-bit Llama 3 handles all requests securely and reliably.

## Open questions for the user
- None for Phase 1. All done criteria are met.

## Next
Phase 2: Voice. Wake-word detection (openWakeWord), local Whisper STT (faster-whisper on CUDA), and male TTS (Windows SAPI5 Microsoft David) integrated into the live app.
