# SAFETY.md: risk tiers and safety rules



This file is the contract for the Safety layer. The code enforces it; this document must always match the code. Update it whenever a tool is added or changed.



## 1. Risk tiers

| Tier | Name | Behaviour | Examples |

| --- | --- | --- | --- |

| 0 | Read-only | Runs automatically, logged | list files, read a file, search memory & vector store, search photos, inspect UI elements, take screenshot (RAM), summarize YouTube, organize Downloads dry run, get mode, list scheduled jobs, get weather, get tech news, get market quote, get financial watchlist, get mutual fund quote, get sports score, search research papers, lookup DOI citation, search/read Gmail, list calendar events |

| 1 | Reversible change | One confirmation; user may choose "remember for this folder" | create or move or copy a file, open or close an app, organize Downloads apply (reversible with undo), write Obsidian vault note, append daily log, set mode, schedule reminder, cancel scheduled job, add/remove financial watchlist, create Gmail draft, generate document (.docx, .xlsx, .pptx, .pdf) |

| 2 | Destructive or external | Explicit confirmation with a preview of exactly what will happen; never remembered | recycle-bin delete, create a calendar event, send content to a cloud model, drive the browser or screen, fill a web cart, desktop action plans, remote approvals |

| 3 | Blocked or system-level | Blocked by default; allowed only if listed in section 6; needs a typed confirmation on the desktop; cannot be approved remotely | modify/delete photos, payments, checkout completion, OTP entry, permanent delete, changing system settings, sending email, editing or deleting calendar events, financial trading/orders, financial advice/recommendations, touching credentials, installing software |



Unknown tools or unclassified calls are Tier 3.



## 2. Tool declaration

Every tool declares: `name`, `tier`, `description`, a Pydantic argument schema, `preview(args)` (a human-readable description of the effect), and `undo(args, result)` when reversible. A tool without a tier cannot be registered.



## 3. Confirmation dialog

- Shows: what Phenom wants to do, the tool, the exact arguments, the tier, and a preview (for example the list of files to be moved with old and new paths, or the ordered steps in an automation plan).

- Buttons: Approve, Deny, and (Tier 1 only) "Approve and remember for this folder".

- Timeouts: no answer within 2 minutes counts as Deny.

- Remembered choices are listed in Settings with a revoke button. They never apply to Tier 2 or 3, and never outside the chosen folder.

- **Voice Safety Guarantee**: Voice requests are marked `source="voice"`. Destructive (Tier 2) and reversible (Tier 1) actions strictly require an on-screen visual confirmation dialog; spoken "yes" or voice affirmations are categorically refused by safety code.

- **Automation Takeover**: Physical user mouse or keyboard input during automated desktop/browser tasks triggers an instant pause (< 1 second). Automation will never resume without an explicit user answer (`continue` or `stop`).

- **Telegram Remote Approvals**: Tier 1 and Tier 2 actions may be approved over Telegram by the whitelisted owner ID, presenting the exact same preview as on the desktop. Tier 3 actions are permanently prohibited from remote approval and require physical typed desktop confirmation.

- **Telegram Whitelist & Lock Guarantee**: Messages or callbacks from non-whitelisted user IDs are silently ignored and logged. The `/lock` command disables remote control until physically re-enabled at the desktop application.



## 4. Action log

SQLite table `action_log`, one row per attempted action:

`id, timestamp, source (desktop|voice|telegram|scheduler), tool, tier, arguments_redacted, decision (auto|approved|denied|blocked|timeout), result_status, error, undo_token`

- Arguments are redacted: no file contents, email bodies, passwords, keys, or payment details.

- The UI log panel supports filter, search, export, and "Undo" where an undo token exists.



## 5. Guardian kill switch

- UI button and a global hotkey (default Ctrl+Alt+Pause, editable).

- On trigger: cancel the running model stream, abort every running tool, close automation sessions, stop speech and listening, set state to "halted", log the event.

- Works even if the model or a tool is hung (runs in its own thread or process and force-terminates child processes).

- After a halt Phenom does nothing until the user clicks Resume.



## 6. Tier 3 allowlist

Empty by default. Anything added needs the user's written approval and a line here: tool, reason, date.

