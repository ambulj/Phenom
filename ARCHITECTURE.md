# ARCHITECTURE.md

## 1. Components
```
Electron app (React + Fluent UI + Three.js orb)
   |  WebSocket (typed JSON messages)
FastAPI backend
   |-- Orchestrator: conversation loop, tool-call loop
   |-- Router: local 8B vs cloud Nemotron
   |-- Safety layer: classify, confirm, log, kill switch (Guardian)
   |-- Tools: files, apps, browser, screen, documents, integrations
   |-- Memory: SQLCipher DB, vector index, Obsidian vault
   |-- Voice: wake word, STT, TTS
   |-- Scheduler: modes, recurring tasks
   |-- Telegram bridge (Phase 6)
```

## 2. Request flow
1. Input arrives (typed, voice, Telegram, scheduler) and is tagged with its source.
2. The orchestrator builds the prompt: system prompt (PERSONALITY.md), relevant memory, learned rules, current mode.
3. The Router picks the model (rules below) and streams tokens to the UI.
4. If the model asks for a tool, the call goes to the Safety layer: classify, preview, confirm if needed, log, run, log result.
5. Tool results return to the model; the loop continues until a final reply.
6. After the task, memory is saved automatically (summary, facts, learned rules).

## 3. Router rules
| Condition | Model | Handling |
| --- | --- | --- |
| Default (simple tasks, non-private) | Local 8B | Local inference, zero data departure |
| Non-private content exceeding local context/quality limit, or when VRAM is full | Cloud Nemotron (build.nvidia.com) | Automatic escalation with UI notice ("sent to cloud") and action log entry |
| Private content (files, email, calendar, contacts, screen, PII, keys, banking/financial, OTPs) | Local 8B (strictly required) | Kept on device; NEVER sent to cloud without explicit previewed approval |
| Borderline / Uncertain privacy classification | Local 8B (default) | Prompt owner to approve or keep local before sending |
| Cloud unreachable or rate limited | Local 8B fallback with chunking | Transparently surfaced to user and logged |

### Privacy Classification & Escalation Specification
- **Definition of Private Content**: Any data from the owner's files, email, calendar, contacts, or screen; PII (names, phone numbers, addresses, government IDs like Aadhaar/PAN); secrets (API keys, passwords, OTPs, financial/banking numbers); and voice transcripts matching any of these criteria.
- **Two-Stage Classifier**:
  1. *Rule-Based Fast Path*: Regex patterns detecting IDs, credit cards, bank accounts, UPI IDs, phone numbers, email addresses, file paths, API keys, and screen capture contexts.
  2. *Local Model Verification*: When regex is clean but content context is ambiguous, the local 8B model performs classification.
  3. *Uncertainty Rule*: If classification confidence is below threshold, fail-safe to "ask the owner" or run locally.
- Every routing and escalation decision is recorded in the action log with its specific rationale.

## 4. WebSocket protocol & API Security
All WebSocket messages have `id`, `type`, `ts`.
- UI to backend: `chat.send`, `chat.cancel`, `confirm.reply`, `settings.update`, `killswitch.trigger`, `mode.set`
- Backend to UI: `chat.token`, `chat.done`, `state.change` (idle|listening|thinking|speaking|halted), `tool.request`, `confirm.request`, `log.entry`, `rules.updated`, `error`
Define each as a Pydantic model in the backend and a TypeScript type in the app, generated from one schema so they never drift.

### Connection & Authentication Specification
1. **Session Token**: At launch, Electron generates a cryptographic 32-byte hex token in `apps/desktop/electron/main.cjs` passed to the Python backend via environment variable `PHENOM_SESSION_TOKEN`. It is exposed to the renderer only via `window.phenom.getSessionToken()` through a contextBridge preload script. It is never logged or stored in localStorage.
2. **WebSocket Handshake Auth**: The client must supply the token in the `Sec-WebSocket-Protocol` header formatted as `phenom.<token>` (e.g. `new WebSocket('ws://127.0.0.1:8000/ws', ['phenom.' + token])`).
   - The backend validates the token using `hmac.compare_digest` before calling `websocket.accept()`.
   - On mismatch, missing token, or unset `PHENOM_SESSION_TOKEN`, the socket is closed immediately with code `4401` and no state/data is sent.
   - Sockets failing authentication 5 times within 60 seconds from the same peer IP are immediately closed.
