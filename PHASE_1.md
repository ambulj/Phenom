# PHASE 1: Core

## Objective
A working chat assistant with the orb, the model router, file and app tools, and a safety layer that cannot be bypassed.

## Read first
AGENTS.md, ARCHITECTURE.md, SAFETY.md, PERSONALITY.md, SPIKES.md (use its recommendations).

## Build order (do not skip ahead)

### Step 1: Scaffold
- Create the repo layout from AGENTS.md section 3.
- Backend: Python 3.11+, FastAPI, Pydantic, pytest, ruff, mypy or pyright.
- App: Electron + React + Vite + TypeScript strict, Fluent UI, ESLint, Prettier, Vitest.
- One command (`npm run dev` at the root) starts backend and app together.
- Generate TypeScript types from the Pydantic message schemas.

### Step 2: Safety layer FIRST
- Implement the tool registry: a tool cannot register without a tier, preview, and schema.
- Implement the classifier, confirmation flow, remembered approvals, and the action log exactly as in SAFETY.md.
- Implement the Guardian: UI button, global hotkey (default Ctrl+Alt+Pause), force-termination of child processes, state `halted`, Resume button.
- Unit tests for each tier, timeouts, denial, remembered approvals, and kill switch.

### Step 3: Backend and protocol
- Typed WebSocket protocol from ARCHITECTURE.md section 4.
- Streaming chat with cancellation.
- Orchestrator loop: prompt build, model call, tool-call loop, final reply.

### Step 4: Model router
- Local 8B via the runtime chosen in SPIKES.md.
- Cloud Nemotron via NVIDIA API.
- Routing rules from ARCHITECTURE.md section 3; privacy labels from SAFETY.md section 7 (automatic rules plus manual override in the UI).
- Approval dialog with the exact-text preview and "remember for this folder" (shareable folders only).
- Log every decision with the reason.

### Step 5: Tools (all behind the Safety layer)
| Tool | Tier |
| --- | --- |
| list_files, read_file, search_files_by_name | 0 |
| create_file, copy_file, move_file, create_folder | 1 |
| recycle_delete | 2 |
| list_apps | 0 |
| open_app, close_app | 1 |
Each has a preview and, where reversible, an undo.

### Step 6: Memory
- SQLCipher DB with the tables in ARCHITECTURE.md section 6 that this phase needs (`messages`, `facts`, `learned_rules`, `approvals_remembered`, `action_log`, `settings`).
- Auto-save after every task: summary, new facts, and any rule learned from a correction.
- UI list of learned rules with edit and delete.

### Step 7: UI
- Orb-first minimal view: orb centred, chat box beneath.
- Panels slide in on demand: chat history, action log, approvals, settings, learned rules. The orb shrinks to a corner icon while a panel is open.
- Orb states and colours per ARCHITECTURE.md section 5.
- Confirmation dialog and preview as in SAFETY.md section 3.
- Follow the Windows light or dark theme.

### Step 8: Personality
- System prompt from PERSONALITY.md. Warn once about risky requests, then follow the decision.

## Tests
- Router: private input never goes to the cloud; long shareable input requests approval first.
- Safety: every tier behaves as specified; a tool cannot run without passing the Safety layer (test by trying to call it directly).
- Kill switch: stops a long-running tool and a model stream in under 1 second.
- Log: contains no secrets or file contents.
- End-to-end: chat over the WebSocket with a tool call and a confirmation.

## Done criteria
- [ ] Chat streams and the orb reflects every state
- [ ] Router picks local or cloud correctly; preview approval appears before any cloud call
- [ ] File and app tools work; every call is logged with its tier
- [ ] Kill switch halts everything in under 1 second
- [ ] Memory persists across restarts and the database is encrypted
- [ ] Learned rules can be listed, edited, and deleted
- [ ] SAFETY.md audit checklist all checked

## Out of scope
Voice, browser or screen control, RAG, integrations, Telegram, installer.

## Finish
Follow the finish protocol in AGENTS.md section 7 and stop.