Permanently blocked without allowlist entries: `modify_photo`, `delete_photo`, `checkout_pay`, `enter_payment_info`, `send_email`, `calendar_delete_event`, `calendar_edit_event`, `place_trade`, `suggest_trade`.



## 7. Privacy labels and cloud escalation

- Labels: `private` (default) or `shareable`.

- Automatic rules: anything in Documents, Desktop, Photos, Mail, Obsidian vault (`vault/`), financial, medical, ID or credential-looking content is `private`. Files in a folder the user marks shareable, and public web content, are `shareable`. The user can override any label in the UI.

- Local first: all requests start on the local model.

- Cloud escalation only when ALL are true: the input is `shareable`, it is too long or too hard for the local model, and the user approved after seeing a preview.

- Preview shows: which model, the exact text or the file excerpts that will be sent, the size, and the reason for escalation.

- "Remember for this folder" is allowed for shareable folders only.

- Every escalation is logged with what was sent (redacted) and the reason.



## 8. Hard prohibitions (enforced in code)

- No trades, no buy or sell suggestions, no financial advice phrasing. Informational market quotes and single-trigger price alerts only.

- No sending email. Phenom may only save email drafts for user review.

- No calendar deletion or editing of existing events. Creating new events is permitted under Tier 2.

- No photo move, rename, edit or delete. Photos are indexed and searched only.

- No permanent delete. Delete means Recycle Bin (`send2trash`).

- No payment, checkout completion, entering card data, or OTP submission. Fill-the-cart stops unconditionally before checkout.

- No typing or storing passwords.

- No audio stored on disk; no audio sent to the cloud. Audio is processed strictly in-memory (RAM) and discarded immediately. Temporary YouTube audio scratch files are guaranteed deleted after transcription.

- Screenshots are processed in RAM only, analyzed locally, and never sent to the cloud or saved without explicit user instruction.

- Spoken "yes" never approves Tier 1 or Tier 2 actions.

- No remote approval for Tier 3 actions; Tier 3 must be confirmed with typed confirmation on the desktop.

- Telegram bot messages from non-whitelisted user IDs are silently ignored and logged; zero replies sent to unauthorized users.

- Remote control can be locked at any time via /lock and cannot be unlocked from Telegram.



## 9. Audit checklist (run at the end of Phases 1, 2, 3, 4, 5, 6, 7)

- [x] Every registered tool has a tier, preview and tests

- [x] No code path calls a tool without the Safety layer

- [x] Kill switch works from UI, hotkey, voice, and Telegram (when present)

- [x] Spoken confirmation cannot approve destructive or reversible actions (on-screen confirmation enforced)

- [x] Zero audio files written to disk (in-memory RAM processing verified)

- [x] Payment and checkout completion are impossible by construction (Tier 3 blocked)

- [x] Screenshots processed in RAM only (zero saved without instruction)

- [x] Photos are untouched by construction; modify and delete are Tier 3 blocked

- [x] Downloads cleanup is 100% reversible via undo token

- [x] Vector embeddings and memory stored encrypted at rest in SQLCipher

- [x] Human takeover pauses automation within 1 second and never resumes without explicit answer

- [x] Sending email is blocked in code and classified Tier 3

- [x] Calendar event deletion and editing are blocked in code and classified Tier 3

- [x] Placing trades and offering buy/sell suggestions are blocked in code and classified Tier 3

- [x] Financial watchlist alerts trigger once without spamming

- [x] Live data pipeline falls back to scraping when API fails and is explicitly labelled

- [x] Generated documents (.docx, .xlsx, .pptx, .pdf) open and parse correctly

- [x] Telegram bot strictly accepts owner user ID only; non-whitelisted senders silently ignored and logged

- [x] Telegram remote approvals work for Tier 1 and Tier 2 with preview

- [x] Tier 3 actions are categorically refused remotely

- [x] Telegram /halt command halts running tasks immediately

- [x] Telegram /lock command disables remote control until re-enabled at the desktop

- [x] Nothing private reaches the cloud or Telegram without a previewed approval

- [x] Log contains no secrets, credentials, or private content

- [x] Every prohibition in section 8 has a test

- [x] Installer bundles UI and backend with prerequisites check