3. **Origin Validation & CORS**:
   - Packaged app origins allowed: `file://`, `null` (Chromium file:// origin), `vscode-file://`, `electron://`.
   - Dev origins (`http://localhost:5173`, `http://127.0.0.1:5173`) are permitted only when `PHENOM_DEV=1`.
   - All other origins (e.g. web pages running in standard browsers) are rejected with code 4401.
   - CORS `allow_credentials` is `False`.
4. **Broadcast Isolation**:
   - `active_websockets` checks an `authenticated` flag on the socket connection. Sensitive broadcasts (`confirm.request`, `log.entry`) are strictly isolated to authenticated sockets.
5. **REST Security**:
   - All REST routes under `/api/*` require `Authorization: Bearer <token>`.
   - The `/health` and `/api/health` endpoints are unauthenticated and return only `{"status": "ok"}` with no environment, path, or configuration metadata.

## 5. Orb states
| State | Colour | Particle behaviour |
| --- | --- | --- |
| idle | calm blue | slow drift, low density motion |
| listening | teal | gentle pulse toward the centre |
| thinking | violet | swirl around the core |
| speaking | amber | bursts timed to speech amplitude |
| halted | red | frozen, dim |
Panel open: the orb shrinks to a corner icon with the same colour and a small animation.

## 6. Memory
Tables: `messages`, `facts`, `learned_rules`, `approvals_remembered`, `action_log`, `watchlist`, `schedules`, `file_index`, `settings`. Encrypted with SQLCipher; the key is in Credential Manager under `Phenom/db-key`. The vector index is stored in the same encrypted store or an encrypted file beside it. The Obsidian vault is plain Markdown in `vault/`.

## 7. Configuration
`config.toml` for non-secret settings (hotkeys, folders, model names). Secrets only in environment variables or Credential Manager. A settings panel writes to config and never displays secrets.


---

## 8. Developer & Coding Agent Architecture (Locked In)
1. **Subprocess Execution**: Commands run via PowerShell 7 (pwsh.exe) with fallback to Windows PowerShell 5.1, isolated inside workspace directories with path containment and execution timeout limits.
2. **Autonomous Pre-Push Quality Gate**: Before preparing a Pull Request, the agent runs test suites, linting, and the zero-secrets scanner locally.
3. **Smart Dev Clipboard**: Clipboard monitoring auto-detects stack traces, JSON, regex, and Git repository URLs, presenting 1-click actions in the desktop HUD.
4. **Failure-Triggered Screen Sampling**: Contextual screen OCR snapshots are taken automatically on terminal test/build failure or IDE syntax error highlights.
5. **Proactive Patch Remediation**: When a build or test fails, the agent analyzes the traceback, drafts a minimal fix diff in the HUD, and waits for 1-click user approval.

---

## 9. Multimodal Remote & Voice Architecture (Locked In)
1. **Barge-in Performance**: Spoken output supports immediate barge-in interruption (< 50ms) via speech recognition or push-to-talk (Ctrl+Space).
2. **Audio Ducking**: Active media volume is automatically ducked by 70% during TTS synthesis or speech input, and restored when idle.
3. **Telegram Multimodal Bridge**: Remote channel processes voice audio notes via local Whisper, responds with audio notes, and inspects attached photos/documents via vision.
4. **Emergency Stop**: Guardian Kill Switch is hard-wired to Triple-tap Escape as well as the UI emergency halt button.

---

## 10. RAG, Storage & Disaster Recovery Architecture (Locked In)
1. **Local Vector Search**: Embedded using local ONNX runtime (ll-MiniLM-L6-v2), running on CPU in < 5ms with zero GPU VRAM consumption.
2. **Daily Encrypted Snapshots**: Automatic daily local backup ZIP archiving SQLite memory, Obsidian vault, and configuration to ~/Documents/Phenom/backups/ with 30-day retention.
3. **Transient Data Purge**: Temporary browser profiles, OCR temp images, and screen caches are auto-purged after 7 days; audit action logs are retained indefinitely.


---

## 11. Multi-Agent Subagent Specialist Architecture (Locked In)
1. **Specialist Subagents**: For complex multi-step coding or refactoring challenges, Phenom coordinates specialized subagent roles (Test Architect, Code Reviewer, Security Auditor, Docs Writer).
2. **Synthesis & Alignment**: Each subagent executes within isolated read-only or workspace sandboxes, and Phenom synthesizes their findings into an executable plan before modifying code.
3. **Test-Driven Pairing**: Every newly authored module or feature is accompanied by matching automated tests (pytest / jest) covering happy paths and boundary edge cases.

---

## 12. Desktop UX & Command Architecture (Locked In)
1. **Raycast / Spotlight Palette (Alt+Space)**: Pressing the global summon hotkey reveals a centered glassmorphic command bar for instant app launching, file search, and natural chat.
2. **Dynamic Screen Border Accent**: A sleek border overlay (ScreenBorderOverlay.tsx) pulses Electric Cyan while listening/thinking, Amber on Tier 2 confirmation checkpoints, and Stark Crimson on Guardian emergency halt.
3. **Integrated HUD Audit Drawer**: 1-click access from the HUD card or command palette to inspect the chronological action log, tool risk tiers, routing rationale, and rollback points.
4. **Collapsible Streaming Console**: Live stdout/stderr output from test runs, builds, or scripts streams in real-time inside a collapsible syntax-highlighted terminal drawer.

---

## 13. Context Management & Dual Escalation (Locked In)
1. **Auto-Compaction**: When conversations reach 80% of local context capacity, older turns are automatically summarized into structured facts and semantic memory.
2. **Cloud Nemotron Rollover**: For ultra-long context operations (such as multi-file repository diffs or massive build logs), Phenom escalates to Cloud Nemotron's 128k context window, keeping privacy invariants intact.
