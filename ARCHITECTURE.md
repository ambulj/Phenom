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


---

## 14. Phase 4: Obsidian Vault, RAG & Media Governance (Locked In)
1. **Structured Engineering Daily Notes**: Daily notes formatted under ault/Daily Notes/YYYY-MM-DD.md containing ## 🎯 Focus & Goals, ## 🔨 Code & Commits, ## 🧠 Technical Learnings, and ## 📌 Follow-ups.
2. **Exact Wikilink Citations**: RAG and document question answering cites sources with exact clickable wikilinks (e.g. [[Architecture#L42]]).
3. **Read-Only Photo Indexing**: Photos in ~/Pictures indexed with EXIF metadata and local AI visual tags (receipt, diagram, screenshot) stored encrypted in SQLCipher; zero file edits/moves per Rule 6.
4. **Reversible Cleanup & Rollback Manifest**: Temporary/download cleanups move files to Windows Recycle Bin only (Rule 7), automatically generating a rollback manifest note in Obsidian.

---

## 15. Phase 5: Financial Feeds, Documents & Modes (Locked In)
1. **Financial Watchlist Invariants**: Informational tracking only (Rule 5: never trade, never suggest buy/sell). Features ±3% intraday swing threshold alerts and an automated 04:00 PM IST market closing digest.
2. **Curated Feeds**: News aggregation across Hacker News, ArXiv AI daily, GitHub Trending, and Indian business headlines.
3. **Modern Executive Document Styling**: Generated documents (.docx, .pptx, .xlsx, .pdf) formatted with modern executive aesthetics, crisp tables, and callouts.
4. **Adaptive Modes**: Work (code & witty banter), Study (deep technical rigor & ambient focus audio), and Chill (relaxed banter & media control).


---

## 16. Phase 6: Telegram Remote Bridge & Security Invariants (Locked In)
1. **Desktop PIN Handshake**: Pairing requires a single-use desktop QR code or 6-digit PIN handshake (/pair <PIN>), permanently binding Abhi's Telegram user ID.
2. **Remote Emergency Locking**: /lock or /halt triggers 
undll32.exe user32.dll,LockWorkStation and the Guardian kill switch, confirming back to Telegram.
3. **Interactive Inline Approvals**: Remote Tier 2 actions display an inline card with [✅ Approve] and [❌ Deny] with a 60-second expiration window.
4. **Redacted Screen Snapshots**: Remote /screen commands automatically redact passwords, credit cards, and OTPs.
5. **Full Duplex Voice**: Voice notes are transcribed locally with Whisper and replied to with spoken audio notes.

---

## 17. Phase 7: Packaging, Auto-Update & Resilience (Locked In)
1. **Dual Packaging**: Packaged as both an NSIS Windows installer (auto-start & uninstaller) and a portable unpacked application.
2. **Silent Background Updates**: Updates download silently in the background and apply upon idle restart with a 7-day automatic rollback window.
3. **Smart Watchdog Crash Recovery**: Process watchdog restarts crashed backend within 3 seconds, sanitizes memory dumps, and posts a notification in the HUD.
4. **Staged Wave Refactoring**: Large-scale codebase refactoring executes in dependency waves with git checkpoints and preview diffs.
5. **3-Way Conflict Detection**: Concurrent file modifications trigger an automated 3-way diff comparison in the HUD to prevent clobbering active edits.


---

## 18. Advanced Engineering Architecture (Locked In)
1. **5-Pillar Code Reviews**: PR reviews enforce security (secret/injection prevention), performance, null safety, test coverage, and typing integrity.
2. **Scientific Hypothesis Debugging**: Root-cause investigation follows a structured loop: Hypothesis formulation -> Minimal reproducible test -> Git bisect -> Patch proposal -> Regression verification.
3. **Database Tiered Safety**: Read-only SQL queries are Tier 0 auto-approved; DDL/DML mutations (UPDATE, DELETE, DROP) require Tier 2 confirmation with preview of affected rows.
4. **Environment Secret Masking**: Console stdout/stderr streams and action logs automatically intercept and mask values found in active .env files with [REDACTED_SECRET].
5. **In-Situ API Testing**: Integrated developer tooling to inspect local HTTP endpoints, validate headers/payloads, and scaffold mock test fixtures.

---

## 19. Daily Engineering Routines & Focus (Locked In)
1. **Interactive 3-Point Standup**: Morning briefings prioritize: 1. Top 3 daily objectives; 2. Calendar focus blocks; 3. Urgent PR reviews; followed by conversational priority selection.
2. **Full Engineering Wrap-Up**: Evening macro audits git repositories for uncommitted changes, appends a structured daily summary to Obsidian, reviews open checklists, and locks the workstation.
3. **50/10 Focus Sprints**: 50-minute deep-work sprints queue non-urgent notifications into a digest and alert on social/video distraction patterns.
4. **Obsidian Reading Queue**: 'Save paper/link' command extracts title, abstract, and tags into ault/Study/Reading List.md.
5. **Audio Completion Ping**: Tasks taking > 30 seconds trigger a soft Jarvis chime and a concise 1-sentence spoken completion summary.


---

## 20. Performance, Search & LoRA Adaptation Architecture (Locked In)
1. **Dynamic LoRA Adapters**: The local 8B model supports loading task-specific and personal coding LoRA adapter weights from ~/Documents/Phenom/lora/ without re-quantizing base weights.
2. **Native Ripgrep Integration**: Global code and symbol lookups execute via bundled native 
g.exe (< 10ms execution across > 100k lines), automatically respecting .gitignore.
3. **Partitioned Vector Namespaces**: Embeddings are segregated into partitioned collections (ault_notes, code_symbols, chat_facts, 
esearch_papers) for scoped cosine similarity retrieval.
4. **Benchmark & Latency Governance**: Test runtimes, VRAM peaks, and TTS latency metrics are logged to SQLite; any regression exceeding 15% triggers a diagnostic HUD card.

---

## 21. Voice, PTY & Desktop Interactivity Architecture (Locked In)
1. **Dual Wake-Word Activation**: Recognizes both 'Hey Phenom' and 'Jarvis' with a 0.65+ confidence threshold and 500ms sliding confirmation window.
2. **Local Quantized Whisper STT**: Offline voice transcription runs on local quantized Whisper (ase.en/small), providing instant speech-to-text without internet access.
3. **Dynamic Emotional TTS Modulation**: Speech cadence, pitch inflection, and tone adjust dynamically to context (celebratory on build success, crisp on alerts, calm on tutoring).
4. **Interactive PTY Console**: The streaming console supports full interactive pseudo-terminal (PTY) emulation for stdin keyboard forwarding.
5. **Windows 11 Virtual Desktop Switching**: Desktop control allows seamless voice navigation across virtual desktops (e.g. 'Switch to Code desktop').
6. **SemVer & Changelog Automation**: Milestones automatically parse conventional commit headers, calculate SemVer version bumps, and generate CHANGELOG.md.


---

## 22. Hardware Telemetry & LAN Architecture (Locked In)
1. **Passive LAN Discovery**: Local devices (NAS, Raspberry Pi, smart displays) are passively discovered via mDNS/SSDP under Tier 0 without intrusive active subnet scanning.
2. **Proactive Hardware Sensor Monitoring**: GPU/CPU temperatures, NVMe free space, and battery metrics are continuously checked; alerts fire in the HUD if GPU > 85°C, NVMe < 10GB, or battery < 15%.
3. **Bluetooth Audio Routing**: Headphone connections/disconnections auto-switch audio playback with volume ducking during Bluetooth handshakes; explicit voice commands can also switch outputs.

---

## 23. Multimodal Vision & Workspace Ergonomics (Locked In)
1. **Mermaid Diagram Reconstruction**: Architecture flowcharts, UML diagrams, and system schemas in screenshots/PDFs are automatically transcribed into executable mermaid markdown.
2. **Code Screenshot Reconstruction**: Code images from videos or tweets are OCR-transcribed, formatted with black/prettier conventions, and offered via 1-click insert in the HUD.
3. **Smart Port Conflict Remediation**: When a dev server encounters EADDRINUSE, Phenom identifies the holding PID via psutil, reveals the process in HUD, and offers 1-click kill or alternative port allocation.
4. **Command Palette Note Fuzzy Finder**: Typing #tag or [[note]] in the Command Palette (Alt+Space) provides instant fuzzy autocomplete and markdown note previews.
5. **Real-Time Streaming Dictation**: Offline continuous speech dictation streams transcribed text with auto-punctuation directly into the active cursor in any Windows application.

---

## 24. Search, Retrieval & Model Execution Optimization (Locked In)
1. **Hybrid SQLite FTS5 + Vector Search (RRF)**: Knowledge retrieval combines exact keyword matching via SQLite FTS5 and semantic vector embeddings via Reciprocal Rank Fusion (RRF) for optimal recall across technical code symbols and conversational notes.
2. **Dynamic Task-Adaptive Sampling**: Model decoding temperature adapts to intent: 0.1 for deterministic coding/tests, 0.3 for architectural research/study notes, and 0.7 for witty conversational banter.
3. **Sub-50ms Stream Cancellation**: Immediate cancellation of streaming LLM token generation and audio synthesis upon Escape tap, push-to-talk release, or barge-in trigger.
4. **Offline DevDocs Local Cache**: Core technical documentation (Python, FastAPI, React, PyTorch, TypeScript) is bundled in a local SQLite cache for instantaneous offline query resolution.
5. **Dynamic Prompt Biasing for Whisper**: Active workspace symbol tables, custom codenames, and recent git diff terminology are dynamically injected into Whisper's initial prompt to boost technical acronym transcription accuracy.
6. **Mathematical Formula Audio Pacing**: Mathematical equations in study mode are vocalized at a measured 0.85x speed with parallel KaTeX visual rendering in the desktop HUD.

---

## 25. System Ergonomics, Desktop Windows & Developer Toolchain (Locked In)
1. **Windows 11 Mica / Acrylic Translucency**: Desktop HUD, Command Palette, and Orb floating surfaces leverage Windows 11 Mica / Acrylic translucent glass materials with Electric Cyan and Stark Gold accents.
2. **Multi-Instance Desktop Support**: Multiple independent Phenom windows can run across distinct monitors without process mutex conflicts.
3. **Win32 Hotkey Collision Detection**: Global keyboard shortcuts (Alt+Space, Ctrl+Space) are pre-validated against registered OS hotkeys; collisions trigger HUD alerts with 1-click alternative keybinding suggestions.
4. **Git Pre-Commit Hook Integration**: Local repository commits automatically verify secret leakage and vault references via an automated pre-commit hook before committing.
5. **Monorepo-Aware Context Targeting**: File changes automatically scope context trees, linting, and unit test runners to the nearest package root rather than executing whole-repository sweeps.
6. **Refactoring Edit Locality Cap**: Automated code refactorings are capped at 150 modified lines per file per turn, preventing uncontrolled sweeping diffs and enforcing incremental atomic changes.
7. **Safe Auto-Stash on Branch Switching**: Switching git branches via voice or command palette automatically creates a timestamped stash and re-applies changes cleanly.
8. **Automated 'phenom doctor' Health Diagnostic**: A built-in CLI diagnostic inspects CUDA availability, GPU VRAM, Python/Node toolchains, Ollama status, and Windows Credential Manager integrity.

---

## 26. Ambient Controls, Power Governance & Continuous Learning (Locked In)
1. **Interactive Disambiguation via HUD**: When ambiguity arises (e.g. conflicting files or stashes), Phenom vocalizes a concise 1-sentence prompt while popping an interactive HUD card with keyboard shortcut targets (1, 2, 3) and clickable chips.
2. **Universal Media Controls (Win32 SMTC)**: System Media Transport Controls provide universal Play/Pause/Next/Volume key event synthesis across Spotify, YouTube, Chrome, and local players with browser session fallback.
3. **Smart AC/Battery Power Governor**: On AC power, background Telegram polling and notification monitoring remain active during screen lock; on battery or Modern Standby sleep, all polling loops and file watchers pause, restoring instantly upon user unlock.
4. **Instant Rules & Spaced Memory Learning**: When corrected by Abhi (e.g. preferring a specific linter or package manager), Phenom immediately commits the rule to a structured cache and injects the top-3 relevant rules into future prompt contexts.

---

## 27. Multi-Project Workspaces, Execution Shell & Dynamic Context Budgeting (Locked In)
1. **Seamless Project Workspace Transition**: Switching projects re-anchors the active workspace root, parses local `.phenom/prompt.md`, focuses or launches the corresponding VS Code window, and re-scopes Git/vector index namespaces dynamically.
2. **Clean UTF-8 PowerShell 7 Subprocess Execution**: Terminal commands run in an isolated `pwsh` session free from user `$PROFILE` side-effects, enforcing strict UTF-8 input/output encoding to eliminate Windows console encoding errors.
3. **Dual Automation Scheduling (Task Scheduler + APScheduler)**: Time-critical wake-from-sleep automations (e.g. 8:00 AM morning standup) register with Windows Task Scheduler, while in-session background loops utilize in-process APScheduler.
4. **Dynamic Context Budgeting & Hybrid Offloading**: The 8B local LLM defaults to an 8,192 token window, dynamically scaling to 16k/32k via RoPE scaling when analyzing large files (enforcing >=1.5 GB free GPU VRAM headroom), falling back to hybrid CPU/GPU offload for massive repositories.

---

## 28. AST Refactoring, Calibration & Ephemeral Privacy Architecture (Locked In)
1. **AST-Aware Semantic Refactoring**: Multi-file refactorings leverage `ast-grep` / tree-sitter for syntax-tree aware replacements rather than brittle regex, presenting an aggregated multi-file diff preview in the HUD before disk modification.
2. **Adaptive Acoustic False-Positive Calibration**: On accidental wake-word trigger, saying 'false trigger' or pressing Escape logs the 2-second pre-roll audio snippet to an encrypted local training dataset to fine-tune wake-word rejection.
3. **Ephemeral In-Memory Clipboard Buffer**: Clipboard history retains a maximum of 20 items in volatile RAM only, automatically scrubbed of API keys/passwords, and purged immediately on Windows lock or app shutdown.
4. **Permanent Obsidian Web Research Archive**: Scraped technical documentation and research articles are cleaned and saved permanently to `vault/Study/Web Research/YYYY-MM/` with source URLs, executive summaries, and key takeaways.

---

## 29. Multi-Agent Arbitration, Database Hygiene & Time-Aware Audio (Locked In)
1. **Chief Architect Synthesis**: When specialist subagents (Code Reviewer, Test Architect, Security Auditor) generate conflicting suggestions, Phenom synthesizes a unified recommendation balancing security and testability, presenting a single cohesive proposal in the HUD.
2. **Automated Weekly Vector Index Maintenance**: Every Sunday at 3:00 AM (or on next idle), the background engine vacuums SQLite/SQLCipher databases, prunes orphaned vector chunks from deleted files, and validates embedding integrity.
3. **Time-Aware Night Audio Mode**: After 11:00 PM, Phenom automatically attenuates TTS speech volume by 40%, adopts a softer, calm vocal cadence, and silences non-critical chimes.
4. **Fast-Forward Wave Merging with HUD Review**: Autonomous feature waves maintain individual atomic task commits on the branch, presenting a 1-click merge button in the HUD alongside a generated changelog summary.

---

## 30. Persona Presets, Context Notifications & File-Watcher Throttling (Locked In)
1. **Dynamic Persona Presets**: Phenom supports voice/HUD switching across three operational personas:
   - `tony_stark` (Default): High-energy, witty, banter-heavy lab partner (*"scene sorted hai"*).
   - `professor`: Deep technical rigor, formal mechanics, zero slang, high detail, and complete mathematical derivations.
   - `silent_copilot`: Strictly visual HUD diffs and test badges, quiet chimes, zero unsolicited dialogue.
2. **Context-Adaptive Build & Test Notifications**: When long-running builds or tests complete in the background:
   - If IDE/editor has OS focus: play subtle completion chime and update HUD status badge.
   - If another app/browser has OS focus: trigger native Windows 11 Action Center toast and speak a concise voice summary (*"Tests passed in 14s"*).
3. **Smart Ignore Patterns & 500ms Churn Debounce**: File watchers auto-ignore standard build directories (`.git`, `node_modules`, `target`, `.venv`, `dist`, `__pycache__`) and `.gitignore`, throttling change events with a 500ms debounce during heavy file churn.