- [x] First-run wizard configures English voice, API keys, safe hotkeys, and indexing boundaries

- [x] Auto-start with Windows, system tray icon, and quiet background start verified

- [x] Auto-update with automatic rollback on boot failure verified

- [x] Crash reporter operates strictly local-only with private path and secret redaction

- [x] System resource benchmark complete: idle CPU 0.0%, RAM 211.9 MB, wake word 3.2% CPU



## 10. Confirmation Invariants, Safe Mode & Privacy Controls (Hardening Pass 2)

- **One-Line Confirmation Invariant**: Every confirmation dialog and Telegram push must generate a single descriptive summary string: `"[Tier {tier}] {action_verb} {item_count} item(s) in {target_summary}"`. Ambiguous or blind prompts are rejected by construction.

- **Preconditions Re-Validation**: Stale approvals are re-validated before execution: file SHA-256 hashes and mtimes, system mode, and Guardian killswitch state must match the state at issuance.

- **Safe Alternative Invariant**: When an action is declined, safe alternatives must have a risk tier $\le$ the declined action's tier, must never repeat a declined tool in the turn chain, and are blocked if the context is tainted (`is_tainted=True`).

- **Meeting Mode & Screen Exclusion**: When video conferencing tools are active, Phenom automatically applies `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` (0x00000011) to hardware-exclude Phenom windows from capture, mutes voice/sound FX, and silences notifications.

- **Safe Mode**: Startup flag `--safe-mode` restricts tool execution strictly to Tier 0 read-only tools, forces local inference, and blocks automation and cloud endpoints. A rolling 7-day rollback snapshot protects against boot failure.

- **Daily Self-Check**: Runs at 04:00 AM checking disk space (< 2 GB alert), database integrity, vault sync, rule SHA-256 verification, and model status, reporting sanitized summaries to Telegram and reserving spoken alerts for critical integrity failures.





---



## 11. Extended Remote & Resilience Safety Contract (Rounds 26-31)

1. **Telegram Pairing & Authentication**: Remote bridge requires a single-use desktop QR code or 6-digit PIN handshake (/pair <PIN>). Non-whitelisted strangers receive zero reply (silent drop) while pushing a high-priority security alert to Abhi's desktop and Telegram.

2. **Workstation Locking on Remote Emergency**: Receiving /lock or /halt from Telegram immediately locks the Windows workstation (

undll32.exe user32.dll,LockWorkStation) and engages the Guardian kill switch.

3. **Remote Media Privacy**: Screenshots transmitted over Telegram automatically redact sensitive regions (passwords, OTPs, banking/card details). Large files (> 50MB) are delivered as chunked 45MB encrypted archives.

4. **Prompt Injection Defense**: When untrusted web content or emails contain adversarial instructions ('Ignore previous instructions...'), Phenom sanitizes the text, strips malicious command vectors, and continues safe analytical evaluation.

5. **Zero Telemetry & Local Crash Dumps**: No crash dumps, memory snapshots, or usage metrics depart the machine; logs reside strictly in ~/Documents/Phenom/logs/.

6. **Strict UAC Elevation**: Any Windows process requiring elevated administrative privileges strictly triggers the standard Windows UAC prompt; background bypass is impossible by construction.





---



## 12. Database, Container & Secret Safety Guarantees (Rounds 32-35)

1. **Database Query Safety**: Read-only SQL queries (SELECT, PRAGMA) are classified as Tier 0. Any mutation query (UPDATE, DELETE, DROP, ALTER, TRUNCATE) is classified as Tier 2, requiring explicit preview of affected tables and estimated row impact before execution.

2. **Container Lifecycle Controls**: Docker status inspection and log reading are Tier 0. Starting, stopping, or restarting containers is Tier 1. Removing containers, pruning networks, or wiping data volumes is Tier 2, strictly requiring interactive confirmation.

3. **Automatic Secret Masking in Logs & Console**: Console streams, stdout/stderr pipelines, and action logs automatically cross-reference active .env values and Windows Credential Manager entries, replacing sensitive strings with [REDACTED_SECRET] before rendering or persisting to disk.

4. **Proactive Secret Migration**: If an uncommitted file contains hardcoded API keys or private tokens, git commit actions are blocked, prompting a 1-click migration to Windows Credential Manager or .env referenced in .gitignore.





---



## 13. Multimodal Vision, Hybrid Router & Cloud Safety Guarantees (Phenom 4.0)

1. **Tier 2 Cloud Vision Escalation (sk_screen_vision_cloud)**:

   - Screen frames are pre-masked in RAM using PrivacyMasker to black out sensitive application windows (password managers, banking, incognito browsing, credentials) before serialization.

   - Any escalation to Cloud VLM (NVIDIA Nemotron / NeVA) strictly requires Tier 2 on-screen user preview and approval.

2. **Deterministic Intent Routing & Rule 4 Invariant (HybridRouter)**:

   - Queries are routed between fast local OS actions (< 200ms target), local UI coordinate finders, and cloud vision in < 5ms.

   - If any query or active context contains sensitive PII (Aadhaar, PAN, payment credentials, private keys), cloud escalation is categorically prohibited and forced to local execution.

3. **Resilient Offline Fallback (MultimodalCoordinator)**:

   - On network drop, HTTP 500/timeout, or missing API credentials, the system automatically degrades to on-device OCR and local Moondream2 VLM without user-facing errors or crashes.

4. **Zero Disk IO for Screen Buffers**:

   - Captured frames, delta hashes, and base64 payloads reside strictly in memory and are discarded immediately after inference.

5. **Real-Time HUD Annotation Transparency (AnnotationStreamer)**:
   - Screen element bounding boxes are streamed over authenticated WebSocket and rendered on the Cyber HUD in Electric Cobalt (#0052FF) and Acid Lime (#CCFF00), ensuring complete user visibility of detected targets before action execution.
   - Bounding boxes auto-fade after timeout and are immediately wiped on task completion.
6. **Guardian Kill Switch Full-System Synchronous Halt (SAF-02)**:
   - Synchronous halt triggered via Ctrl+Alt+Pause global hotkey or HUD button:
     - Synchronously purges TTS speech and releases audio hardware (< 50ms).
     - Dispatches ision.clear_annotations to wipe all active HUD bounding boxes immediately.
     - Aborts pending confirmation dialogs and locks orb state in halted (#EF4444).


---

## 14. Autonomous Desktop & Browser Orchestration Guarantees (Phenom 5.0 Phase 1)

1. **Tier 2 Multi-Step Execution Preview (execute_autonomous_task)**:
   - The autonomous orchestrator decomposes complex natural language goals into sequential primitive actions (GoalPlan).
   - Before any autonomous action loop starts, the full multi-step plan is registered in the Safety Registry as Tier 2 and rendered to the user for explicit confirmation with a complete step preview.
2. **Strict Rule 8 Payment & Checkout Prohibition by Construction**:
   - The AutonomousGoalPlanner scans planned intents and parameter signatures for financial and payment primitives (e.g. pay, checkout, credit_card, purchase, order).
   - If detected, planning fails immediately with SafetyViolationError prior to execution, preventing the engine from ever executing a payment step.
3. **Sub-Second Human Takeover (< 1s)**:
   - Physical mouse movement or hardware keystrokes during an active automation session trigger 	akeover_manager._trigger_pause in < 1 second.
   - Automation loop immediately suspends between actions and streams an interactive takeover state (	akeover) to the Cyber HUD.
   - Resumption is impossible without explicit user confirmation (continue); if the user selects stop or the 15-second takeover timeout expires, the automation session safely aborts with checkpoint preserved.
4. **Resilient Task Checkpointing**:
   - After each step execution, a TaskCheckpoint is recorded with step index, state, and results, allowing interrupted sessions to safely resume from the exact point of interruption without repeating side-effect actions.
5. **Real-Time Cyber HUD Telemetry**:
   - During execution, the engine broadcasts continuous screen.action_ticker events with step progress and descriptions, and screen.click_highlight ripples around active click coordinates.


---

## 15. Obsidian Second Brain & Note Crystallization Guarantees (Phenom 5.0 Phase 2)

1. **Strict Vault Path Sandboxing (
esolve_and_sandbox_vault_path)**:
   - All note creation, reading, and appending operations are strictly sandboxed inside the external Obsidian vault directory.
   - Any path traversal escape attempts (.., junctions, drive-switching) or attempts to target the Phenom code repository immediately trigger VaultSandboxViolation.
2. **Rule 4 Vault Privacy Invariant**:
   - Vault markdown files are classified as private by default. Note extraction and crystallization operate locally without sending private vault contents to cloud models without explicit approval.
3. **1-Click Reversible Rollback Engine**:
   - Every note crystallization or daily log modification generates an undo_token storing the pre-mutation state (or new-file marker).
   - 
ollback_vault_note(undo_token) restores previous note contents or removes newly created files cleanly, committing the reversal to the vault's local Git repository.
4. **Safety Registry Tier 1 Classification (crystallize_session_notes, 
ollback_vault_note)**:
   - Registered as Tier 1 tools with interactive previews and immutable logging in SQLite ction_log.


---

## 16. Proactive Ambient Intelligence & Context Guarantees (Phenom 5.0 Phase 3)

1. **Non-Intrusive Ambient Alert Invariant**:
   - Ambient alerts rendered on the Cyber HUD must never steal window focus, disrupt active user keyboard inputs, or interrupt foreground fullscreen workflows.
   - Alert toasts auto-dismiss after 6 seconds and display non-blocking category pills with dismiss controls.
2. **Deep Focus & Meeting Mode Silence**:
   - In DEEP_FOCUS mode (or when video conferencing is active in Meeting Mode), all non-critical notifications are strictly suppressed by policy (
otification_policy == 'silent').
   - Procedural audio chimes are muted (udio_volume_scale == 0.0) in Deep Focus.
3. **Alert Fatigue Prevention via 5-Minute Cooldowns**:
   - Hardware resource alerts (CPU, RAM, GPU VRAM) enforce a minimum 5-minute cooldown between repeated alerts.
   - Calendar alerts are deduplicated per unique meeting ID, ensuring each meeting triggers at most once.
4. **Zero Audio Disk I/O**:
   - Ambient chimes (play_ambient_toast_chime, play_subtle_alert_chime) are synthesized directly in RAM using NumPy sine waves with zero temporary audio files created on disk.
5. **Safety Registry Tier 0 Status**:
   - get_ambient_status and set_assistant_mode are registered as Tier 0 read-only / safe configuration tools.


---

## 17. Mobile Remote Companion & Multi-Layer Safety Guarantees (Phenom 5.0 Phase 4)

1. **Owner-Only Authentication & Silent Stranger Drop**:
   - The Telegram remote companion strictly processes updates originating from the whitelisted numeric `_owner_id`.
   - All unauthorized messages, callback queries, and voice notes from strangers are silently dropped with zero response returned, and logged to `ignored_messages_log` for auditing.

2. **Multi-Layer Rule 8 Zero-Payment Invariant (Defense-in-Depth)**:
   - **Layer 1 (Remote Bridge Gate)**: Rejects `/do` commands containing prohibited payment keywords (`pay`, `checkout`, `buy`, `credit_card`, `purchase`) with an immediate Rule 8 warning and action log audit record.
   - **Layer 2 (Autonomous Goal Planner)**: Pre-flight regex scanner raises `PermissionError` on payment/checkout goals, terminating planning before execution starts.
   - **Layer 3 (Safety Tool Registry)**: `checkout_pay` and `enter_payment_info` are permanently blocked (Tier 3) and raise `PermissionError` unconditionally.
   - **Layer 4 (Browser Cart Automator)**: Traverses e-commerce platforms to add requested items to cart, halts before checkout review, and hard-fails if payment or OTP keywords are detected. No code path exists to submit payments.

3. **Remote 6-Digit PIN Gate & 3-Strike Lockout**:
   - Tier 2 modifying actions dispatched remotely require 6-digit PIN authorization.
   - PIN messages auto-delete after 15 seconds via Telegram message ephemerality (`deleteMessage`).
   - 3 consecutive failed PIN attempts trigger immediate complete remote lockout, which can only be reset physically at the desktop application.

4. **Synchronous Guardian Full-System Halt (< 25ms SLA)**:
   - Triggering the Guardian kill switch (`Ctrl+Alt+Pause` or remote `/halt`) halts the system in under 25ms (verified ~13.4ms).
   - Synchronously silences TTS audio speech, clears HUD bounding boxes and overlay annotations, and invokes `autonomous_engine.abort("guardian_halt")` to break running loops immediately.

5. **In-RAM Voice Memo Decryption & Transcription**:
   - Remote voice memos are decoded and transcribed via local Whisper entirely in memory. Zero voice audio bytes or credentials are ever written to disk.


---

## 18. Continuous Desktop Visual Memory & Temporal Recall (Phenom 6.0 Phase 1)

1. **Strictly Zero Screen Frame Disk Writes**:
   - Screen frames captured by `FrameGrabber` and processed by `VisualMemoryMonitor` exist solely in transient RAM buffers. No screenshot image files (PNG, JPEG, BMP) are ever written to disk.
2. **Perceptual Delta Triggering (< 1.5% Delta Gate)**:
   - Screen differences are evaluated via downsampled 64x36 grayscale thumbnail hashing (`DeltaDetector`).
   - If the normalized pixel difference is below 0.015, all text extraction and embedding generation are skipped, ensuring near-zero idle resource consumption.
3. **Sensitive Application Exclusion & Window Redaction**:
   - `PrivacyMasker` monitors top-level and foreground windows. Any window matching sensitive patterns (1Password, Bitwarden, KeePass, private browsing / incognito tabs, online banking, crypto wallets, Credential Manager) is blacked out in memory or completely excluded from OCR extraction.
   - Text elements whose bounding boxes overlap sensitive window rects are automatically discarded.
4. **100% Local GPU Vector Embeddings & Encrypted SQLCipher Storage**:
   - Text vector embeddings are computed locally using `sentence-transformers` (`all-MiniLM-L6-v2`) on NVIDIA CUDA or local CPU. Zero visual or text history is ever transmitted off the machine without explicit preview approval.
   - Extracted text chunks and 384-dimensional dense vectors are persisted in an encrypted SQLCipher database (`visual_history.db`) with rolling 7-day retention pruning.
5. **Safety Registry Tier 0 Classification (search_visual_memory)**:
   - `search_visual_memory` is registered as a Tier 0 read-only tool with structured preview descriptions.
6. **Guardian Kill Switch Synchronization**:
   - Triggering the Guardian kill switch immediately halts the `VisualMemoryMonitor` ingestion loop synchronously alongside speech and automation aborts.


---

## 19. Hybrid Autonomous Worker Swarm Guarantees (Phenom 6.0 Phase 2)

1. **Focus Protection & Headless Isolation Invariant**:
   - Background web scraping, research, and documentation crawling run strictly inside headless Playwright contexts (`headless=True`) or detached subprocesses.
   - Background workers must never create taskbar windows, never grab foreground window focus, and never move the physical mouse cursor.
2. **Rule 8 Zero-Payment Invariant in Headless Workers**:
   - Every URL and action payload in `HeadlessBrowserWorker` and `WorkerSwarmManager` is screened against `BLOCKED_PAYMENT_KEYWORDS` (`place order`, `pay now`, `proceed to pay`, `checkout`, `cvv`, `otp`).
   - If any payment keyword is detected, execution halts immediately with `PermissionError` and logs a blocked action entry.
3. **Destructive Command Defense in Subprocess CLI Workers**:
   - Destructive commands matching dangerous system deletion or formatting patterns (`format`, `del /f /s C:\Windows`, `rm -rf /`) are blocked by code-level regex scanners.
4. **Bounded Concurrency & Resource Safety**:
   - `WorkerSwarmManager` strictly limits concurrent background workers (default maximum 3) to prevent system memory exhaustion and browser process leaks.
5. **Durable Step Checkpointing**:
   - Worker task progress is recorded in SQLite `swarm_checkpoints` after every step, allowing recovery or post-mortem auditing without data loss.
6. **Safety Registry Classifications**:
   - `get_swarm_status`: Tier 0 read-only tool.
   - `dispatch_swarm_task`: Tier 1 tool requiring preview confirmation.
   - `abort_swarm_task`: Tier 1 tool requiring confirmation.
7. **Guardian Kill Switch Full-Swarm Abort (< 25ms SLA)**:
   - Triggering the Guardian kill switch immediately invokes `swarm_manager.abort_all("guardian_halt")`, terminating all running headless browsers and subprocesses synchronously in < 25ms (verified ~20.9ms).


---

## 20. Deep Obsidian Second-Brain Knowledge Graph Guarantees (Phenom 6.0 Phase 3)

1. **Strict Vault Sandboxing & Path Containment**:
   - Every file read, link insertion, and graph traversal operation is constrained strictly within the configured vault directory (`resolve_and_sandbox_vault_path()`).
   - Any path traversal (`..`), directory junction, or code repository collision is rejected with `VaultSandboxViolation`.
2. **1-Click Reversible Link Insertions & Mandatory Git Commits**:
   - Any automated modification to Obsidian notes (e.g., adding `[[wikilinks]]`) records a pre-mutation snapshot in the crystallizer undo registry, generating a unique `undo_token`.
   - Every mutation is committed automatically to the vault's local git repository (`vault.commit_changes()`).
   - Calling `rollback_vault_note(undo_token)` reverses link additions and restores original note contents cleanly.
3. **Local-First Graph Privacy**:
   - The bidirectional graph index (`ObsidianGraphIndex`) and semantic topic co-pilot (`ObsidianGraphCoPilot`) operate 100% locally using on-device CUDA text embeddings (`all-MiniLM-L6-v2`).
   - Vault notes, daily logs, and personal ideas are never transmitted to cloud models without explicit user-previewed confirmation.
4. **Safety Registry Classifications**:
   - `query_obsidian_graph`: Tier 0 read-only tool.
   - `find_orphan_notes`: Tier 0 read-only tool.
   - `synthesize_vault_topic`: Tier 0 read-only tool.
   - `link_vault_notes`: Tier 1 tool requiring interactive preview approval.


---

## 21. Full-Duplex Voice Pipeline & Presence Awareness Guarantees (Phenom 6.0 Phase 4)

1. **Strictly Zero Audio Disk Writes (In-RAM Circular Ring Buffer)**:
   - Microphone chunks (16kHz, 512 samples/chunk) ingested by `FullDuplexVoicePipeline` reside strictly within an in-memory ring buffer (`collections.deque(maxlen=N)`).
   - No audio files (`.wav`, `.mp3`, `.raw`) are ever written to the file system during continuous listening, voice detection, or turn-taking.
2. **Sub-50ms Conversational Barge-In Interruption**:
   - When assistant speech playback is active and user voice is detected (via Silero VAD probability >= 0.50 or RMS floor gate), `barge_in_controller` instantly cancels TTS playback via `tts_engine.stop_speech()` in < 5ms.
   - Background system audio is ducked asynchronously, and the pipeline transitions to `LISTENING` with zero user disruption.
3. **100% Offline Local Silero VAD Inference**:
   - Speech activity detection runs entirely on-device via the bundled ONNX Silero VAD model (`silero_vad.onnx`) with recurrent state caching.
   - Per-chunk inference latency is ~0.2-0.5ms with zero cloud network dependence or data leakage.
4. **Context-Aware Presence Modulation & Deep Focus Silence**:
   - `VoiceModulator` synchronizes TTS volume scale, speech cadence (rate), and Jarvis conversational tone with active application presence:
     - `WORK`: 100% volume, brisk cadence (+1), executive tone.
     - `STUDY`: 35% gentle volume, measured pace (0), scholarly tone.
     - `CHILL`: 65% relaxed volume, playful witty tone.
     - `DEEP_FOCUS`: 0% volume (strictly muted audio), zero audible notifications.
5. **Guardian Kill Switch Full Voice & Audio Halt (< 25ms SLA)**:
   - Triggering the Guardian kill switch immediately invokes `duplex_pipeline.halt()` and `tts_engine.stop_speech()` synchronously, clearing all ring buffers, queues, and audio streams in under 10ms (verified ~7.4ms).
6. **Safety Registry Classifications**:
   - `get_voice_duplex_status`: Tier 0 read-only tool for real-time duplex metrics and active modulation status.
   - `configure_voice_presence`: Tier 1 tool requiring user preview confirmation to alter volume scale, cadence rate, or mode overrides.
   - `trigger_voice_barge_in`: Tier 0 low-risk tool for instantaneous speech interruption.

## 22. Ambient Context Sensing & Proactive Event Architecture Guarantees (Phenom 7.0 Phase 1)

1. **Zero Low-Level Input Hooks (`WH_KEYBOARD_LL` Prohibited)**:
   - User inactivity monitoring in `Win32IdleDetector` uses `ctypes.windll.user32.GetLastInputInfo` and `kernel32.GetTickCount64()`.
   - No keyboard or mouse event hooks are installed. The assistant cannot log keystrokes, intercept user input, or trigger antivirus heuristics.
2. **Automatic Privacy Redaction of Sensitive Window Titles**:
   - `Win32ContextSensor` inspects active foreground windows and processes.
   - Any window title or process containing sensitive terms (`bitwarden`, `keepass`, `1password`, `whatsapp`, `telegram`, `banking`, `login`, `password`, `credential`, `authenticator`, etc.) is strictly sanitized to `[REDACTED_SENSITIVE_APP]`.
3. **Anti-Fatigue Rate Limiting & Cooldown Engine**:
   - `ProactiveEventDispatcher` enforces a default cooldown (e.g. 15 minutes) between non-urgent recommendation cards to prevent notification spam.
   - Non-urgent cards (`priority < URGENT`) are completely suppressed and queued silently during `DEEP_FOCUS` and `STUDY` modes.
   - Urgent calendar reminders (< 15 min to meeting) bypass non-critical cooldowns and pulse the Three.js Orb with Acid Lime (`#CCFF00`).
4. **Synchronous Guardian Kill Switch Halt (< 25ms SLA)**:
   - `guardian.trigger()` synchronously invokes `idle_detector.halt()`, `context_sensor.halt()`, and `proactive_dispatcher.halt()`, cancelling all background polling tasks in < 25ms.
5. **Safety Registry Classifications**:
   - `get_proactive_status`: Tier 0 read-only tool for idle duration, active window context, and active card list.
   - `configure_proactive_cooldown`: Tier 1 tool requiring confirmation to modify idle thresholds or event cooldowns.
   - `dismiss_proactive_card`: Tier 0 tool for dismissing active recommendation cards.

## 23. Autonomous Executive Briefing & Calendar/Gmail Triage Guarantees (Phenom 7.0 Phase 2)

1. **Strict Drafts-Only Invariant for Email (Rule 9)**:
   - All email modifications by `GmailTriageService` use IMAP `APPEND` directly into the `[Gmail]/Drafts` mailbox folder with `\Draft` flag.
   - It is physically impossible for Phenom to transmit outbound emails: `send_email` raises `EmailSendingProhibitedError` and no SMTP libraries or send endpoints exist.
2. **Read-Only IMAP Inspection (`EXAMINE INBOX`)**:
   - Inbox scanning for unread priority threads operates using the IMAP `EXAMINE` command (read-only mode), ensuring message flags, read status, and labels on the server remain completely unmutated.
3. **Calendar Modification Prohibitions**:
   - Creating calendar events uses the Google Calendar REST API (`create_event`) and requires Tier 1 confirmation.
   - Deleting or editing existing calendar events is strictly prohibited: `delete_calendar_event` and `edit_calendar_event` raise `CalendarModificationProhibitedError`.
4. **Calendar Horizon Deduplication**:
   - `CalendarLookaheadScanner` scans upcoming events within 15–30 minutes. An in-memory deduplication set ensures each unique `event_id` triggers an urgent notification at most once.
5. **Synchronous Guardian Kill Switch Halt (< 25ms SLA)**:
   - `guardian.trigger()` synchronously invokes `calendar_scanner.halt()` and `gmail_triage.halt()`, aborting all active lookahead loops and IMAP queries in < 25ms.
6. **Safety Registry Classifications**:
   - `get_executive_briefing`: Tier 0 read-only operational briefing query.
   - `scan_calendar_upcoming`: Tier 0 read-only calendar lookahead query.
   - `triage_unread_emails`: Tier 0 read-only inbox triage inspection.
   - `draft_email_reply`: Tier 1 tool requiring user preview confirmation before saving a draft to `[Gmail]/Drafts`.
   - `schedule_meeting_event`: Tier 1 tool requiring user preview confirmation before adding a new event to Google Calendar.
