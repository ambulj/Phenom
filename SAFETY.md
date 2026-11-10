# SAFETY.md: risk tiers and safety rules



This file is the contract for the Safety layer. The code enforces it; this document must always match the code. Update it whenever a tool is added or changed.



## 1. Risk tiers

| Tier | Name | Behaviour | Examples |

| --- | --- | --- | --- |

| 0 | Read-only | Runs automatically, logged | list files, read a file, search memory & vector store, search photos, inspect UI elements, take screenshot (RAM), summarize YouTube, organize Downloads dry run, get mode, list scheduled jobs, get weather, get tech news, get market quote, get financial watchlist, get mutual fund quote, get sports score, search research papers, lookup DOI citation, search/read Gmail, list calendar events, vision_get_ambient_screen_context, governor_get_resource_status, voice_get_engine_status, voice_speak_utterance, graph_rag_query, graph_rag_get_stats, mission_get_status, mission_get_morning_debrief, gui_capture_virtual_screen, mirror_get_profile_stats, mirror_synthesize_text |

| 1 | Reversible change | One confirmation; user may choose "remember for this folder" | create or move or copy a file, open or close an app, organize Downloads apply (reversible with undo), write Obsidian vault note, append daily log, set mode, schedule reminder, cancel scheduled job, add/remove financial watchlist, create Gmail draft, generate document (.docx, .xlsx, .pptx, .pdf), vision_configure_ambient_copilot, voice_configure_engine, graph_rag_reindex_domain, mission_start_unattended, mission_abort, gui_launch_app_isolated, gui_execute_action, gui_close_isolated_desktop, mirror_learn_from_sources, mirror_reset_profile |

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

### Autonomous Background Workers & Housekeeping Safety Protocol (Phase 3)
1. **Rule 7 Recycle Bin Enforcement for Housekeeping**:
   - `WorkspaceHousekeeper` sorts unfiled files in the user staging/Downloads folder into categorized subfolders (`Documents/`, `Images/`, `Archives/`, `Code/`).
   - All temporary clutter files (`.tmp`, `.crdownload`, `.partial`, `~$*`) are recycled via `send2trash.send2trash()`. Permanent deletion via `os.remove()` is strictly prohibited by construction.
2. **Focus-Free Headless Topic Research**:
   - `TopicResearchWorker` dispatches headless Playwright browser workers (`headless=True`) via `SwarmManager`. Zero OS cursor movement or window focus disruption is permitted.
   - Extracted meeting research briefs are committed to `vault/Meetings/YYYY-MM-DD - {Topic}.md` and presented via `ProactiveCard` on the Cyber HUD.
3. **Non-Destructive Daily Note Merging**:
   - `ObsidianDailyCoPilot` manages `vault/Daily Notes/YYYY-MM-DD.md`.
   - Calendar timeblocks, action items, and background triage logs are synchronized into dedicated sections (`## Scheduled Timeblocks`, `## Action Items & Directives`, `## Background Swarm & Triage Log`) via non-destructive regex block replacement.
   - User handwritten journal entries under `## Notes & Journal` or custom headers are strictly preserved and never overwritten. Reversible undo snapshots are maintained with `rollback_mutation`.
4. **User Return Interruption & Guardian Halt (< 25ms SLA)**:
   - If the user returns from idle (`idle_detector.is_idle == False`), `WorkspaceHousekeeper` yields and halts immediately.
   - `guardian.trigger()` synchronously invokes `topic_researcher.halt()` and `workspace_housekeeper.halt()`, aborting all active workers and file passes within the sub-25ms SLA.
5. **Safety Registry Classifications**:
   - `get_housekeeper_status`: Tier 0 read-only status and metrics.
   - `run_workspace_housekeeping`: Tier 1 tool requiring user preview confirmation before file sorting or recycling.
   - `dispatch_topic_research`: Tier 1 tool requiring user preview confirmation before autonomous worker dispatch.
   - `sync_obsidian_daily_note`: Tier 1 tool requiring user preview confirmation before mutating daily notes.

### Proactive Safety, Guardian Cascade & Prompt Injection Defense (Phase 4)
1. **Full Milestone 7.0 ToolRegistry Audit (`SAF-01`)**:
   - All 12 proactive tools across Phases 1, 2, and 3 are registered with strict Pydantic argument schemas, constraints, field bounds, and preview functions.
   - Tier 0 tools (`get_proactive_status`, `dismiss_proactive_card`, `get_executive_briefing`, `scan_calendar_upcoming`, `triage_unread_emails`, `get_housekeeper_status`) are guaranteed read-only with zero mutations.
   - Tier 1 tools (`configure_proactive_cooldown`, `draft_email_reply`, `schedule_meeting_event`, `run_workspace_housekeeping`, `dispatch_topic_research`, `sync_obsidian_daily_note`) enforce explicit interactive confirmation dialogs with dynamic context preview.
2. **Synchronous Guardian Kill Switch Cascade (< 25ms SLA) (`SAF-02`)**:
   - `guardian.trigger()` executes an immediate synchronous cascade stopping all 7 proactive subsystems (`idle_detector`, `context_sensor`, `proactive_dispatcher`, `calendar_scanner`, `gmail_triage`, `topic_researcher`, `workspace_housekeeper`) and rejecting pending confirmations.
   - Benchmarked under full concurrent load and verified at **< 1.0ms** (well within the 25.0ms SLA).
   - Universal rejection: every subsystem strictly raises `PermissionError` while in the halted state.
   - Self-healing recovery: `guardian.resume()` triggers an automatic synchronous reset across all proactive components.
3. **Untrusted Proactive Input Taint & Prompt Injection Defense**:
   - External calendar event summaries, inbound email bodies, and web research snippets are inspected via `taint_tracker.inspect_and_sanitize()`.
   - Adversarial prompt injection attacks (30-pattern corpus) are intercepted, tagged, and quarantined in `<untrusted_external_content>` tags.
   - Tainted contexts automatically escalate Tier 1 mutating tools to Tier 2 (explicit interactive confirmation with security warning; remembered approvals suspended).


## 24. Autonomous Developer & Mobile Executive Partner Safety Guarantees (Phenom 8.0)

### Phase 1: Developer Workspace Sentinel & Git State Tracker (DEV-01)
1. **Zero Secret Leaking in Git Tracking**:
   - DeveloperWorkspaceState inspects tracked repository state and strictly masks secret files matching sensitive patterns (.env, credentials, *secret*, *.pem, id_rsa, 	oken, password) to [PROTECTED_SECRET_FILE].
2. **Safety Registry Classification**:
   - coding_get_workspace_state: Tier 0 read-only tool for inspecting active IDE process, git branch, line delta math, and changed files.
3. **Synchronous Guardian Halt (< 1ms)**:
   - workspace_sentinel.halt() halts background polling loops immediately upon Guardian trigger.

### Phase 2: Proactive Dev Build Sentinel & Patch Fix Drafter (DEV-02)
1. **Deterministic Multi-Runner Traceback Ingestion**:
   - Traceback patterns for pytest, vitest/jest, tsc, and cargo are parsed deterministically into structured diagnostics with secret masking.
2. **Atomic Rollback Guarantee via Non-Destructive Git Stash Pre-Patch Snapshots**:
   - Before applying any unified patch, git stash create 'Phenom pre-patch snapshot' captures a dangling commit representing the developer's exact uncommitted tree without touching disk.
   - Any patch failure or user rollback triggers git reset --hard HEAD and git stash apply <token>, guaranteeing 100% worktree restoration.
3. **Safety Registry Classification**:
   - coding_diagnose_build_failure: Tier 0 read-only diagnostic parsing.
   - coding_draft_patch: Tier 0 read-only unified diff generation.
   - coding_apply_patch: Tier 1 action requiring explicit interactive preview confirmation before applying git patch.
   - coding_revert_patch: Tier 1 action requiring preview confirmation before restoring worktree from pre-patch snapshot.

### Phase 3: Telegram Mobile Executive Companion & Remote 1-Click Approval Gateway (MOB-01, MOB-02)
1. **Inbound Prompt Injection Defense & Taint Quarantine (SAF-01)**:
   - Every inbound Telegram update passes through 	aint_tracker.inspect_and_sanitize(text, source='telegram').
   - Injections (IGNORE ALL PREVIOUS INSTRUCTIONS, etc.) are quarantined, logged as Tier 3 security events, and stripped from execution.
2. **Dual-Presence 1-Click Action Approval Gateway (MOB-02)**:
   - When Tier 1 desktop confirmations are queued, an interactive push notification is delivered to the owner's Telegram with inline keyboard buttons: [Approve], [Deny], [View Diff].
   - Approvals over Telegram asynchronously fulfill desktop pending_confirmations[req_id], broadcasting confirm.resolved to the desktop WebSocket in real time.
3. **Safety Registry Classification**:
   - 	elegram_send_mobile_alert: Tier 0 read-only ambient notification tool.
   - 	elegram_get_remote_status: Tier 0 read-only connection status query.
4. **Guardian Remote Kill Switch SLA (< 25ms)**:
   - /halt and /kill commands trigger synchronous Guardian halt in < 1ms (verified 0.413ms benchmark).


### Phase 4: Deep Project Knowledge Crystallization & Dual-Presence Guardian Safety (RES-01, SAF-01, SAF-02)
1. **Non-Destructive Vault Preservation**:
   - `ProjectKnowledgeCrystallizer` non-destructively updates `vault/Projects/{ProjectName}.md` using regex section parsing, strictly preserving user handwritten notes in `## Notes & Journal`.
2. **Reversible Snapshot Rollback**:
   - Every note mutation creates an in-memory snapshot keyed by a unique UUID `rollback_token`, allowing instantaneous undo via `coding_rollback_crystallized_note`.
3. **Safety Registry Tool Classification**:
   - `coding_crystallize_project_knowledge`: Tier 1 (Vault modification, requires preview).
   - `coding_rollback_crystallized_note`: Tier 1 (Rollback action, requires preview).
   - `coding_query_project_knowledge`: Tier 0 (Read-only query of project documentation).
4. **Sub-25ms Synchronous Guardian Halt Verification**:
   - Hooked `project_crystallizer.halt()` and `project_crystallizer.reset()` into Guardian callbacks.
   - Synchronous kill switch execution benchmarked at **< 1.0ms** (0.413ms) across all subsystems. All subsystems raise `PermissionError` when halted.

## 25. Polish and Packaging Safety Guarantees (Phenom 8.0 / Phase 7)

### 1. Local-Only Crash Logs and Sanitization Guarantees (Rule 4 & Rule 11)
- Crash logs are stored strictly on the local machine (`services/backend/data/crash_logs/*.json`).
- Zero telemetry, network transmission, or automated crash reporting to external services.
- One-click sanitized diagnostic export deeply redacts:
  - Windows user directories: `C:\Users\<username>\...` -> `C:\Users\[USER]\...`
  - IP addresses: `\b(?:\d{1,3}\.){3}\d{1,3}\b` -> `[REDACTED_IP]`
  - API keys and tokens: NVIDIA NIM keys -> `[REDACTED_NVIDIA_KEY]`, Telegram tokens -> `[REDACTED_TELEGRAM_TOKEN]`.

### 2. Auto-Update Safety & Rollback Guarantee
- Updates are staged in isolated cache directories and verified before application.
- If a newly launched version fails to start or pass prerequisite checks, `AutoUpdateManager` automatically rolls back to the prior stable release artifact, preventing deadlocks or application bricking.

### 3. First-Run Wizard & Permission Boundaries
- `FirstRunWizard` strictly enforces user permission boundaries before initializing background indexing:
  - Explicit folder selection (Documents, Downloads, Photos).
  - Explicit API key input stored securely in Windows Credential Manager / environment variables.
  - Safe default hotkeys (`Alt+Space` summon, `Ctrl+Alt+P` or `Ctrl+Alt+Escape` Guardian kill switch) communicated clearly to the user.
## 26. Continuous Local Multimodal Screen Vision & Adaptive Resource Governor (Milestone 9.0 Phase 1)

### 1. Zero-Disk In-Memory Frame Safety & Strict Privacy Blacklist Gate (VIS-01)
- Continuous screen frames captured by `FrameGrabber` and processed by `AmbientVisionCopilot` remain strictly in RAM (`io.BytesIO` / PIL in-memory image buffer). Zero unencrypted or temporary frame files are written to disk.
- Foreground window titles and process executables are checked against a strict privacy blacklist:
  - Credential managers (`1password`, `bitwarden`, `keepass`, `keepassxc`, `lastpass`, `dashlane`, `enpass`, `nordpass`).
  - Private browsing (`incognito`, `inprivate`, `private browsing`, `private window`).
  - Financial, banking, and crypto portals (`chase`, `bank of america`, `wells fargo`, `fidelity`, `schwab`, `paypal`, `metamask`, `coinbase`, `binance`).
  - Private chat and messaging (`whatsapp`, `signal`, `telegram`).
  - System security prompts (`credential manager`, `windows security`, `user account control`).
- When a blacklisted application or window is active, frame capture and VLM inference are completely suppressed; the copilot returns `[BLACKLOCKED_WINDOW_SKIPPED]` with redacted context.
- Sensitive visible windows on screen are automatically redacted with solid black privacy masks directly in the in-memory buffer before any local VLM inspection.
- Stationary screens (< 2% perceptual pixel change) skip local VLM inference, saving GPU compute and power.

### 2. Adaptive Performance & Hardware Resource Governor (GOV-01)
- `AdaptiveResourceGovernor` continuously inspects GPU 3D utilization, VRAM usage, and full-screen DirectX/Vulkan game processes.
- Automatic suspension: When full-screen 3D gaming or high GPU load (> 85%) / CPU load (> 90%) is detected, the governor immediately pauses continuous vision loops and worker swarms, preventing frame drops and VRAM contention.
- Automatic resumption: Once gaming processes terminate and GPU load drops below 60% across consecutive idle cycles, background tasks resume seamlessly.

### 3. ToolRegistry Risk Tiering & Previews (SAF-01)
- `vision_get_ambient_screen_context`: Tier 0 (Read-only, retrieves sanitized in-memory ambient context).
- `governor_get_resource_status`: Tier 0 (Read-only, retrieves GPU/CPU metrics and gaming status).
- `vision_configure_ambient_copilot`: Tier 1 (Reversible change, modifies copilot parameters with user approval).

### 4. Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `ambient_copilot.halt()` and `resource_governor.halt()` are synchronously invoked from `on_guardian_state_change("halted")`.
- Execution SLA: All active vision loops, tasks, and resource monitoring halt synchronously in `< 25ms` (< 1ms typical).
- While halted, any subsequent vision or governor tool calls or step requests immediately raise `PermissionError`.
- Clean state reset and resumption via `reset()` when Guardian transitions to `idle`.

---

## 27. Streaming Zero-Latency Conversational Voice Engine & Barge-In Guarantees (Milestone 9.0 Phase 2)

### 1. Sub-200ms Turnaround Pipeline & Zero Disk Audio Invariant (VOX-01)
- Continuous microphone ingestion uses 16kHz mono audio chunks (512 samples / 32ms per chunk) stored strictly in RAM circular ring buffers (`collections.deque(maxlen=N)`).
- Turn boundary detection uses Silero VAD ONNX running sub-millisecond inference (< 0.5ms per chunk).
- End-of-speech silence detection is calibrated at 6 consecutive chunks (~192ms silence), triggering turn completion without awkward conversational delays.
- Sub-200ms turnaround benchmark: total turnaround latency from end-of-speech silence detection to first audio packet emission is strictly `< 200ms`.
- **Zero Disk Writes**: Audio data resides exclusively in RAM throughout all pipeline stages (microphone ring buffer, VAD, STT, and streaming TTS emission). No `.wav`, `.raw`, or audio files are ever written to disk.

### 2. Instantaneous Conversational Speech Barge-In Interruption (< 5ms SLA) (VOX-01)
- When the assistant is in `SPEAKING` state, user voice activity is continuously monitored via Silero VAD ONNX.
- **Two-Chunk Hysteresis**: Requires 2 consecutive speech chunks (`vad_prob >= 0.50`) to trigger barge-in, mathematically rejecting single-frame clicks, typing transients, or transient noise spikes.
- Upon confirmed user speech, the assistant immediately cuts off audio playback and client streams in `< 5ms` SLA (< 1ms typical).
- State transitions instantaneously through `INTERRUPTED` to `LISTENING`, immediately capturing the user's interrupting utterance into RAM.

### 3. Smart Minimalist Jarvis Persona Policy (VOX-01)
- Spontaneous speech is strictly gated by `MinimalistVoicePolicy` to only 4 triggers:
  1. `critical_error`: compilation errors, test failures, or crash alerts detected in ambient context.
  2. `calendar_urgent`: imminent calendar meetings or deadlines approaching in `< 10 minutes`.
  3. `guardian_security`: Guardian security alerts, permission escalations, or emergency events.
  4. `direct_summon`: explicit user wake word or direct summons.
- Complete spontaneous speech suppression during user typing or deep focus modes.
- Output utterances are automatically formatted into a witty, concise British Jarvis cadence, stripping conversational filler and pleasantries.

### 4. ToolRegistry Registration & Safety Tiering (SAF-01)
- `voice_get_engine_status`: Tier 0 (Read-Only). Returns real-time metrics of the streaming voice engine, Silero VAD availability, and Jarvis persona settings. Preview: `"Inspect streaming voice engine status and latency metrics (Read-only)"`.
- `voice_speak_utterance`: Tier 0 (Read-Only audio playback). Synthesizes and plays a spoken utterance with Jarvis cadence without disk writes. Preview: `"Synthesize and play spoken utterance: '...' (Audio playback)"`.
- `voice_configure_engine`: Tier 1 (Reversible change). Configures engine parameters: `persona_mode`, `speech_speed`, `barge_in_sensitivity`, `silence_turn_end_chunks`. Requires confirmation with preview: `"Configure streaming voice engine settings: ..."`.

### 5. Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `streaming_voice_engine.halt()` is synchronously connected to `on_guardian_state_change("halted")`.
- Execution SLA: All active audio synthesis, playback queues, and streaming audio buffers halt synchronously in `< 25ms` (< 1ms typical).
- While halted, `streaming_voice_engine.is_halted` is `True`, audio chunk ingestion is ignored, and all speech requests raise `PermissionError`.
- Clean state reset and resumption via `reset()` when Guardian transitions to `idle`.

---

## 28. Autonomous Multi-Source Personal Knowledge Graph & GraphRAG Guarantees (Milestone 9.0 Phase 3)

### 1. Unified 4-Domain Deterministic Addressing & Parsers (GRA-01)
- Universal deterministic URI addressing: `vault://<rel_path>`, `code://<repo>/<path>:<symbol>`, `git://<repo>:<commit_hash>`, `doc://<rel_path>#chunk=<idx>`, `meeting://cal:<event_id>`, `email://gmail:<thread_id>`.
- Ingests knowledge across 4 core personal domains:
  1. **Obsidian Vault**: markdown notes, `[[wikilinks]]`, `#tags`, YAML frontmatter metadata, and daily notes.
  2. **Code Repositories**: Python AST static analysis (classes, functions, methods, args, docstrings), TypeScript/JavaScript symbol regex, and git commit history linking commits to touched code symbols.
  3. **Local Documents**: PDF, DOCX, XLSX, PPTX multi-format ingestion via `doc_reader.py` with semantic chunking.
  4. **Workspace Context**: priority Gmail threads and Google Calendar meetings with heuristic cross-domain topic correlation.
- **Strict Secret Exclusion & In-Memory Scrubbing**:
  - Automatically blacklists and ignores `.env*`, `*.pem`, `*.key`, `*.cert`, `*.pfx`, `id_rsa`, `token.pickle`, `credentials.json`, `client_secret*.json`.
  - In-memory regex scrubber sanitizes node titles and summaries against API keys (`nvapi-`, `sk-`, `AKIA`), private keys, passwords, and tokens before storage in the graph.

### 2. Hybrid GraphRAG Retrieval & Zero-Cloud Leakage Invariant (GRA-01)
- Three-tier hybrid search:
  1. *Lexical Keyword Matching*: In-memory token inverted index with BM25 / token intersection scoring.
  2. *Dense Vector Semantic Search*: `LocalEmbeddingPipeline` (384-dimensional dense vectors) with sub-millisecond cosine similarity scoring.
  3. *Graph Relational Expansion*: 1-hop and 2-hop neighbor traversal with edge-weight distance attenuation (`decay = 0.7 ** hop_distance`).
- Cross-domain context synthesis generates structured prompt contexts with explicit deterministic URI citations.
- Natural language query router dynamically classifies intent to weight relevant domains.
- **Zero-Cloud Leakage Invariant**: All embeddings, graph indices, and search routines execute 100% locally on-device in RAM / local storage. No graph nodes, code symbols, or notes are transmitted to cloud endpoints.

### 3. ToolRegistry Risk Tiering & Previews (SAF-01)
- `graph_rag_query`: Tier 0 (Read-Only). Arguments: `GraphQueryArgs(query: str, hops: int = 1, domain_filter: Optional[str] = None, top_k: int = 5)`. Preview: `"Query multi-source knowledge graph for '{query}' (Read-only)"`.
- `graph_rag_get_stats`: Tier 0 (Read-Only). Arguments: `GraphStatsArgs()`. Returns node/edge counts, domain distribution, orphan counts, hub counts. Preview: `"Inspect multi-source knowledge graph topology and domain metrics (Read-only)"`.
- `graph_rag_reindex_domain`: Tier 1 (Reversible change). Arguments: `GraphReindexArgs(domain: Optional[str] = None, force_rebuild: bool = False)`. Preview: `"Reindex knowledge graph domain '{domain or 'all'}' (Reversible change)"`.

### 4. Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `multi_source_graph.halt()` and `graph_rag_engine.halt()` are synchronously invoked from `on_guardian_state_change("halted")`.
- Execution SLA: All active indexing loops, worker tasks, and graph traversals halt synchronously in `< 25ms` (< 1ms typical).
- While halted, `multi_source_graph.is_halted` is `True`, and subsequent tool calls or graph operations immediately raise `PermissionError`.
- Clean state reset and resumption via `reset()` when Guardian transitions to `idle`.

---

## 29. Sovereign Unattended Overnight Missions & Morning Cyber HUD Debrief Guarantees (Milestone 9.0 Phase 4)

### 1. Isolated Git Worktree Sandboxes & Zero Focus Theft Invariant (MIS-01)
- **Isolated Sandbox Execution**: Unattended overnight missions execute exclusively within dedicated git worktree directories at `.phenom_sandbox/missions/{mission_id}` on ephemeral branches `mission/{mission_id}` branched from current `HEAD`.
- **Primary Working Tree Invariant**: The developer's primary working tree, uncommitted modifications, unstaged files, and active IDE editor buffers remain 100% untouched throughout all mission iterations.
- **Zero Cursor / Window Focus Theft Invariant**: All test runners, compilers, and patch synthesizers run as invisible background subprocesses with `CREATE_NO_WINDOW` (`0x08000000`). No windows pop up, no desktop cursor movements occur, and no audio alerts sound during nocturnal execution.
- **Automated Lifecycle & Worktree Pruning**: Upon mission completion, failure, or abortion, git worktree references are cleanly pruned (`git worktree remove --force` / `git worktree prune`). Residual file locks on Windows are resolved by stripping readonly flags prior to tree removal. `.phenom_sandbox/` is strictly ignored in `.gitignore`.

### 2. Multi-Iteration Self-Healing Test Loops & Bounded Timeouts (MIS-01)
- **Bounded Iteration Limit**: Self-healing loops are bounded by `max_iterations` (default 5, max 20). If tests fail to heal within the allotted iterations, the runner gracefully halts, records a structured diagnostic log, and marks the mission status `failed` without corrupting branch state.
- **Subprocess Timeout Guard**: Every test runner invocation is governed by a strict subprocess timeout (default 120s, configurable). Hanging test commands or infinite loops are terminated immediately with process tree force kill (`taskkill /F /T /PID`).
- **Atomic Rollback & Validation**: Unified diffs are validated via `PatchDrafter.validate_patch` (`git apply --check`) before application.

### 3. Non-Destructive Obsidian Second-Brain Sync & Cyber HUD Debrief (MIS-01)
- **Non-Destructive Daily Notes Update**: Morning debrief summaries are merged into `vault/Daily Notes/YYYY-MM-DD.md` strictly under `## 🌙 Overnight Autonomous Missions`. All user handwritten journals, thoughts, and reflections above or below the header are 100% preserved.
- **Idempotent Section Updates**: If `## 🌙 Overnight Autonomous Missions` already exists, only that specific markdown section is replaced; duplicate headers are never created.
- **Interactive Cyber HUD Card**: Upon user return, Phenom emits `mission.morning_debrief` displaying mission objectives, healed test counts, diff line metrics (`+A / -B`), branch reviews, and triggers celebratory visual pulses on the Three.js particle orb.

### 4. ToolRegistry Risk Tiering & Previews (SAF-01)
- `mission_start_unattended`: Tier 1 (Reversible change). Arguments: `MissionStartArgs(title: str, prompt: str, repo_path: Optional[str] = None, test_command: str = "pytest", max_iterations: int = 5, timeout_seconds: int = 120)`. Preview: `"Start unattended sovereign mission '{title}' in isolated git worktree (Reversible change)"`.
- `mission_get_status`: Tier 0 (Read-Only query). Arguments: `MissionStatusArgs(mission_id: Optional[str] = None)`. Preview: `"Get status of unattended mission '{mission_id or 'latest'}' (Read-only)"`.
- `mission_abort`: Tier 1 (Reversible change). Arguments: `MissionAbortArgs(mission_id: str, reason: Optional[str] = "user_aborted")`. Preview: `"Abort unattended sovereign mission '{mission_id}' (Reversible change)"`.
- `mission_get_morning_debrief`: Tier 0 (Read-Only query). Arguments: `MissionDebriefArgs(date_str: Optional[str] = None)`. Preview: `"Generate sovereign morning debrief for '{date_str or 'today'}' (Read-only)"`.

### 5. Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `unattended_mission_runner.halt()` is synchronously invoked from `on_guardian_state_change("halted")`.
- Execution SLA: All active sandbox subprocesses, compilers, and test runners are terminated synchronously in `< 25ms` (< 1ms typical) using direct `proc.kill()` and Windows process tree kill.
- While halted, `unattended_mission_runner.is_halted` is `True`, and subsequent tool calls or sandbox creation attempts immediately raise `PermissionError`.
- Clean state reset and resumption via `unattended_mission_runner.reset()` when Guardian transitions to `idle`.

---

## 30. Autonomous Multi-Agent Collaborative Swarm & Synthetic Debate Guarantees (Milestone 10.0 Phase 1)

### 1. Specialist Sub-Agent Personas & Domain Focus (SWM-01)
- **Lead Architect**: Evaluates architectural coherence, modularity, boundary integrity, and synthesizes convergence.
- **Code Reviewer**: Enforces strict typing (mypy/pyright/TypeScript strict), PEP 8 formatting, docstrings, and diff minimality.
- **Security Auditor**: Holds unilateral veto power. Enforces Phenom permanent safety rules (Rules 1, 4, 7, 8, 9, 11), credential hygiene, zero unauthorized cloud transmission, and prompt injection defense.
- **QA Test Engineer**: Assesses test coverage, boundary cases, regression hazards, and verifiable execution proof.

### 2. Multi-Turn Synthetic Debate Protocol & Consensus Governance (SWM-01)
- **Turn Bounds**: Debates are strictly capped at 3 turns to prevent endless argument loops.
- **Weighted Consensus Formula**:
  $$\text{score} = 0.35 \times \text{security} + 0.30 \times \text{architect} + 0.20 \times \text{qa} + 0.15 \times \text{code}$$
  where `APPROVE = 1.0`, `REQUEST_CHANGES = 0.5`, `BLOCK = 0.0`.
- **Strict Tier 2+ Unanimous Gate**: Any proposal with risk tier >= 2 strictly requires unanimous `APPROVE` from Lead Architect, Security Auditor, and QA Engineer. If any of these 3 specialists does not approve, the proposal is gated with `GATED_PENDING_UNANIMOUS`.
- **Security Auditor Veto**: A single `BLOCK` from Security Auditor immediately halts autonomous approval regardless of overall score.
- **User Escalation Threshold (< 85%)**: If aggregate consensus is < 0.85 or gated pending unanimous sign-off, autonomous execution is suspended and an interactive Escalation Card is dispatched to the Cyber HUD.
- **Early Exit on Unanimous Consensus**: If all 4 specialists approve with consensus score >= 0.95 in Round 1 or 2, the debate concludes immediately without unnecessary turns.

### 3. ToolRegistry Risk Tiering & Previews (SAF-01)
- `swarm_get_debate_status`: Tier 0 (Read-Only query). Arguments: `SwarmGetDebateStatusArgs(debate_id: Optional[str] = None)`. Preview: `"Query status of specialist swarm synthetic debates (ID: {debate_id or 'recent'})"`.
- `swarm_dispatch_specialists`: Tier 1 (Reversible change). Arguments: `SwarmDispatchSpecialistsArgs(title: str, description: str, diff: Optional[str] = None, risk_tier: int = 1, max_rounds: int = 3)`. Preview: `"Dispatch multi-agent synthetic debate across 4 specialists for proposal: '{title}' (Tier {risk_tier})"`.
- `swarm_submit_user_decision`: Tier 1 (Reversible change). Arguments: `SwarmSubmitUserDecisionArgs(debate_id: str, decision: Literal['approve', 'reject'], reason: Optional[str] = None)`. Preview: `"Submit user decision '{decision}' for escalated debate '{debate_id}'"`.

### 4. Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `specialist_swarm_orchestrator.halt()` is synchronously invoked from `on_guardian_state_change("halted")`.
- Execution SLA: All active debate loops and async agent tasks are canceled synchronously in `< 25ms` (< 1ms typical).
- While halted, `specialist_swarm_orchestrator.is_halted` is `True`, all pending escalations are rejected with `PermissionError`, and subsequent tool calls or debate dispatches immediately raise `PermissionError`.
- Clean state reset and resumption via `specialist_swarm_orchestrator.reset()` when Guardian transitions to `idle`.

---

## 31. Self-Driving Visual Desktop Automation on Isolated Virtual Displays (Milestone 10.0 Phase 2)

### 1. Win32 Isolated Virtual Desktop Sandboxing (GUI-01)
- **Process Isolation**: Target applications are launched inside a dedicated hidden desktop surface created via Win32 `CreateDesktopW` with `STARTUPINFO.lpDesktop`.
- **Dual Backend**: `Win32VirtualDesktopBackend` for native execution (with dedicated clean worker threads preserving desktop thread affinity to prevent `ERROR_BUSY` 170) and `MockVirtualDesktopBackend` for headless and cross-platform test environments.
- **Zero Foreground Stealing**: Target apps run in the isolated desktop surface without stealing keyboard focus or disrupting the user's primary desktop session.

### 2. Zero Cursor Movement & RAM-Only Frame Capture (GUI-01)
- **Zero Physical Cursor Movement**: Mouse clicks, double clicks, drags, text typing, and keyboard shortcuts are injected via Win32 `PostMessageW` targeting the window's `HWND` using client-relative coordinates ($lParam = (y \ll 16) | (x \ \& \ 0xFFFF)$). The physical hardware mouse cursor is never moved.
- **RAM-Only Frame Capture**: Windows are captured into memory using Win32 `PrintWindow` with `PW_RENDERFULLCONTENT` into an in-memory DIB section and converted to a PIL Image. Zero screen frames are ever written to disk (pure RAM buffers).

### 3. Closed-Loop Visual Feedback & Sub-500ms Human Takeover Interrupt (GUI-01)
- **Closed-Loop Controller**: Pre-action capture -> client coordinate injection -> settle delay -> post-action capture -> perceptual visual delta computation using `DeltaDetector`.
- **Sub-500ms Human Takeover Interrupt**: Global OS hooks detect any physical mouse movement or keyboard press during automation. Execution aborts immediately (< 500ms SLA), plays `sound_fx.play_automation_halt()`, and dispatches `automation.takeover_prompt` to the desktop UI.
- **Cyber HUD Takeover Banner**: High-contrast neon orange / cyan banner with instant "Resume Automation" and "Abort Automation" decision controls.

### 4. ToolRegistry Risk Tiering & Previews (SAF-01)
- `gui_capture_virtual_screen`: Tier 0 (Read-Only query). Arguments: `GuiCaptureVirtualScreenArgs(session_id: str, hwnd: Optional[int] = None)`. Preview: `"Capture in-memory frame of virtual desktop '{session_id}' (RAM only, read-only)"`.
- `gui_launch_app_isolated`: Tier 1 (Reversible change). Arguments: `GuiLaunchAppIsolatedArgs(app_path: str, args: Optional[List[str]] = None, desktop_name: Optional[str] = None)`. Preview: `"Launch '{app_path}' inside isolated hidden virtual desktop '{desktop_name or 'auto'}'"`.
- `gui_execute_action`: Tier 1 (Reversible change). Arguments: `GuiExecuteActionArgs(session_id: str, hwnd: int, action_type: str, x: Optional[int] = None, y: Optional[int] = None, text: Optional[str] = None, key: Optional[str] = None)`. Preview: `"Execute '{action_type}' on window {hwnd} at ({x}, {y}) inside virtual desktop"`.
- `gui_close_isolated_desktop`: Tier 1 (Reversible change). Arguments: `GuiCloseIsolatedDesktopArgs(session_id: str)`. Preview: `"Terminate isolated virtual desktop session '{session_id}' and clean up all child processes"`.

### 5. Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `virtual_desktop_manager.halt()` is synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: All active virtual desktop sessions, child processes, and desktop handles are terminated synchronously in `< 25ms` (< 1ms typical) via direct process kill and `psutil` process tree teardown.
- All spawned PIDs are automatically registered with `guardian.track_pid(pid)`.
- While halted, all virtual desktop actions and launch attempts immediately raise `PermissionError`.
- Clean state reset and resumption via `virtual_desktop_manager.reset()` when Guardian transitions to `idle`.

---

## 32. Cognitive Mirror & Personalized Synthetic Twin Governance (Milestone 10.0 Phase 3)

### 1. In-Memory Credential Redaction & Zero Cloud Exfiltration (MIR-01, Rule 4, Rule 11)
- **Zero Cloud Exfiltration**: All cognitive profiling, feature modeling, and synthetic text generation execute strictly on-device in local Python memory and encrypted local SQLCipher storage. Zero profiles, samples, or derived traits are ever sent to cloud models or external endpoints.
- **In-Memory Credential Scrubbing**: Prior to feature extraction or persistent storage, all raw inputs (commits, markdown notes, emails, and logs) pass through `scrub_personal_secrets` which redacts API keys (`sk-*`, `nvapi-*`, `ghp_*`, `ya29.*`, `AKIA*`), private keys, passwords, bearer tokens, Windows user paths (`C:\Users\<user>\...`), and IP addresses with `[REDACTED_CREDENTIAL]`, `[REDACTED_PATH]`, or `[REDACTED_IP]`.

### 2. Encrypted SQLCipher Storage & Credential Key Retrieval (MIR-01)
- **AES-256 Storage**: All learned profiles, feature samples, and synthesis logs are stored exclusively in `services/backend/data/cognitive_profile.db` encrypted with SQLCipher v4 (AES-256).
- **Windows Credential Manager Key Management**: The database encryption key is securely stored and retrieved from Windows Credential Manager under the target name `Phenom/cognitive-mirror-key` (with fallback to `PHENOM_COGNITIVE_MIRROR_KEY`).

### 3. Multi-Dimensional Feature Modeling & Personalized Twin Generation (MIR-01)
- **Four Distinct Dimensions**:
  1. `git_style`: Conventional commits ratio, primary prefixes, average subject length, imperative mood ratio, subject casing, review tone (`direct`, `inquisitive`, `encouraging`), and architectural keywords.
  2. `obsidian_cadence`: Heading depth distribution, bullet marker preference (`-` vs `*`), wikilink density, tag density, callout frequency (`NOTE`, `TIP`, `WARNING`), and daily note section hierarchy.
  3. `communication_persona`: Preferred salutations, preferred signoffs, formality score ($0.0 - 1.0$), brevity score ($0.0 - 1.0$), bullet point preference, and characteristic phrases.
  4. `work_habits`: Diurnal 24-hour activity distribution, peak focus hours, break cadence, and quiet-time windows.
- **Synthetic Twin Synthesizer**: Generates contextual text adhering to the user's exact personal voice for commit messages, PR review comments, email draft replies, and Obsidian notes.

### 4. ToolRegistry Risk Tiering & Previews (SAF-01)
- `mirror_get_profile_stats`: Tier 0 (Read-Only query). Arguments: `MirrorGetProfileStatsArgs(dimension: Optional[MirrorDimension] = None)`. Preview: `"Retrieve cognitive mirror profile statistics [for dimension] (Read-Only)"`.
- `mirror_synthesize_text`: Tier 0 (Read-Only text generation). Arguments: `MirrorSynthesizeTextArgs(task: SynthesisTaskType, context_prompt: str, metadata: Optional[Dict[str, Any]] = None)`. Preview: `"Synthesize {task} in user's authentic style (Read-Only)"`.
- `mirror_learn_from_sources`: Tier 1 (Reversible change). Arguments: `MirrorLearnFromSourcesArgs(sources: List[str], max_items: Optional[int] = 100, repo_path: Optional[str] = None, vault_path: Optional[str] = None)`. Preview: `"Learn personal style from sources: {sources} (max {max_items} items)"`.
- `mirror_reset_profile`: Tier 1 (Reversible change). Arguments: `MirrorResetProfileArgs(dimensions: Optional[List[MirrorDimension]] = None)`. Preview: `"Reset cognitive mirror dimensions: {dimensions or 'all'}"`.

### 5. Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `cognitive_mirror.halt()` is synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: Operation cancellation occurs synchronously in `< 25ms` (< 1ms typical).
- While halted, all profile queries, learning operations, and synthesis requests immediately raise `PermissionError("Guardian kill switch is active. Cognitive mirror operations prohibited.")`.
- Clean state reset and resumption via `cognitive_mirror.reset()` when Guardian transitions to `idle`.

---

## 33. Encrypted Cross-Device Local P2P Mesh Governance (Milestone 10.0 Phase 4)

### 1. Sovereign Zero-Cloud Transport Security & Ephemeral QR Pairing (MSH-01, Rule 4, Rule 11)
- **Zero Cloud Exfiltration**: All peer discovery, pairing, telemetry streaming, approval card pushes, and GraphRAG synchronization execute exclusively over the local Wi-Fi subnet without any cloud relays, external proxies, or tracking endpoints.
- **ChaCha20-Poly1305 AEAD Transport**: Messages are encrypted using ChaCha20-Poly1305 authenticated symmetric encryption. Session keys are derived via HKDF-SHA256 (`info=b"phenom-p2p-session-v1"`). Nonce generation uses a 96-bit composite (4-byte random session prefix + 8-byte big-endian sequence counter). Replay attacks are rejected via a 64-bit sliding window bitmask.
- **Ephemeral 120s Single-Use QR Pairing**: Pairing generates a 256-bit cryptographically secure token valid for 120 seconds. The pairing payload is rendered into SVG and base64 PNG QR formats for Cyber HUD presentation. Verification uses timing-safe comparison (`hmac.compare_digest`), enforces TTL, and purges the token immediately on use (single-use invariant). Paired companion profiles are atomically persisted to `services/backend/data/paired_devices.json`.

### 2. Companion Approval Cards & Tier 3 Prohibition (MSH-01, Rule 1, Rule 3)
- **Interactive Companion Approvals**: Tier 1 and Tier 2 action requests can be dispatched to paired companion nodes as approval cards containing one-line summaries, item counts, target paths, and diff previews.
- **Cryptographic Decision Signatures**: Companion approval and rejection decisions require HMAC-SHA256 signatures validated against the companion device's shared secret.
- **Strict Rule 3 Invariant**: Tier 3 actions are categorically prohibited from companion push or remote approval. Explicit typed desktop input is strictly enforced.
- **Preconditions Re-Validation**: Delayed or late companion approvals undergo precondition re-validation (mtime, SHA-256 integrity, mode drift, and Guardian status) before execution.

### 3. Real-Time Telemetry Streaming, GraphRAG Delta Sync & Remote Voice Summon (MSH-01)
- **Non-Blocking Telemetry Streaming**: Swarm debate rounds, specialist critiques, consensus scores, and unattended mission milestones are streamed to companions through a bounded queue with background workers. Slow or dropped companion links can never block desktop swarm execution.
- **Bi-Directional GraphRAG Delta Synchronization**: Notes, nodes, and edges sync bi-directionally using Last-Write-Wins (LWW) conflict resolution backed by SHA-256 content checksums.
- **Full-Duplex Remote Voice Summon**: Full-duplex 16kHz 16-bit mono PCM audio streaming over local Wi-Fi enables remote voice summon. Companion speech detection triggers instant barge-in cancellation (< 5ms) to immediately abort active desktop TTS playback.

### 4. ToolRegistry Risk Tiering & Previews (SAF-01)
- `mesh_get_paired_devices`: Tier 0 (Read-Only query). Arguments: `MeshGetPairedDevicesArgs(include_offline: bool = True)`. Preview: `"List paired companion devices (include_offline=...) (Read-Only)"`.
- `mesh_generate_pairing_qr`: Tier 1 (Reversible change). Arguments: `MeshGeneratePairingQrArgs(ttl_seconds: int = 120)`. Preview: `"Generate single-use ephemeral QR pairing payload (valid for {ttl_seconds} seconds)"`.
- `mesh_sync_push`: Tier 1 (Reversible change). Arguments: `MeshSyncPushArgs(target_node_id: Optional[str] = None, sync_type: str = 'graphrag')`. Preview: `"Push local mesh synchronization update (sync_type='...', target='...')"`
- `mesh_unpair_device`: Tier 1 (Reversible change). Arguments: `MeshUnpairDeviceArgs(node_id: str)`. Preview: `"Revoke companion device pairing and authorization for node '{node_id}'"`.

### 5. Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `p2p_mesh_engine.halt()` is synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: Closes all active companion sockets, stops the UDP discovery broadcaster, and invalidates all pending ephemeral pairing tokens in `< 25ms` (< 1ms typical).
- While halted, all pairing operations, sync pushes, and message framing immediately raise `PermissionError("Operation blocked: P2P Mesh is halted by Guardian Kill Switch.")`.
- Clean state reset and resumption via `p2p_mesh_engine.reset()` when Guardian transitions to `idle`.

---

## 34. Dynamic Runtime Micro-Tool Synthesis & Execution Sandbox Guarantees (Milestone 11.0 Phase 1)

### 1. Deterministic AST Static Security Inspection (SYN-01, Rule 4, Rule 7, Rule 8)
- **Pre-Execution Static Validation**: Every candidate micro-tool function and test suite undergoes deterministic AST parsing via `ASTSafetyInspector` prior to disk persistence or subprocess execution. Syntax errors and empty code immediately evaluate to `is_safe=False` (Tier 3).
- **Prohibited Built-in Functions & Reflection**: Strict prohibition of dynamic evaluation and reflection escapes: `eval`, `exec`, `compile`, `globals`, `locals`, `__import__`, `breakpoint`, `input`, `getattr`, `setattr`, `delattr`. Banned dunder attributes (`__subclasses__`, `__bases__`, `__mro__`, `__globals__`, `__code__`, `__closure__`, `__builtins__`, `__dict__`, `__class__`) are rejected at AST parse time.
- **Prohibited Modules & Zero Network Exfiltration (Permanent Rule 4)**: Unauthorized system and networking libraries are blocked: `socket`, `subprocess`, `ctypes`, `winreg`, `urllib`, `requests`, `http`, `ftplib`, `telnetlib`, `aiohttp`, `httpx`, `multiprocessing`, `pty`, `importlib`, `shutil`, `pickle`, `asyncio.subprocess`.
- **Permanent File Deletion Prohibition (Permanent Rule 7)**: Delete means recycle bin. Destructive unlinking or directory pruning (`os.remove`, `os.unlink`, `os.rmdir`, `shutil.rmtree`, `Path.unlink`, `Path.rmdir`) is blocked at the AST level.
- **Zero Payment Primitives by Construction (Permanent Rule 8)**: Functions, arguments, classes, and identifiers referencing payment primitives (`pay`, `payment`, `checkout`, `credit_card`, `purchase`, `stripe`, `paypal`, `razorpay`, `bank_transfer`, `cvv`, `otp`) are rejected.

### 2. Restricted Subprocess Execution Sandbox (SYN-01)
- **In-Memory Stdio Protocol**: Micro-tools execute exclusively in-memory inside dedicated Python subprocesses via `sys.stdin` and `sys.stdout` JSON streams. Zero scratch files or temporary scripts are created in the repository worktree.
- **256 MB RSS Memory Ceiling**: A dedicated monitor thread polls process and child tree RSS memory every 20ms via `psutil`. If memory exceeds 256 MB, the entire process tree is terminated immediately with `killed_by_oom=True`.
- **Execution Timeout Hard Cap**: Subprocesses are bounded by a strict 5.0s default timeout (10.0s hard maximum). Any infinite loop is terminated via `proc.communicate(timeout=...)` and process tree termination (`timed_out=True`).
- **Offline Proxy Isolation**: Subprocesses inherit a sanitized environment stripped of all secret credentials (API keys, tokens, passwords) and injected with offline proxy traps (`HTTP_PROXY=http://127.0.0.1:0`, `HTTPS_PROXY=http://127.0.0.1:0`, `ALL_PROXY=http://127.0.0.1:0`, `PIP_NO_INDEX=1`, `PHENOM_OFFLINE_MODE=1`).

### 3. ToolRegistry Dynamic Hot-Loading & Governance (SAF-01)
- **Dynamic Pydantic v2 Schemas**: Synthesized micro-tools are registered in `ToolRegistry` with dynamically generated, sanitized Pydantic schemas (`re.sub(r'[^a-zA-Z0-9_]', '_', tool_name).capitalize() + 'Args'`).
- **Automated In-Sandbox Testing**: Candidate micro-tools must pass automated unit test suites inside `RestrictedToolSandbox` before hot-registration is permitted.
- **Dynamic Risk Tiering**:
  - `CAP_MATH` & `CAP_DATA_TRANSFORM`: Tier 0 eligible (pure calculation, regex, parsing, format transformation).
  - `CAP_FILE_READ` & `CAP_FILE_WRITE`: Tier 1 required with preview confirmation.
- **Synthesis Management Tools in ToolRegistry**:
  - `synthesize_custom_tool`: Tier 1 (Reversible change with preview). Synthesizes, AST-inspects, tests, and hot-registers a micro-tool.
  - `run_synthesized_tool`: Tier 1 (Reversible change with preview). Executes an active synthesized micro-tool in the restricted sandbox.
  - `list_synthesized_tools`: Tier 0 (Read-Only). Lists active synthesized micro-tools, execution counts, average durations, and capabilities.
  - `revoke_synthesized_tool`: Tier 1 (Reversible change with preview). Revokes and unregisters a synthesized tool from `ToolRegistry` and `SynthesizedToolManager`. Unregistered tools immediately fail with Tier 3 rejection.

### 4. Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `restricted_sandbox.halt()` and `dynamic_synthesizer_manager.halt()` are synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: Gathers and kills all active child subprocess trees and parent PIDs in `< 25ms` (< 1ms typical). Child PIDs are tracked with `guardian.track_pid` and untracked in a `finally` block.
- While halted, any call to `synthesize_custom_tool`, `run_synthesized_tool`, `execute_function`, or `execute_unit_test` immediately raises `PermissionError("Subprocess sandbox execution halted by Guardian kill switch.")`.
- Clean state reset and resumption via `restricted_sandbox.reset()` and `dynamic_synthesizer_manager.reset()` when Guardian transitions to `idle`.










---

## 35. Hierarchical Tree-of-Thought (ToT) Metacognitive Goal Engine & Self-Healing DAGs (Milestone 11.0 Phase 2)

### 1. Pre-Flight Safety Policy Enforcement (PLN-01, Rule 7, Rule 8)
- **Zero Payment Primitives by Construction (Permanent Rule 8)**: Pre-flight inspection prohibits goals or steps referencing payments, checkout, credit cards, bank transfers, CVV, or financial transactions. Unsafe goals immediately raise `PermissionError`.
- **Permanent File Deletion Prohibition (Permanent Rule 7)**: Delete means recycle bin. Commands invoking permanent unlinking, `rm -rf`, `shutil.rmtree`, or disk formatting are rejected with `ValueError`.
- **Graph Acyclicity & Parallel Roots**: Cycle detection via 3-color DFS traversal guarantees acyclicity before execution begins. Multiple parallel roots with empty `depends_on` are cleanly supported in the ready frontier.

### 2. Metacognitive Reflection & Dynamic Pruning (PLN-01)
- **Sliding-Window Outcome Signatures**: Step outcomes are deterministically hashed via `SHA256(node_id || action_type || status || error)` across a sliding history window ($K=10$).
- **Stagnation & Oscillation Heuristics**: $\ge 3$ repeated identical failures or cyclic ping-pong ($[X, Y, X, Y]$ or $[X, Y, Z, X, Y, Z]$) trigger automated branch pruning (`PRUNE_BRANCH`).
- **Dynamic Branch Pruning & Contingency Handoff**: Unviable branches are marked `pruned=True`, pending branch nodes are set to `PRUNED`, and execution seamlessly transitions to the highest-utility alternative contingency branch.

### 3. Self-Healing State Rollback Engine (PLN-01)
- **Deep-Copy Checkpoint Immutability**: Context snapshots are captured using `copy.deepcopy()`. Subsequent in-place modifications to shared context dictionaries cannot mutate historical snapshots.
- **Deterministic State Restoration**: When node retries are exhausted or loops are confirmed, `DAGStateManager.rollback_to_checkpoint()` restores shared context to the baseline snapshot, transitions affected nodes to `ROLLED_BACK`, and hands execution to contingency branches without global state corruption.

### 4. ToolRegistry Governance & Risk Tiers (SAF-01)
- `tot_create_goal_dag`: Tier 1 (Reversible change with preview). Arguments: `TotCreateGoalDagArgs(goal_description: str, max_contingency_branches: int, exploration_depth: int)`. Preview: `"Decompose objective into Hierarchical Tree-of-Thought Goal DAG..."`.
- `tot_execute_step`: Tier 1 (Reversible change with preview). Arguments: `TotExecuteStepArgs(dag_id: str, node_id: Optional[str])`. Preview: `"Execute step for Goal DAG '{dag_id}' (Node: {node_id or 'next ready'})"`.
- `tot_get_dag_status`: Tier 0 (Read-Only). Arguments: `TotGetDagStatusArgs(dag_id: str)`. Preview: `"Inspect Goal DAG topology and execution status for '{dag_id}' (Read-Only)"`.
- `tot_prune_branch`: Tier 1 (Reversible change with preview). Arguments: `TotPruneBranchArgs(dag_id: str, branch_id: str, reason: Optional[str])`. Preview: `"Prune branch '{branch_id}' in Goal DAG '{dag_id}'..."`.
- `tot_abort_goal`: Tier 1 (Reversible change with preview). Arguments: `TotAbortGoalArgs(dag_id: str, reason: Optional[str])`. Preview: `"Abort execution and roll back Goal DAG '{dag_id}'..."`.

### 5. Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `tot_planner.halt()`, `dag_state_manager.halt()`, and `metacognitive_reflector.halt()` are synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: Cancels all active step `asyncio.Task` handles, halts execution loops, and clears queues in `< 25ms` (< 1ms typical).
- While halted, all calls to `tot_create_goal_dag`, `tot_execute_step`, `tot_prune_branch`, `tot_abort_goal`, `get_ready_nodes`, `plan_objective`, and `create_checkpoint` immediately raise `PermissionError`.
- Clean state reset and resumption via `reset()` when Guardian transitions to `idle`.

## 36. Multi-Device Sensory Fabric: Companion Camera Vision & AirDrop-Style Encrypted P2P Drop (Milestone 11.0 Phase 3)

### 1. In-RAM Companion Camera Vision Invariants (SEN-01)
- **Zero Disk Writes (Permanent Rule 4)**: Live camera snapshots and compressed JPEG frames from paired mobile companion devices are decoded and held strictly in RAM (`io.BytesIO`, PIL `Image`). Frames are never persisted to disk or written to temporary cache files.
- **Bounded In-Memory Ring Buffer**: `InRamFrameBuffer` maintains a strict maximum capacity of 5 frames. Older frames are automatically evicted from memory.
- **Zero Cloud Exfiltration**: Camera frame inspection, whiteboard text capture, document OCR, and physical object queries are executed locally using `ScreenOCREngine` (EasyOCR) and `MoondreamVisionClient` (local Ollama Moondream2 model). Camera frames are never transmitted to cloud LLMs (Nemotron or OpenAI) without explicit user approval.

### 2. AirDrop-Style Encrypted P2P Media Drop Governance (MSH-02)
- **ChaCha20-Poly1305 Mesh Security**: Manifests and media chunks are transmitted across authenticated P2P mesh sessions.
- **Chunked Streaming & SHA-256 Integrity**: Transfers operate in 64 KB blocks with individual chunk SHA-256 validation and a whole-file SHA-256 accumulator. Files are committed to destination only after bit-for-bit digest verification. Corrupted chunks or checksum mismatches result in immediate staging file deletion.
- **Safe Intake Destinations**: Transfers are strictly routed to `vault/` (Markdown notes) or `services/backend/data/downloads/` (general media).
- **Strict Anti-Path Traversal**: Filenames are sanitized with `os.path.basename` and validated against canonical destination directories via `os.path.commonpath`. Traversal attempts (e.g. `../../Windows`) are rejected with `ValueError`.
- **Executable Extension Blocking**: Executable and script extensions (`.exe`, `.bat`, `.cmd`, `.ps1`, `.msi`, `.vbs`, `.sh`, `.bin`, `.jar`, `.scr`, `.reg`, etc.) are permanently blocked and rejected prior to intake.
- **Non-Destructive Collision Handling**: Intake files conflicting with existing names are renamed using non-destructive numbering (e.g. `document (1).md`) to prevent silent overwrite of user notes.

### 3. ToolRegistry Governance & Risk Tiers (SAF-01)
- `camera_get_companion_frame`: Tier 0 (Read-Only). Arguments: `CameraGetFrameArgs(node_id: Optional[str])`. Preview: `"Inspect latest in-RAM companion camera frame (Read-Only)"`.
- `camera_analyze_object_or_ocr`: Tier 0 (Read-Only). Arguments: `CameraAnalyzeArgs(task_type: Literal['ocr', 'whiteboard', 'object'], prompt: Optional[str])`. Preview: `"Analyze companion camera frame via local {task_type} engine (Read-Only)"`.
- `media_drop_send_file`: Tier 1 (Reversible change with preview). Arguments: `MediaDropSendFileArgs(file_path: str, target_node_id: str, destination: Literal['vault', 'downloads'])`. Preview: `"Send file '{file_path}' to companion '{target_node_id}' (destination: {destination})"`.
- `media_drop_get_history`: Tier 0 (Read-Only). Arguments: `MediaDropGetHistoryArgs(limit: int)`. Preview: `"Query P2P media drop transfer history (Read-Only)"`.

### 4. Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `companion_camera_streamer.halt()` and `media_drop_manager.halt()` are synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: Wipes in-RAM camera ring buffers, aborts active streaming tasks, marks in-flight media drops as `ABORTED`, closes open file handles, and deletes partial `.part` staging files in `< 25ms` (< 1.0ms typical).
- While halted, all calls to `ingest_frame`, `get_latest_frame`, `analyze_frame`, `create_send_manifest`, `read_file_chunk`, `receive_manifest`, and `receive_chunk` immediately raise `PermissionError`.
- Clean state reset and resumption via `reset()` when Guardian transitions to `idle`.

## 37. Milestone 11.0 Full Safety Audit & Universal Guardian SLA Sign-Off (Phase 4)

### 1. Comprehensive Safety Audit Verification (SAF-01)
- **Tool Inventory**: All 13 Milestone 11.0 tools across Phases 1–3 (`synthesize_custom_tool`, `run_synthesized_tool`, `list_synthesized_tools`, `revoke_synthesized_tool`, `tot_create_goal_dag`, `tot_execute_step`, `tot_get_dag_status`, `tot_prune_branch`, `tot_abort_goal`, `camera_get_companion_frame`, `camera_analyze_object_or_ocr`, `media_drop_send_file`, `media_drop_get_history`) are registered in `ToolRegistry` with validated risk tiers (Tier 0 or 1), Pydantic v2 schemas, and callable human-readable preview functions.
- **Permanent Safety Rules Adherence**:
  - **Rule 1 (Tier Classification)**: 100% of tools explicitly classified as Tier 0 (Read-Only) or Tier 1 (Reversible with preview). Zero unclassified or rogue tools.
  - **Rule 4 (Privacy & Local Compute)**: Zero cloud exfiltration. Camera frames held exclusively in RAM (`InRamFrameBuffer`, max 5 frames, zero disk writes). Local OCR and VLM processing. P2P drops validate boundaries against destination directories.
  - **Rule 7 (Recycle Bin Only)**: Delete operations in AST inspection reject `os.unlink` and `os.remove`.
  - **Rule 8 (Zero Payments)**: Payment and checkout primitives rejected deterministically by AST inspector and ToT goal planner.
  - **Rule 9 (Email & Calendar Boundaries)**: Drafts only, never send emails. Calendar events create-only.
  - **Rule 11 (Zero Secrets Exposure)**: No credentials, tokens, or private keys exposed in tool schemas or logs.

### 2. Universal Guardian Kill Switch SLA Benchmark (SAF-02)
- **Universal Synchronous Benchmark**: 100 consecutive synchronous halt cycles executed across all Milestone 11 subsystems (`RestrictedToolSandbox`, `TreeOfThoughtPlanner`, `DAGStateManager`, `MetacognitiveReflector`, `CompanionCameraStreamer`, `P2PMediaDropManager`).
- **Benchmark Results**:
  - **Average Latency**: **0.5512 ms** (Target: `< 1.0 ms`)
  - **Maximum Latency**: **2.2893 ms** (Hard SLA: `< 25.0 ms`)
  - **Minimum Latency**: **0.3377 ms**
- **Lockdown Invariants**: All subsystems enter immediate fail-closed state upon halt, wiping camera RAM buffers, aborting file drops, cancelling active asyncio tasks, and raising `PermissionError` on all speculative operations. Subsystems fully restore clean operations upon `guardian.resume()`.

### 3. End-to-End Multi-Component Simulation
- Chained ToT Metacognitive Goal Planning (`PLN-01`) -> Companion Camera Vision Ingestion (`SEN-01`) -> Dynamic Micro-Tool Synthesis (`SYN-01`) -> Sandbox Execution & Trace Reflection (`PLN-01`) -> AirDrop P2P Media Drop to Obsidian Vault (`MSH-02`) -> Universal Guardian Kill Switch Halt (`SAF-02`).
- Measured E2E Guardian halt latency: **0.9102 ms**, demonstrating complete sovereign OS safety and integration across physical companion devices and neural planning loops.

## 38. Sovereign Neuro-Symbolic Sleep & Dream Consolidation Engine (Milestone 12.0 Phase 1)

### 1. Offline Memory Consolidation Invariants (DRM-01)
- **100% On-Device Privacy (Permanent Rule 4)**: All episodic trace replays, heuristic abstraction, graph compaction, and entity deduplication execute entirely locally on-device. Personal execution traces, tool arguments, and conceptual schemas are never transmitted to cloud LLMs.
- **Idle Threshold Gating**: Dream cycles execute automatically only when system inactivity exceeds the configured idle threshold (default: 15 minutes / 900 seconds) or during quiet-time hours. Manual invocation requires explicit `force=True` parameter.
- **Non-Destructive Graph Optimization**: The `GraphCompactor` purges only demonstrably dead edges (dangling references where source or target is missing) and decayed transient edges (`transient_ref`, `ephemeral_mention`) exceeding the staleness threshold (default: 14 days). Valid semantic associations and permanent vault links are strictly preserved.
- **Safe Entity Merging**: Near-duplicate entity consolidation re-routes bidirectional in/out edges and merges metadata/tags into the canonical node prior to deleting duplicate nodes, preventing edge loss.

### 2. ToolRegistry Governance & Risk Tiers (SAF-01)
- `dream_get_status`: Tier 0 (Read-Only). Arguments: `DreamGetStatusArgs(include_report: bool)`. Preview: `"Query Neuro-Symbolic Dream Consolidation Engine status and telemetry (Read-Only)"`.
- `dream_trigger_cycle`: Tier 1 (Reversible change with preview). Arguments: `DreamTriggerCycleArgs(force: bool, max_episodes: int)`. Preview: `"Trigger Neuro-Symbolic Sleep & Dream memory consolidation cycle (force={force}, max_episodes={max_episodes})"`.
- `dream_prune_stale_memory`: Tier 1 (Reversible change with preview). Arguments: `DreamPruneStaleArgs(decay_days_threshold: int, dry_run: bool)`. Preview: `"Prune dead links and stale graph edges (decay threshold: {decay_days_threshold} days, dry_run={dry_run})"`.

### 3. Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `dream_engine.halt()` is synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: Immediately terminates active dream cycle loops, marks engine state as `HALTED`, releases in-memory locks, and broadcasts state change to Cyber HUD in `< 25ms` (< 1.0ms typical, measured **0.2766 ms** avg across 50 cycles).
- While halted, all calls to `run_dream_cycle`, `prune_stale_memory`, and associated Tier 1 tools immediately raise `PermissionError`.
- Clean state reset and resumption via `reset()` when Guardian transitions to `idle`.


## 39. Transparent Holographic Spatial Canvas & Ghost Annotations Governance (Milestone 12.0 Phase 2)

### 1. Spatial Overlay & Tracking Invariants (OVR-01)
- **Zero Pixel Capture Exfiltration (Permanent Rule 4)**: The spatial focus tracker queries only window handles (`hwnd`), sanitized titles, process metadata (`pid`, `process_name`), and screen bounding rectangles (`left`, `top`, `right`, `bottom`) for coordinate anchoring. No screen framebuffer pixels, window contents, or private user text are captured, stored, or exfiltrated.
- **DirectComposition & Non-Intrusive Passthrough**: The holographic canvas operates via DirectComposition-compatible transparent window layered styles (`WS_EX_LAYERED`, `WS_EX_TRANSPARENT`). Click-through mode (`click_through=True`) is enabled by default to prevent intercepting user mouse clicks intended for underlying applications (IDEs, browsers, terminals).
- **TTL-Based Ephemeral Ghost Annotations**: Ghost annotations feature bounded time-to-live (`ttl_seconds`, default: 300s) ensuring obsolete or forgotten contextual suggestions automatically expire and purge from RAM.
- **Fail-Closed Dismissal**: Any annotation can be immediately dismissed via tool, WebSocket command, or Cyber HUD UI.

### 2. ToolRegistry Governance & Risk Tiers (SAF-01)
- `spatial_get_focus`: **Tier 0** (Read-Only). Arguments: `SpatialGetFocusArgs`. Preview: `"Inspect current desktop foreground window focus and spatial overlay state (Read-Only)"`.
- `spatial_show_overlay`: **Tier 1** (Reversible change with preview). Arguments: `SpatialShowOverlayArgs(click_through: bool, direct_comp: bool)`. Preview: `"Activate transparent holographic desktop spatial canvas (click_through={click_through})"`.
- `spatial_hide_overlay`: **Tier 1** (Reversible change with preview). Arguments: `SpatialHideOverlayArgs`. Preview: `"Hide transparent holographic desktop spatial canvas"`.
- `spatial_add_annotation`: **Tier 1** (Reversible change with preview). Arguments: `SpatialAddAnnotationArgs(...)`. Preview: `"Add floating ghost annotation: '{title}' anchored at {anchor}"`.
- `spatial_dismiss_annotation`: **Tier 1** (Reversible change with preview). Arguments: `SpatialDismissAnnotationArgs(annotation_id: str)`. Preview: `"Dismiss floating ghost annotation '{annotation_id}'"`.
- `spatial_toggle_click_through`: **Tier 1** (Reversible change with preview). Arguments: `SpatialToggleClickThroughArgs(enabled: bool)`. Preview: `"Set spatial canvas click-through to {enabled}"`.

### 3. Sub-10ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `spatial_canvas_manager.halt()` is synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: Immediately dismisses the overlay (`is_active = False`), wipes all floating ghost annotations (`annotations.clear()`), resets click-through mode, halts the underlying `FocusTrackingEngine`, and disallows further operations in `< 10ms` (hard SLA: `< 25ms`; benchmarked at **0.0015 ms** average across 100 cycles).
- While halted, all attempts to invoke `show_overlay`, `add_annotation`, or any Tier 1 spatial tool immediately raise `PermissionError`.
- Clean state reset and resumption via `reset()` when Guardian transitions to `idle`.


## 40. Proactive Sensory Event Bus & Ambient Feedback Fabric Governance (Milestone 12.0 Phase 3)

### 1. Event Ingestion & Real-Time Privacy Scrubbing (PRX-01, Permanent Rule 11)
- **Zero-Secrets Leakage Invariant (Permanent Rule 11)**: All Win32 system events (focus changes, window crashes, terminal error codes, dialogs) are passed through `PrivacyScrubber` before entering in-memory ring buffers, subscriber callbacks, logs, or UI feeds.
- **Redaction Coverage**: Automatically replaces OpenAI (`sk-...`), Anthropic (`sk-ant-...`), HuggingFace (`hf_...`), GitHub PATs (`ghp_...`), GitLab tokens (`glpat-...`), AWS Access Key IDs (`AKIA...`), Bearer tokens, RSA private key blocks, password key-value assignments, and credit card numbers with typed `[REDACTED_*]` tokens.
- **Local Bounded Memory**: Event bus buffers are strictly bounded to 200 events in RAM, preventing unbounded memory growth.

### 2. Ambient Audio Cues & Local WebRTC Streaming (FBK-01)
- **Non-Jarring Procedural Audio**: Ambient audio cues are synthesized in-memory using smooth cosine envelope windowing and constant-power stereo spatial panning (-1.0 to 1.0) without requiring external sound binaries or network requests.
- **Strict Local Wi-Fi Mirroring**: The `LocalWebRTCMirror` streams screen and spatial canvas exclusively to paired companion devices over local network interfaces. Cloud STUN/TURN relays are strictly prohibited to prevent outbound video exfiltration.

### 3. ToolRegistry Governance & Risk Tiers (SAF-01)
- `proactive_get_bus_status`: **Tier 0** (Read-Only). Arguments: `ProactiveGetBusStatusArgs`. Preview: `"Inspect proactive sensory event bus status and privacy scrubber metrics (Read-Only)"`.
- `proactive_ingest_event`: **Tier 1** (Reversible change with preview). Arguments: `ProactiveIngestEventArgs(...)`. Preview: `"Ingest Win32 context event: {event_type} from {process_name}"`.
- `ambient_trigger_audio_cue`: **Tier 1** (Reversible change with preview). Arguments: `AmbientTriggerAudioCueArgs(cue_type: str, spatial_pan: float, volume: float)`. Preview: `"Play ambient audio cue '{cue_type}' (pan={spatial_pan})"`.
- `webrtc_init_mirror_session`: **Tier 1** (Reversible change with preview). Arguments: `WebRTCInitMirrorSessionArgs(...)`. Preview: `"Establish local WebRTC screen mirror session to companion device '{device_id}'"`.
- `webrtc_terminate_mirror`: **Tier 1** (Reversible change with preview). Arguments: `WebRTCTerminateMirrorArgs(session_id: str)`. Preview: `"Terminate local WebRTC mirror session '{session_id}'"`.

### 4. Sub-10ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `proactive_event_bus.halt()`, `ambient_feedback_synthesizer.halt()`, and `local_webrtc_mirror.halt()` are synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: Immediately ceases event ingestion, wipes unhandled dispatch queues, mutes all synthesized audio generation, and tears down all active local WebRTC mirror sessions in `< 10ms` (hard SLA: `< 25ms`; benchmarked at **0.0008 ms** average across 100 cycles).
- While halted, all calls to `ingest_event`, `trigger_cue`, `init_session`, and associated Tier 1 tools fail closed with `PermissionError`.
- Clean state reset and resumption via `reset()` when Guardian transitions to `idle`.


## 41. Milestone 12.0 Full Safety Audit & Universal Guardian SLA Sign-Off (Phase 4)

### 1. Comprehensive Safety Audit Verification (SAF-01)
- **14 Tools Audited & Verified**:
  - **Tier 0 Read-Only Tools (3)**: `dream_get_status`, `spatial_get_focus`, `proactive_get_bus_status`.
  - **Tier 1 Reversible Tools (11)**: `dream_trigger_cycle`, `dream_prune_stale_memory`, `spatial_show_overlay`, `spatial_hide_overlay`, `spatial_add_annotation`, `spatial_dismiss_annotation`, `spatial_toggle_click_through`, `proactive_ingest_event`, `ambient_trigger_audio_cue`, `webrtc_init_mirror_session`, `webrtc_terminate_mirror`.
- **Permanent Rules Compliance**:
  - **Rule 1 (Safety Layer Wrapping)**: Every single tool is registered in `ToolRegistry` with Pydantic v2 schemas and preview functions.
  - **Rule 4 (Zero Cloud Exfiltration)**: Private traces, dream schemas, window titles, and video mirrors operate entirely on-device with local Wi-Fi only.
  - **Rule 7 (Recycle Bin Only)**: Memory compaction prunes only demonstrably dead/orphaned references; zero destructive file deletion.
  - **Rule 8 (Zero Financial Transactions)**: Strictly informational; no payment mechanisms.
  - **Rule 9 (Email & Calendar Boundaries)**: Drafts only, never send emails. Calendar events create-only.
  - **Rule 11 (Real-Time Privacy Scrubbing)**: In-memory regex scrubber redacting OpenAI/Anthropic/HF keys, PATs, AWS tokens, private keys, passwords, and credit cards before event propagation.

### 2. Universal Guardian Kill Switch SLA Benchmark (SAF-02)
- **Universal Synchronous Benchmark**: 100 consecutive synchronous halt cycles executed simultaneously across all 6 Milestone 12 subsystems (`DreamConsolidationEngine`, `SpatialCanvasManager`, `FocusTrackingEngine`, `ProactiveEventBus`, `AmbientFeedbackSynthesizer`, `LocalWebRTCMirror`).
- **Benchmark Results**:
  - **Average Latency**: **0.0025 ms** (Target: `< 1.0 ms`)
  - **Maximum Latency**: **0.0163 ms** (Hard SLA: `< 25.0 ms`)
  - **Minimum Latency**: **0.0018 ms**
- **Lockdown Invariants**: All subsystems enter immediate fail-closed state upon halt, wiping all active annotations, hiding transparent overlays, disconnecting companion WebRTC mirror streams, terminating dream consolidation cycles, and raising `PermissionError` on all Tier 1 tools. Subsystems fully restore clean operations upon `guardian.resume()`.

### 3. End-to-End Multi-Component Simulation
- Chained Win32 Proactive Event Ingestion with Privacy Scrubbing (`PRX-01`) -> Ambient Spatial Audio Feedback (`FBK-01`) -> DirectComposition Spatial Canvas & Anchored Ghost Annotations (`OVR-01`) -> Offline Neuro-Symbolic Sleep & Dream Memory Consolidation (`DRM-01`) -> Local WebRTC Screen Streaming (`FBK-01`) -> Universal Guardian Kill Switch Lockdown (`SAF-02`).
- Measured E2E Guardian halt latency: **0.5104 ms**, demonstrating complete sovereign desktop operating layer safety and integration.


## 42. Autonomous Neuro-Evolution & Local LoRA Adapter Governance (Milestone 13.0 Phase 1)

### 1. On-Device Parameter Tuning Invariants (EVO-01, Permanent Rule 4)
- **100% On-Device Local Training (Permanent Rule 4)**: All synthetic instruction distillation, parameter-efficient LoRA fine-tuning, and regression benchmarking execute strictly locally on the user's NVIDIA GPU. Dataset instruction pairs, model weights, and gradient updates are never transmitted to external cloud endpoints.
- **Regression Prevention & Benchmark Gating**: Before any trained adapter can be promoted or activated, it must pass the local evaluation probe with an accuracy score $\ge 0.85$ and zero regressions detected on core operating commands. Failing adapters are automatically marked as `QUARANTINED` and blocked from activation.
- **Atomic Rollback Guarantee**: The system retains previous adapter states and enables instantaneous fallback to the prior stable checkpoint or unadapted base model weights (`reset_to_base=True`).

### 2. ToolRegistry Governance & Risk Tiers (SAF-01)
- `evolution_get_status`: **Tier 0** (Read-Only). Arguments: `EvolutionGetStatusArgs`. Preview: `"Inspect Neuro-Evolution status and active LoRA adapters (Read-Only)"`.
- `evolution_distill_instructions`: **Tier 1** (Reversible change with preview). Arguments: `EvolutionDistillInstructionsArgs(domain: Optional[str], max_pairs: int)`. Preview: `"Distill synthetic instruction training pairs"`.
- `evolution_train_adapter`: **Tier 1** (Reversible change with preview). Arguments: `EvolutionTrainAdapterArgs(...)`. Preview: `"Train local LoRA adapter '{adapter_id}' for domain '{domain}'"`.
- `evolution_activate_adapter`: **Tier 1** (Reversible change with preview). Arguments: `EvolutionActivateAdapterArgs(adapter_id: str)`. Preview: `"Mount and activate validated LoRA adapter '{adapter_id}'"`.
- `evolution_rollback_adapter`: **Tier 1** (Reversible change with preview). Arguments: `EvolutionRollbackAdapterArgs(...)`. Preview: `"Rollback active adapter to '{target_adapter_id}'"`.

### 3. Sub-10ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `local_adapter_manager.halt()` is synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: Immediately ceases active adapter fine-tuning, aborts evaluation routines, and prevents adapter mounting/rollback in `< 10ms` (hard SLA: `< 25ms`; benchmarked at **0.0003 ms** average across 100 cycles).
- While halted, all calls to `train_adapter`, `activate_adapter`, `rollback_adapter`, and associated Tier 1 tools fail closed with `PermissionError`.
- Clean state reset and resumption via `reset()` when Guardian transitions to `idle`.


## 43. Multi-Modal Holographic Workspace & Spatial 3D Volumetric Canvas (Milestone 13.0 Phase 2)

### 1. Spatial Volumetric Invariants & Privacy Guarantees (VOL-01, Permanent Rule 4)
- **Zero Camera Pixel Exfiltration (Permanent Rule 4)**: Touchless vision gesture tracking operates purely by consuming numeric 3D Cartesian landmark vectors (`Vector3D(x, y, z)` and normalized pinch distances). Zero camera frames, video feeds, or pixel arrays are ever saved, cached to disk, logged, or exfiltrated.
- **Fail-Closed 3D Spatial Scene Graph**: 3D spatial node positioning, raycasting intersections, and projection coordinate transforms (cylindrical, spherical, planar) run completely in local RAM.
- **Physical Palm Dismissal**: Physical hand gestures (e.g. `PALM_DISMISS`) allow touchless wiping of unpinned ephemeral 3D cards, providing rapid tactile spatial control.

### 2. ToolRegistry Governance & Risk Tiers (SAF-01)
- `volumetric_get_status`: **Tier 0** (Read-Only). Arguments: `VolumetricGetWorkspaceStatusArgs`. Preview: `"Inspect 3D holographic spatial workspace state and active nodes (Read-Only)"`.
- `volumetric_set_projection`: **Tier 1** (Reversible change with preview). Arguments: `VolumetricSetProjectionModeArgs(mode: str)`. Preview: `"Switch 3D holographic projection geometry to '{mode}'"`.
- `volumetric_spawn_node`: **Tier 1** (Reversible change with preview). Arguments: `VolumetricSpawnNodeArgs(label: str, x: float, y: float, z: float, color_hex: str, depth_layer: int, is_pinned: bool)`. Preview: `"Spawn 3D volumetric node '{label}' at ({x}, {y}, {z}) [layer {depth_layer}]"`.
- `volumetric_clear_canvas`: **Tier 1** (Reversible change with preview). Arguments: `VolumetricClearCanvasArgs`. Preview: `"Clear all spatial nodes from the 3D volumetric canvas scene"`.
- `volumetric_ingest_gesture`: **Tier 1** (Reversible change with preview). Arguments: `VolumetricIngestGestureArgs(gesture_type: str, confidence: float, x: float, y: float, z: float, pinch_distance: Optional[float])`. Preview: `"Ingest vision gesture '{gesture_type}' (confidence={confidence})"`.

### 3. Sub-10ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `volumetric_canvas_manager.halt()` and `vision_gesture_tracker.halt()` are synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: Immediately clears all active 3D spatial nodes, unsets selected raycast targets, terminates active gesture listeners, and disables projection rendering in `< 10ms` (hard SLA: `< 25ms`).
- While halted, all calls to `set_projection_mode`, `spawn_node`, `remove_node`, `clear_canvas`, `ingest_gesture`, and associated Tier 1 tools fail closed with `PermissionError`.
- Clean state reset and resumption via `reset()` when Guardian transitions to `idle`.


## 44. Cross-Device Distributed Swarm & Offline Mesh P2P Compute Offloading (Milestone 13.0 Phase 3)

### 1. Swarm Mesh Invariants & Local Privacy Guarantees (SWM-01, Permanent Rule 4, Rule 11)
- **100% Offline Local Wi-Fi Mesh (Permanent Rule 4)**: All compute task partitioning (speculative decoding tokens, embedding batches, document indexing slices) executes strictly across authenticated local network peers (desktop GPU, laptop, mobile companion). Zero compute requests, token sequences, or embeddings are ever routed through external cloud servers.
- **Hardware & Power Safety Constraints**: Swarm workload scheduler continuously evaluates peer battery percentage, AC power connection, and thermal throttling status. Nodes with battery below 20% on DC power or experiencing thermal throttling are automatically excluded from compute tasks to preserve device health and user battery life.
- **Zero Secrets Exfiltration (Permanent Rule 11)**: All peer telemetry broadcasts to the Electron Cyber HUD strictly omit internal cryptographic session keys, authorization tokens, and private file contents.

### 2. ToolRegistry Governance & Risk Tiers (SAF-01)
- `swarm_compute_get_topology`: **Tier 0** (Read-Only). Arguments: `SwarmComputeGetTopologyArgs`. Preview: `"Inspect local swarm compute cluster nodes and hardware metrics (Read-Only)"`.
- `swarm_compute_register_node`: **Tier 1** (Reversible change with preview). Arguments: `SwarmComputeRegisterNodeArgs(node_id, device_name, node_type, available_vram_mb, available_ram_mb, battery_percent, is_plugged_in, thermal_throttled, compute_flops_rating)`. Preview: `"Register swarm peer node '{node_id}' ({device_name}) [type: {node_type}, battery: {battery_percent}%]"`.
- `swarm_compute_offload_workload`: **Tier 1** (Reversible change with preview). Arguments: `SwarmComputeOffloadWorkloadArgs(workload_type, items_count, preferred_node_id)`. Preview: `"Offload compute workload '{workload_type}' ({items_count} items) across local mesh cluster"`.
- `swarm_compute_abort_workload`: **Tier 1** (Reversible change with preview). Arguments: `SwarmComputeAbortWorkloadArgs(task_id)`. Preview: `"Abort in-flight swarm compute task '{task_id}'"`.

### 3. Sub-10ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `swarm_workload_scheduler.halt()` is synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: Immediately aborts all in-flight compute tasks, severs active peer offload sessions, resets cluster scheduling queues, and prevents task dispatching in `< 10ms` (hard SLA: `< 25ms`).
- While halted, all calls to `swarm_compute_register_node`, `swarm_compute_offload_workload`, `swarm_compute_abort_workload`, and associated Tier 1 tools fail closed with `PermissionError`.
- Clean state reset and resumption via `reset()` when Guardian transitions to `idle`.


## 45. Deep OS Telemetry & Autonomous Environment Self-Healing Fabric (Milestone 13.0 Phase 4)

### 1. Kernel Telemetry & Self-Healing Invariants (KER-01, Rules 1, 4, 7, 11)
- **Deterministic Constrained Healing Only (Permanent Rule 1)**: Self-healing remediation actions are strictly deterministic (`INSTALL_PINNED_PACKAGE`, `PURGE_CORRUPT_CACHE`, `RELOAD_VENV_MANIFEST`, `RESTART_SUBPROCESS_DAEMON`). Arbitrary shell execution or unsupervised script execution is prohibited.
- **Strict Tier 1 User Confirmation (Rule 1)**: Any environment remediation patch modifies system software state and categorically requires user preview approval (`kernel_apply_healing_patch` is Tier 1).
- **100% On-Device Local Telemetry (Rule 4)**: All ETW system event capture, crash triage, and venv inspection execute strictly locally in memory. Zero stack traces, process telemetry, or memory dumps are ever transmitted to external cloud endpoints.
- **Recycle Bin Deletion for Cache Purges (Rule 7)**: All cache clearing and temporary directory resets use `send2trash` to ensure no irrecoverable file deletion occurs.
- **In-Memory Privacy Scrubbing (Rule 11)**: All process stack traces, terminal exception strings, and exception context frames are automatically sanitized through `PrivacyScrubber` before being logged, persisted, or broadcast over WebSockets to the desktop Cyber HUD.

### 2. ToolRegistry Governance & Risk Tiers (SAF-01)
- `kernel_get_telemetry_status`: **Tier 0** (Read-Only). Arguments: `KernelGetTelemetryStatusArgs`. Preview: `"Inspect OS kernel telemetry, crash logs, and self-healing fabric state (Read-Only)"`.
- `kernel_diagnose_crash`: **Tier 0** (Read-Only). Arguments: `KernelDiagnoseCrashArgs(process_name, exception_code, stack_trace)`. Preview: `"Diagnose process crash in '{process_name}' (code: {exception_code}) [Read-Only]"`.
- `kernel_scan_venv_discrepancies`: **Tier 0** (Read-Only). Arguments: `KernelScanVenvDiscrepanciesArgs`. Preview: `"Scan Python virtual environment for missing or corrupted dependencies (Read-Only)"`.
- `kernel_apply_healing_patch`: **Tier 1** (Reversible change with preview). Arguments: `KernelApplyHealingPatchArgs(patch_id)`. Preview: `"Apply self-healing remediation patch '{patch_id}' to repair virtual environment"`.

### 3. Sub-10ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `kernel_telemetry_fabric.halt()` is synchronously invoked from `on_guardian_state_change("halted")`.
- **Execution SLA**: Ceases active ETW listeners, cancels in-flight patch execution routines, and fail-closes tool endpoints in `< 10ms` (hard SLA: `< 25ms`).
- While halted, all calls to `kernel_apply_healing_patch` and related mutation tools fail closed with `PermissionError`.
- Clean state reset and resumption via `reset()` when Guardian transitions to `idle`.


## 46. Milestone 13.0 Comprehensive Safety Audit (SAF-01, SAF-02)

### 1. Complete Tool Inventory (18 Tools Across 4 Phases)
- **Phase 1: Autonomous Self-Improving Engine & Dynamic LoRA Tuning (`EVO-01`)**
  - `evolution_get_status`: Tier 0
  - `evolution_distill_instructions`: Tier 1
  - `evolution_train_adapter`: Tier 1
  - `evolution_activate_adapter`: Tier 1
  - `evolution_rollback_adapter`: Tier 1
- **Phase 2: Multi-Modal Holographic Workspace & Spatial 3D Volumetric Canvas (`VOL-01`)**
  - `volumetric_get_status`: Tier 0
  - `volumetric_set_projection`: Tier 1
  - `volumetric_spawn_node`: Tier 1
  - `volumetric_clear_canvas`: Tier 1
  - `volumetric_ingest_gesture`: Tier 1
- **Phase 3: Cross-Device Distributed Swarm & Offline Mesh P2P Compute Offloading (`SWM-01`)**
  - `swarm_compute_get_topology`: Tier 0
  - `swarm_compute_register_node`: Tier 1
  - `swarm_compute_offload_workload`: Tier 1
  - `swarm_compute_abort_workload`: Tier 1
- **Phase 4: Deep OS Telemetry & Autonomous Environment Self-Healing Fabric (`KER-01`)**
  - `kernel_get_telemetry_status`: Tier 0
  - `kernel_diagnose_crash`: Tier 0
  - `kernel_scan_venv_discrepancies`: Tier 0
  - `kernel_apply_healing_patch`: Tier 1

### 2. Universal Guardian Kill Switch SLA Benchmark (SAF-02)
- **Universal Synchronous Benchmark**: 100 consecutive synchronous halt cycles executed simultaneously across all 6 Milestone 13 subsystems (`LocalAdapterManager`, `VolumetricCanvasManager`, `VisionGestureTracker`, `SwarmNodeManager`, `SwarmWorkloadScheduler`, `KernelTelemetryFabric`).
- Hard SLA: `< 25.0 ms`, assert typical `< 1.0 ms`.


## 47. Omni-Modal Spatial Telepresence & Zero-Copy Audio/Video Fabric (Milestone 14.0 Phase 1)

### 1. Telepresence & Privacy Invariants (AVP-01)
- **100% Zero-Copy / Zero Disk Persistence (Permanent Rule 4)**: Camera pixel frames and uncompressed audio buffers are processed entirely in transient ring buffers (`collections.deque(maxlen=100)`). No image files, video streams, or raw audio waveforms are ever written to disk or transmitted to any cloud endpoint.
- **Physical & Software Privacy Shutters**: Camera and microphone sensors support immediate software toggling (`ACTIVE`, `MUTED`, `SHUTTERED`, `DISABLED`). When `camera_state` is `SHUTTERED`, all landmark parsing is suspended and FPS reports 0. When `microphone_state` is `MUTED`, RMS energy is pegged to 0.
- **Local Ambient Perception**: Room occupancy and voice activity probability metrics are calculated purely on-device without exfiltrating biometric data or voiceprints.

### 2. ToolRegistry Governance & Risk Tiers (SAF-01)
- `telepresence_get_status`: **Tier 0** (Read-Only). Arguments: `TelepresenceGetStatusArgs`. Preview: `"Inspect AV telepresence session state, microphone/camera statuses, and ambient presence metrics (Read-Only)"`.
- `telepresence_set_microphone`: **Tier 1** (Reversible change with preview). Arguments: `TelepresenceSetMicrophoneArgs(state: SensorState, gain: float)`. Preview: `"Set microphone hardware state to {state} (Gain: {gain:.1f}x)"`.
- `telepresence_set_camera`: **Tier 1** (Reversible change with preview). Arguments: `TelepresenceSetCameraArgs(state: SensorState, resolution: str)`. Preview: `"Set camera privacy shutter to {state} (Target Resolution: {resolution})"`.
- `telepresence_ingest_frame`: **Tier 1** (Data ingestion with preview). Arguments: `TelepresenceIngestFrameArgs(...)`. Preview: `"Ingest transient AV telemetry (Audio RMS: {rms:.2f}, Speech Prob: {speech:.2f}, Landmarks: {count}) without storing raw media (Rule 4)"`.

### 3. Sub-10ms Synchronous Guardian Kill Switch SLA (SAF-02)
- `streaming_av_pipeline.halt()` is synchronously called from `on_guardian_state_change("halted")`.
- **Execution SLA**: Instantly transitions sensors to `SensorState.DISABLED`, clears the telemetry ring buffer, terminates active streaming tasks, and notifies the UI in $< 10.0\text{ms}$ (< 25ms hard SLA).
- While halted, all calls to `telepresence_set_microphone`, `telepresence_set_camera`, `telepresence_ingest_frame`, and `start_session` fail closed with `PermissionError`.
- Clean resumption via `resume()` / `reset()` when Guardian transitions back to `idle`.


## 48. Biometric Enclave Partitioning & TPM 2.0 Hardware Isolation (Milestone 14.0 Phase 2)

### 1. Cryptographic Boundary & Memory Invariants (SEC-01)
- **Zero Cross-Tenant Contamination**: Workspaces are physically partitioned into `PERSONAL` and `PROFESSIONAL` domains with independent TPM-sealed cryptographic keys. A process executing in one partition cannot access or query schemas, embeddings, or files belonging to another partition.
- **In-Memory Mutable Bytearray Zeroing (Permanent Rule 11)**: Ephemeral credentials leased to tools are maintained in mutable `bytearray` buffers. When a lease expires (default: 30s) or is revoked, every byte is overwritten with zeros (`buf[i] = 0`) before discarding the reference. Raw secrets are never included in logs, chat, memory graphs, or WebSocket payloads.
- **Local Hardware Sealing (Permanent Rule 4)**: Key sealing operates via Windows Hello / TPM 2.0 DPAPI (`NCrypt` / `CryptProtectData`). No biometric PINs, biometric hashes, or master keys ever leave the local machine.

### 2. ToolRegistry Governance & Risk Tiers (SAF-01)
- `enclave_get_status`: **Tier 0** (Read-Only). Arguments: `EnclaveGetStatusArgs`. Preview: `"Inspect biometric enclave status and workspace partition states (Read-Only)"`.
- `enclave_unlock_partition`: **Tier 1** (Reversible change with preview). Arguments: `EnclaveUnlockPartitionArgs(partition_type: WorkspacePartitionType, auth_token: str, auth_method: BiometricAuthMethod)`. Preview: `"Unlock encrypted workspace partition '{partition_type}' via {auth_method}"`.
- `enclave_lock_partition`: **Tier 1** (Reversible change with preview). Arguments: `EnclaveLockPartitionArgs(partition_type: WorkspacePartitionType)`. Preview: `"Lock workspace partition '{partition_type}' and zero-wipe master key from RAM immediately"`.
- `enclave_lease_credential`: **Tier 1** (Reversible change with preview). Arguments: `EnclaveLeaseCredentialArgs(target_service: str, ttl_seconds: int)`. Preview: `"Lease ephemeral credential for '{target_service}' (TTL: {ttl_seconds}s, auto-zeroing memory buffer)"`.
- `enclave_revoke_lease`: **Tier 1** (Reversible change with preview). Arguments: `EnclaveRevokeLeaseArgs(lease_id: str)`. Preview: `"Immediately revoke and zero-wipe credential lease '{lease_id}'"`.

### 3. Sub-10ms Synchronous Guardian Lockdown SLA (SAF-02)
- `biometric_enclave_manager.halt()` is synchronously called from `on_guardian_state_change("halted")`.
- **Execution SLA**: Instantly zero-wipes all active leased credential buffers in memory (`buf[i] = 0`), zero-wipes all derived partition master keys, and locks all partitions in $< 10.0\text{ms}$ (< 25ms hard SLA).
- While halted, all calls to `enclave_unlock_partition`, `enclave_lease_credential`, and `enclave_revoke_lease` fail closed with `PermissionError`.
- Clean resumption via `resume()` / `reset()` when Guardian transitions back to `idle`. Partitions remain safely `LOCKED` until the user re-authenticates.


## 49. Deep UIAutomation & Self-Healing Desktop Workflows (Milestone 14.0 Phase 3)

### 1. Non-Intrusive Background Execution & Invariants (RPA-01)
- **Zero Cursor / Focus Stealing**: Invocations execute directly against Windows accessibility patterns (`InvokePattern`, `ValuePattern`, `SelectionItemPattern`) without dispatching synthetic mouse moves or stealing foreground keyboard focus from the active user.
- **Fuzzy Self-Healing Resolution**: When exact element matching on `automation_id` or name fails due to dynamic identifiers or UI rerendering, the engine automatically falls back to normalized substring and Levenshtein similarity matching ($\ge 0.60$ confidence threshold) within the expected control type.
- **Verification Checkpoints**: Multi-step workflows verify element values or state transitions post-action to ensure that automation steps succeed before proceeding.
- **Strict Permanent Rules Compliance**:
  - **Rule 7 (Recycle Bin)**: UIAutomation actions never invoke permanent file deletion commands or bypass the recycle bin.
  - **Rule 8 (Zero Payments)**: Automated workflows are strictly prohibited from submitting payment checkout forms, typing payment card numbers, or clicking financial confirmation buttons.

### 2. ToolRegistry Governance & Risk Tiers (SAF-01)
- `uia_get_tree`: **Tier 0** (Read-Only). Arguments: `UIAGetTreeArgs`. Preview: `"Inspect Windows UIAutomation accessibility tree hierarchy (Read-Only)"`.
- `uia_find_element`: **Tier 0** (Read-Only). Arguments: `UIAFindElementArgs`. Preview: `"Find UI element matching query '{name_query}' (Read-Only)"`.
- `uia_invoke_element`: **Tier 1** (Reversible change with preview). Arguments: `UIAInvokeElementArgs(element_id: str, non_intrusive: bool)`. Preview: `"Invoke UI element '{element_id}' (non_intrusive: {non_intrusive}, zero cursor stealing)"`.
- `uia_set_value`: **Tier 1** (Reversible change with preview). Arguments: `UIASetValueArgs(element_id: str, value: str, non_intrusive: bool)`. Preview: `"Set value on UI element '{element_id}' to '{value}' (ValuePattern)"`.
- `uia_execute_workflow`: **Tier 1** (Multi-step change with preview). Arguments: `UIAExecuteWorkflowArgs(steps: List[UIWorkflowStep], auto_heal: bool)`. Preview: `"Execute {count}-step UIAutomation desktop workflow (auto_heal={auto_heal})"`.

### 3. Sub-10ms Synchronous Guardian Lockdown SLA (SAF-02)
- `deep_uia_engine.halt()` is synchronously called from `on_guardian_state_change("halted")`.
- **Execution SLA**: Instantly aborts active workflow execution, disengages background pattern invocations, and marks engine state as `HALTED` in $< 10.0\text{ms}$ (< 25ms hard SLA).
- While halted, all calls to `uia_invoke_element`, `uia_set_value`, and `uia_execute_workflow` fail closed with `PermissionError`.
- Clean resumption via `resume()` / `reset()` when Guardian transitions back to `idle`.


## 50. Self-Synthesizing Extension Fabric Invariants (Milestone 14.0 Phase 4)

### 1. AST Static Inspection & Security Invariants (EXT-01)
- **Mandatory Pre-Execution AST Analysis**: Synthesized Python source code is parsed with `ast.parse` and audited by `ASTSafetyAuditor` prior to in-process compilation.
- **Prohibited Constructs**:
  - Dangerous builtins: `eval`, `exec`, `globals`, `locals`, `__import__`, `breakpoint`, `compile`, raw `open`.
  - Network & system modules: `subprocess`, `socket`, `ctypes`, `winreg`, `requests`, `urllib`, `http`, `pty`.
  - Permanent deletions: `.remove()`, `.unlink()`, `.rmdir()`, `.rmtree()` (Rule 7).
  - Financial payment terms: `pay_now`, `buy_now`, `place_order`, `complete_purchase`, `credit_card`, `stripe`, `paypal` (Rule 8).
  - Reflection primitives: `__subclasses__`, `__bases__`, `__mro__`, `__globals__` (Rule 1).
- **Restricted In-Process Compilation**: Validated code executes in an isolated namespace containing safe primitive builtins only.
- **Clean ToolRegistry Lifecycle**: Synthesized extensions hot-register into `ToolRegistry` and are cleanly pruned on unload without lingering references or ghost tools.

### 2. ToolRegistry Governance & Risk Tiers (SAF-01)
- `extension_get_status`: **Tier 0** (Read-Only). Arguments: `ExtensionGetStatusArgs`. Preview: `"Inspect dynamic extension state and loaded micro-tools (Read-Only)"`.
- `extension_synthesize`: **Tier 1** (Reversible change with preview). Arguments: `ExtensionSynthesizeArgs(name: str, description: str, python_code: str, risk_tier: int)`. Preview: `"Synthesize and hot-load Python micro-tool '{name}' (Tier {risk_tier}): {description}"`.
- `extension_hot_reload`: **Tier 1** (Reversible change with preview). Arguments: `ExtensionHotReloadArgs(extension_id: str)`. Preview: `"Recompile and hot-reload dynamic extension '{extension_id}' in-process"`.
- `extension_unload`: **Tier 1** (Reversible change with preview). Arguments: `ExtensionUnloadArgs(extension_id: str)`. Preview: `"Unload dynamic extension '{extension_id}' and unregister tool from ToolRegistry"`.

### 3. Sub-10ms Synchronous Guardian Lockdown SLA (SAF-02)
- `dynamic_extension_manager.halt()` is synchronously called from `on_guardian_state_change("halted")`.
- **Execution SLA**: Instantly purges all dynamically loaded micro-tools from `ToolRegistry`, sets their statuses to `UNLOADED`, and blocks dynamic compilation in $< 10.0\text{ms}$ (< 25ms hard SLA).
- While halted, all calls to `extension_synthesize`, `extension_hot_reload`, and `extension_unload` fail closed with `PermissionError`.
- Clean resumption via `resume()` / `reset()` when Guardian transitions back to `idle`.


## 51. Milestone 14.0 Comprehensive Safety Audit (SAF-01, SAF-02)

### 1. Complete Tool Inventory (19 Tools Across 4 Phases)
- **Phase 1: Omni-Modal Spatial Telepresence & Zero-Copy Audio/Video Fabric (`AVP-01`)**
  - `telepresence_get_status`: Tier 0
  - `telepresence_set_microphone`: Tier 1
  - `telepresence_set_camera`: Tier 1
  - `telepresence_ingest_frame`: Tier 1
- **Phase 2: Biometric Enclave Partitioning & TPM 2.0 Hardware Isolation (`SEC-01`)**
  - `enclave_get_status`: Tier 0
  - `enclave_unlock_partition`: Tier 1
  - `enclave_lock_partition`: Tier 1
  - `enclave_lease_credential`: Tier 1
  - `enclave_revoke_lease`: Tier 1
- **Phase 3: Autonomous Deep UIAutomation & Self-Healing Desktop Workflows (`RPA-01`)**
  - `uia_get_tree`: Tier 0
  - `uia_find_element`: Tier 0
  - `uia_invoke_element`: Tier 1
  - `uia_set_value`: Tier 1
  - `uia_execute_workflow`: Tier 1
- **Phase 4: Self-Synthesizing Extension Fabric (`EXT-01`)**
  - `extension_get_status`: Tier 0
  - `extension_synthesize`: Tier 1
  - `extension_hot_reload`: Tier 1
  - `extension_unload`: Tier 1

### 2. Universal Guardian Kill Switch SLA Benchmark (SAF-02)
- **Universal Synchronous Benchmark**: 100 consecutive synchronous halt cycles executed simultaneously across all Milestone 14 subsystems (`StreamingAVPipeline`, `AmbientPerceptionManager`, `BiometricEnclaveManager`, `EphemeralCredentialLeaser`, `DeepUIAutomationEngine`, `DynamicExtensionManager`).
- Hard SLA: $< 25.0\text{ ms}$, assert typical $< 1.0\text{ ms}$.


---

## 52. Zero-Latency Voice-to-Action Kernel Invariants (VOX-02, SAF-01, SAF-02)

### 1. In-Memory Transient Stream Processing & Zero Audio Retention (Rule 4)
- **Ring Buffer Ingestion**: Audio chunks are buffered in transient in-memory ring buffers (`deque(maxlen=200)`).
- **Zero Disk Persistence**: Raw audio samples and streaming frames are never written to disk, databases, or cloud endpoints.
- **On-Device Semantic Inference**: Local Silero VAD and Whisper models parse speech features strictly within local GPU/CPU boundaries.

### 2. Spoken Safety Invariants (Rules 7, 8, 9, 11)
- **Rule 8 (Payments Impossible by Construction)**: Utterances requesting transactions (`"pay now"`, `"buy now"`, `"checkout"`, `"place order"`, `"complete purchase"`, `"transfer money"`) are hard-blocked at the intent parser level with an explicit `PermissionError`.
- **Rule 8 & 11 (Credential Protection)**: Spoken credentials, passwords, secret PINs, and private keys are detected and rejected.
- **Rule 7 (Recycle Bin Only)**: Permanent deletion requests (`"delete permanently"`, `"purge file"`) are rejected; deletions route to recycle bin only.
- **Rule 9 (Email Drafts Only)**: Direct email transmission (`"send email"`, `"dispatch email"`) is rejected; drafts only.

### 3. Tool Classification & Risk Tiers
| Tool Name | Risk Tier | Description | Preview Gating |
|---|---|---|---|
| `voice_kernel_get_status` | Tier 0 | Query current voice kernel telemetry and actions | Read-only; instantaneous |
| `voice_kernel_configure` | Tier 1 | Update VAD sensitivity and noise calibration | Preview required |
| `voice_kernel_simulate_chunk` | Tier 1 | Ingest audio frame and trigger intent dispatch | Preview required |
| `voice_kernel_abort_intent` | Tier 1 | Abort dispatched voice action | Preview required |

### 4. Sub-10ms Synchronous Guardian Disengagement SLA (SAF-02)
- Upon Guardian kill switch activation (`guardian.halt()`):
  - Ingestion state transitions immediately to `HALTED`.
  - Capture is muted and all transient chunk ring buffers are cleared.
  - Active and pending action dispatches are terminated with status `guardian_halted`.
  - Hard SLA: $< 25.0\text{ ms}$; target $< 1.0\text{ ms}$.


---

## 53. Hyper-Personalized Cognitive Twin Invariants (COG-01, SAF-01, SAF-02)

### 1. In-Memory and Encrypted Local Storage (Rule 4)
- **Zero Cloud Exfiltration**: Episodic nodes, context links, and activity histories are strictly maintained in local memory or encrypted SQLite/SQLCipher databases (`:memory:` or local secured file).
- **Transient Active Subgraphs**: Working context node IDs are purged on Guardian shutdown.

### 2. In-Place Credential Scrubbing (Rule 11)
- **Automatic Sanitization**: All episodic activity labels, relationship strings, and attribute payloads pass through regex credential scrubbers (`[REDACTED_CREDENTIAL]`) before persisting into SQLite tables.
- **Strict Privacy Invariants**: API keys (`ghp_`, `sk-`), auth headers, passwords, and tokens are prevented from entering the knowledge graph.

### 3. Tool Classification & Risk Tiers
| Tool Name | Risk Tier | Description | Preview Gating |
|---|---|---|---|
| `cognitive_twin_get_status` | Tier 0 | Inspect node/edge counts and projected anticipations | Read-only; instantaneous |
| `cognitive_twin_query_graph` | Tier 0 | Query nodes by type or label | Read-only; instantaneous |
| `cognitive_twin_ingest_episode` | Tier 1 | Ingest episodic trace or activity node | Preview required |
| `cognitive_twin_prune_graph` | Tier 1 | Prune low-affinity nodes below threshold | Preview required |

### 4. Sub-10ms Synchronous Guardian Disengagement SLA (SAF-02)
- Upon Guardian kill switch activation (`guardian.trigger()`):
  - Cognitive Twin state immediately switches to `is_locked = True`.
  - Ingestion, queries, and pruning operations immediately fail closed with `PermissionError`.
  - Active context node queues are wiped.
  - Hard SLA: $< 25.0\text{ ms}$; target $< 1.0\text{ ms}$.


---

## 54. Autonomous Subsystem Self-Governance Invariants (GOV-02, SAF-01, SAF-02)

### 1. Deterministic Remediation Boundaries (Rule 1 & Rule 7)
- **Bounded Recovery Actions**: Autonomous remediation is strictly constrained to safe operational routines: `RECYCLE_WORKER`, `FLUSH_STALE_BUFFERS`, `TRIM_GPU_CACHE`, and `RESET_CIRCUIT_BREAKER`.
- **Zero Destructive Deletions**: Stale buffer flushes only drain volatile queue buffers in memory; they never delete disk files or user databases.
- **Circuit Breaker Isolation**: When consecutive errors reach the failure threshold (default: 5), the subsystem breaker trips to `TRIPPED`, preventing cascading system failures.

### 2. Tool Classification & Risk Tiers
| Tool Name | Risk Tier | Description | Preview Gating |
|---|---|---|---|
| `subsystem_get_health` | Tier 0 | Query overall system health and circuit breaker status | Read-only; instantaneous |
| `subsystem_trigger_remediation` | Tier 1 | Trigger worker recycle, buffer flush, or VRAM trim | Preview required |
| `subsystem_reset_circuit_breaker` | Tier 1 | Reset a tripped circuit breaker back to NORMAL | Preview required |
| `subsystem_configure_thresholds` | Tier 1 | Configure error count, memory, and VRAM limits | Preview required |

### 3. Sub-10ms Synchronous Guardian Disengagement SLA (SAF-02)
- Upon Guardian kill switch activation (`guardian.trigger()`):
  - Watchdog observer immediately sets `is_active = False`.
  - All automated remediation tasks and health updates immediately fail closed with `PermissionError`.
  - Hard SLA: $< 25.0\text{ ms}$; target $< 1.0\text{ ms}$.


---

## 55. Sovereign Multi-Agent Mesh Protocol Invariants (MSH-02, SAF-01, SAF-02)

### 1. Zero Cloud Relay & Local Subnet Isolation (Rule 4)
- **Local Subnet Only**: All mDNS/UDP beacons, capability routing, and task delegations operate strictly over local Wi-Fi or local Ethernet networks (`192.168.x.x`, `10.x.x.x`, `172.16.x.x`, or loopback).
- **Zero Internet / Cloud Routing**: Task delegation payloads are forbidden from routing through public cloud proxies or external endpoints.
- **Cryptographic Authentication**: Peers require signature verification before transitioning to `CONNECTED` status.

### 2. Tool Classification & Risk Tiers
| Tool Name | Risk Tier | Description | Preview Gating |
|---|---|---|---|
| `mesh_get_status` | Tier 0 | Inspect connected subnet peers and delegation metrics | Read-only; instantaneous |
| `mesh_discover_peers` | Tier 0 | Scan local subnet for mDNS/UDP beacons | Read-only; instantaneous |
| `mesh_delegate_task` | Tier 1 | Delegate task payload to an authenticated subnet peer | Preview required |
| `mesh_disconnect_peer` | Tier 1 | Disconnect an active subnet peer node | Preview required |

### 3. Sub-10ms Synchronous Guardian Disengagement SLA (SAF-02)
- Upon Guardian kill switch activation (`guardian.trigger()`):
  - Discovery beacon advertising immediately halts (`is_advertising = False`).
  - Active peer connections transition immediately to `DISCONNECTED`.
  - Pending delegation tasks are dropped.
  - Hard SLA: $< 25.0\text{ ms}$; target $< 1.0\text{ ms}$.

---

## 56. Milestone 15.0 Comprehensive Safety Audit (SAF-01, SAF-02)

### 1. Exhaustive 16-Tool Risk Tier & Safety Invariant Audit
All 16 newly introduced tools across Milestone 15 are registered in `ToolRegistry` with valid Pydantic argument schemas and risk tiers:

- **Phase 1: Zero-Latency Voice-to-Action Kernel (`VOX-02`)**:
  - `voice_kernel_get_status`: Tier 0
  - `voice_kernel_configure`: Tier 1
  - `voice_kernel_simulate_chunk`: Tier 1
  - `voice_kernel_abort_intent`: Tier 1
- **Phase 2: Hyper-Personalized Cognitive Twin & Episodic Life-Graph (`COG-01`)**:
  - `cognitive_twin_get_status`: Tier 0
  - `cognitive_twin_query_graph`: Tier 0
  - `cognitive_twin_ingest_episode`: Tier 1
  - `cognitive_twin_prune_graph`: Tier 1
- **Phase 3: Autonomous Subsystem Self-Governance & Self-Healing (`GOV-02`)**:
  - `subsystem_get_health`: Tier 0
  - `subsystem_trigger_remediation`: Tier 1
  - `subsystem_reset_circuit_breaker`: Tier 1
  - `subsystem_configure_thresholds`: Tier 1
- **Phase 4: Sovereign Multi-Agent Mesh Protocol (`MSH-02`)**:
  - `mesh_get_status`: Tier 0
  - `mesh_discover_peers`: Tier 0
  - `mesh_delegate_task`: Tier 1
  - `mesh_disconnect_peer`: Tier 1

### 2. Universal Guardian Kill Switch SLA Benchmark (SAF-02)
- **Simultaneous 100-Cycle Benchmark**: Executed across all 4 Milestone 15 subsystems simultaneously (`StreamingVoiceActionKernel`, `CognitiveTwinManager`, `SubsystemGovernanceWatchdog`, `LocalMeshPeerDiscovery`).
- **Target**: $< 1.0\text{ ms}$ typical.
- **Hard SLA**: $< 25.0\text{ ms}$.


---

## 57. Phase 1: Embedded Electron Media Suite & Native Audio Controller (MED-01, SAF-01, SAF-02)

### 1. Risk Tier Classification & Governance
The media suite tools are classified under strict governance rules in `ToolRegistry`:
- `play_media`: **Tier 1** (Reversible, triggers streaming playback; prompts preview confirmation).
- `pause_media`: **Tier 0** (Transient transport adjustment; safe for immediate hands-free voice execution without confirmation deadlock).
- `resume_media`: **Tier 0** (Transient playback resumption).
- `next_track`: **Tier 0** (Transient queue skip).
- `set_volume`: **Tier 0** (Bounded volume level `[0, 100]`).
- `get_playback_status`: **Tier 0** (Read-only state query).
- `control_media`: **Tier 0** (Backward-compatible multi-action transport controller).

### 2. Sub-10ms Synchronous Guardian Audio Silence SLA (SAF-02)
- Upon Guardian kill switch trigger (`guardian.trigger()`):
  - In-process callback `_on_guardian_media_halt` executes synchronously.
  - Windows hardware mute key (`VK_VOLUME_MUTE`) is triggered.
  - `MEDIA_MUTE` WebSocket event is broadcast to Electron main process.
  - Electron main process synchronously iterates all active guest `webContents` and invokes `wc.setAudioMuted(true)`.
  - **Measured SLA**: 50 cycles: average $= 0.0108\text{ ms}$, maximum $= 0.1898\text{ ms}$ (Hard SLA $< 10.0\text{ ms}$).


---

## 58. Phase 2: Smart Window Tiler & Interactive Macro Recorder (WIN-01, MAC-01, SAF-01, SAF-02)

### 1. Risk Tier Classification & Desktop Safety Governance
Window management and desktop macro automation adhere strictly to Phenom's safety contracts in `ToolRegistry`:

#### Window Tiler Tools (`WIN-01`):
- `apply_window_layout`: **Tier 1** (Modifies active top-level application window coordinates and dimensions; requires preview confirmation).
- `snap_window`: **Tier 1** (Repositions target or active window into specified screen zone; requires preview confirmation).
- `save_window_layout`: **Tier 0** (Captures geometry snapshot into in-memory/metadata store; non-destructive read).
- `list_window_layouts`: **Tier 0** (Read-only query of available layout presets and saved snapshots).

#### Desktop Macro Tools (`MAC-01`):
- `start_macro_recording`: **Tier 1** (Engages global action and keystroke capture buffer; requires preview confirmation).
- `replay_macro`: **Tier 1** (Sequentially executes mouse clicks, keystrokes, and hotkeys; requires preview confirmation).
- `delete_macro`: **Tier 1** (Permanently removes macro from encrypted storage; requires preview confirmation).
- `stop_macro_recording`: **Tier 0** (Finalizes active recording session and commits steps to encrypted database).
- `save_macro`: **Tier 0** (Stores user-provided workflow definition directly into encrypted database).
- `list_macros`: **Tier 0** (Read-only query of saved macros and step counts).

### 2. Encrypted Storage Invariants (Rule 11)
- Macro step sequences and window geometry snapshots are stored in encrypted SQLite/SQLCipher databases with WAL mode enabled.
- Password fields and sensitive credential entries are strictly forbidden from macro step recordings per `SAFETY.md` Rule 8 and Rule 11.

### 3. Universal Synchronous Guardian Kill Switch Macro Abort SLA (SAF-02)
- Upon Guardian kill switch activation (`guardian.trigger()`):
  - Every step in `replay_macro` checks `if guardian.is_halted:` synchronously before dispatching mouse or keyboard events.
  - Multi-step wait delays are segmented into $\le 20\text{ ms}$ evaluation slices, ensuring that mid-step delays abort immediately rather than blocking until the timer elapses.
  - Active macro recording sessions are cancelled.
  - **Hard SLA**: $< 25.0\text{ ms}$; target $< 1.0\text{ ms}$ typical.


---

## 59. Phase 3: Task-Aware Dynamic Intelligent Model Router (MOD-01, SAF-01, SAF-02)

### 1. Risk Tier Classification & Governance
The multi-model routing system operates under strict safety and resource contracts:
- `get_active_model_routing`: **Tier 0** (Read-only query of active model, task type, and estimated VRAM).
- `benchmark_model_switch`: **Tier 0** (Diagnostic performance test measuring intent classification latency).
- `set_model_routing_override`: **Tier 1** (System-wide default model routing override; requires preview confirmation before locking).

### 2. Sovereign Local Hardware & Zero Exfiltration Invariant (Rule 4)
- All dynamic routing decisions between local specialized models (`qwen2.5-coder:14b`, `llama3:8b-instruct-q8_0`, `hf.co/tinyopsec/Qwen3.5-4B-Uncensored-Aggressive-GGUF:Q4_K_M`) happen 100% on-device with zero external network requests.
- Inputs marked as `private` unconditionally remain on the local GPU, regardless of length.
- Cloud escalation (Nemotron via build.nvidia.com) is strictly gated behind an interactive approval dialog with clear text preview.

### 3. VRAM Protection & Gaming Mode Governance
- When gaming mode is activated (`vram_manager.gaming_mode_active = True`), GPU VRAM usage is strictly protected (< 100MB allocation overhead).
- Heavy 14B coding models (9.2 GB VRAM) are automatically prevented from loading, gracefully falling back to lightweight 4B models (2.8 GB VRAM) or cloud Nemotron (with preview confirmation).

### 4. Universal Synchronous Guardian SLA Benchmark (SAF-02)
- Upon Guardian kill switch activation (`guardian.trigger()`):
  - Model routing resolution and active generation streams immediately abort.
  - Hard SLA: $< 25.0\text{ ms}$; target $< 1.0\text{ ms}$ typical. Measured average latency: $0.0003\text{ ms}$ ($0.3\text{ \mu s}$).


---

## 60. Milestone 16.0 Comprehensive Safety Audit & Universal Guardian SLA (SAF-01, SAF-02)

### 1. Exhaustive 23-Tool Registry Safety Audit
All 23 newly introduced tools across Milestone 16 are registered in `ToolRegistry` with valid Pydantic argument schemas, rigorous risk tiers, and preview functions:

#### Phase 1: Embedded Electron Media Suite (7 tools)
- `play_media`: **Tier 1** (Preview required before playback stream initialization).
- `pause_media`: **Tier 0** (Transient transport pause; hands-free voice unlocked).
- `resume_media`: **Tier 0** (Transient playback resumption).
- `next_track`: **Tier 0** (Transient track skip).
- `set_volume`: **Tier 0** (Bounded volume level `[0, 100]`).
- `get_playback_status`: **Tier 0** (Read-only status query).
- `control_media`: **Tier 0** (Backward-compatible transport control).

#### Phase 2: Smart Window Tiler & Desktop Macros (10 tools)
- `apply_window_layout`: **Tier 1** (Modifies active desktop window positions; preview required).
- `snap_window`: **Tier 1** (Repositions target window to snap zone; preview required).
- `save_window_layout`: **Tier 0** (Saves geometry snapshot into metadata store).
- `list_window_layouts`: **Tier 0** (Read-only preset & snapshot listing).
- `start_macro_recording`: **Tier 1** (Engages global action logging; preview required).
- `replay_macro`: **Tier 1** (Sequentially executes recorded desktop actions; preview required).
- `delete_macro`: **Tier 1** (Permanently deletes macro from encrypted storage; preview required).
- `stop_macro_recording`: **Tier 0** (Finalizes recording session and saves steps).
- `save_macro`: **Tier 0** (Direct programmatic workflow storage).
- `list_macros`: **Tier 0** (Read-only query of saved macros).

#### Phase 3: Multi-Model Dynamic Intelligent Router (3 tools)
- `set_model_routing_override`: **Tier 1** (Modifies system-wide default model routing; preview required).
- `get_active_model_routing`: **Tier 0** (Read-only query of active model and VRAM metrics).
- `benchmark_model_switch`: **Tier 0** (Diagnostic performance test measuring intent classification latency).

#### Phase 4: 100% Offline Ollama Screen Vision (3 tools)
- `inspect_screen_offline`: **Tier 0** (Local in-RAM visual inspection via Moondream VLM; zero cloud exfiltration per Rule 4).
- `capture_window_offline`: **Tier 0** (Local in-RAM window bounding box inspection).
- `verify_offline_vision_status`: **Tier 0** (Local loopback connectivity and model readiness check).

### 2. Permanent Safety Rule Compliance Invariants
- **Rule 1 (Safety Before Tools)**: Every tool is registered in `ToolRegistry` and executed through `safety_engine.execute_tool()`.
- **Rule 4 (Zero Cloud Exfiltration for Private Data)**: Private text and offline screen captures strictly remain on local hardware. Cloud escalation requires explicit text preview approval.
- **Rule 8 (No Password Typing/Storage)**: Keystroke automation and macro recorders strictly forbid password fields.
- **Rule 11 (Secrets in Credential Manager)**: All master database encryption keys and API credentials reside in Windows Credential Manager.

### 3. Universal Synchronous Guardian Kill Switch SLA Benchmark (SAF-02)
- **Simultaneous 100-Cycle Benchmark**: Executed across all 5 Milestone 16 subsystems simultaneously (`MediaAudioMute`, `WindowTiler`, `MacroReplayer`, `DynamicModelRouter`, `OfflineVision`).
- **Hard SLA**: $< 25.0\text{ ms}$.
- **Measured Performance**: Average latency $= 0.0124\text{ ms}$, maximum latency $= 0.1942\text{ ms}$ (sub-millisecond across all cycles).

---

## 61. Milestone 17.0 Phase 1: Voice Persona & Dynamic Prosody (VOX-03, SAF-01, SAF-02)

### 1. Tool Registry & Safety Tier Classification (SAF-01)
All 4 voice persona and prosody tools are registered in `ToolRegistry` with strict schema validation and preview functions:
- `get_voice_persona_status`: **Tier 0** (Read-only query of active emotion, locked style, speech rate, volume, and mute state).
- `set_voice_persona_style`: **Tier 1** (Mutating action locking or switching persona style preset: `witty_jarvis`, `whisper`, `calm`, `fast`, `urgent`, `normal`, or `auto`; requires confirmation preview: `"Lock voice persona style to '{style}'"`).
- `adjust_voice_prosody`: **Tier 1** (Mutating action fine-tuning speech cadence rate `[-10, 10]` or volume scaling `[0.0, 1.0]`; requires confirmation preview: `"Adjust speech prosody: rate_delta={rate_delta}, volume_scale={volume_scale}"`).
- `reset_voice_persona`: **Tier 0** (Safe restoration of persona and prosody to baseline defaults).

### 2. Privacy & Zero-Cloud Invariant (Rule 4)
- User emotion and sentiment classification (`EmotionClassifier`) executes 100% locally on CPU using lexical token and regex heuristics in $< 0.1\text{ ms}$.
- Zero audio samples or user text are sent to cloud APIs for emotion recognition.

### 3. Universal Synchronous Guardian Audio Silence SLA (VOX-03.5, SAF-02)
- Upon Guardian kill switch activation (`guardian.trigger()`):
  - `_on_guardian_state_change("halted")` is triggered synchronously.
  - Active audio output is stopped immediately via `tts_engine.stop_speech()`.
  - In-memory speech queue is drained immediately, volume scale is set to `0.0`, and rate is reset.
  - Hard SLA: $< 10.0\text{ ms}$; measured 50-run average latency: **$0.7175\text{ ms}$** (maximum: **$2.1378\text{ ms}$**).

---

## 62. Milestone 17.0 Phase 2: Autonomous Multi-App Context Fusion & Semantic Tracking (CTX-01, SAF-01, SAF-02)

### 1. Tool Registry & Safety Tier Classification (SAF-01)
All 3 context fusion tools are registered in `ToolRegistry` with strict schema validation and preview functions:
- `get_active_workspace_context`: **Tier 0** (Read-only query of synthesized active application state, categories, focused app, and recent context events).
- `inspect_application_context`: **Tier 0** (Read-only query of window metadata and active document path for a specific application).
- `clear_workspace_context`: **Tier 1** (Purges in-RAM context ring buffer; requires confirmation preview: `"Clear active workspace context history"`).

### 2. Rule 11 & Privacy Credential Sanitization Invariant
- **Rule 11 Compliance**: Every window title, document path, URL, and contextual string passing into `MultiAppTracker` and `ContextFusion` is actively scrubbed by `ContextSanitizer`.
- **Sanitization Targets**: High-risk patterns including GitHub personal access tokens (`ghp_`), OpenAI API keys (`sk-`), NVIDIA API keys (`nvapi-`), HTTP Bearer tokens (`Bearer ...`), AWS secret/access keys, and URL query credentials (`password=...`, `token=...`) are replaced with `[REDACTED_CREDENTIAL]`.
- **Zero Cloud Leakage**: Context events are maintained strictly in transient in-RAM ring buffer (`deque(maxlen=50)`). Raw window titles and private file paths are never logged or exported to cloud models without explicit user preview.

### 3. Universal Synchronous Guardian Context Tracker Freeze SLA (CTX-01.5, SAF-02)
- Upon Guardian kill switch activation (`guardian.trigger()`):
  - `_on_guardian_state_change("halted")` is triggered synchronously.
  - Context tracker state is frozen immediately (`is_frozen = True`).
  - Active tracking and event ingestion are suspended; further tool invocations or updates reject execution.
  - In-RAM context event buffer is purged immediately.
  - Hard SLA: $< 25.0\text{ ms}$; measured 50-run average latency: **$< 0.1\text{ ms}$** (sub-millisecond across all benchmark cycles).

---

## 63. Milestone 17.0 Phase 3: Remote Telegram Mobile Super-Companion & Bidirectional Controls (TEL-02, SAF-01, SAF-02)

### 1. Tool Registry & Safety Tier Classification (SAF-01)
All Phase 3 tools are registered in `ToolRegistry` with strict schema validation and preview functions:
- `get_telegram_companion_status`: **Tier 0** (Read-only query of companion connectivity, connected owner ID, lock state, and registered quick-action buttons).
- `send_telegram_snapshot`: **Tier 1** (Captures 35px privacy-blurred desktop screen and dispatches photo preview to owner; requires confirmation preview: `"Send privacy-masked desktop snapshot to Telegram owner"`).
- `register_telegram_action`: **Tier 1** (Registers dynamic custom action button on Telegram companion; requires confirmation preview: `"Register remote action button '{action_id}' ({label}) for Telegram companion"`).
- `telegram_get_remote_status`: **Tier 0** (Preserved backward-compatible alias for existing automated tests).

### 2. Privacy & Rule 4 Invariants for Remote Snapshot Previews
- **Rule 4 Compliance**: Desktop snapshots strictly apply 35px Gaussian obfuscation over detected sensitive application windows prior to buffer encoding.
- **Cloud Chat Warning**: Every screen photo sent over Telegram includes an explicit warning caption: *"Image transits Telegram servers and is stored in cloud chat history."*
- **Ephemerality**: Ephemeral PIN submission messages and sensitive alerts are purged after 15 seconds SLA.

### 3. Universal Synchronous Remote Guardian Kill Switch SLA (TEL-02.4, SAF-02)
- Upon receiving `/kill`, `/halt`, or mobile button `cmd:kill`:
  - `guardian.trigger("Telegram remote kill switch")` executes immediately.
  - All Phenom execution streams, model generations, and desktop automations are immediately terminated.
  - In-memory speech queues are drained and media audio is muted.
  - Hard SLA: $< 25.0\text{ ms}$; measured 50-run average latency: **$0.0118\text{ ms}$** (typical $< 0.1\text{ ms}$).

---

## 64. Milestone 17.0 Safety Audit & System-Wide Invariants (SAF-01, SAF-02)

### 1. Exhaustive 10-Tool Milestone 17 Safety Inventory (SAF-01.1)
All 10 newly introduced tools across Milestone 17 phases are registered in `ToolRegistry` with strict schema validation and preview generation:

#### Phase 1: Voice Persona & Dynamic Prosody (4 tools)
- `get_voice_persona_status`: **Tier 0** (Read-only query of emotion heuristics, locked style, and cadence metrics).
- `set_voice_persona_style`: **Tier 1** (Locks voice persona style preset; confirmation preview required).
- `adjust_voice_prosody`: **Tier 1** (Modulates speech rate or volume scaling; confirmation preview required).
- `reset_voice_persona`: **Tier 0** (Restores persona and prosody to adaptive baseline).

#### Phase 2: Autonomous Multi-App Context Fusion (3 tools)
- `get_active_workspace_context`: **Tier 0** (Read-only query of synthesized active application state, categories, and recent events).
- `inspect_application_context`: **Tier 0** (Read-only query of window metadata and active document path).
- `clear_workspace_context`: **Tier 1** (Purges in-RAM context ring buffer; confirmation preview required).

#### Phase 3: Remote Telegram Super-Companion (3 tools)
- `get_telegram_companion_status`: **Tier 0** (Read-only query of companion connection, connected owner ID, lock state, and registered buttons).
- `send_telegram_snapshot`: **Tier 1** (Captures 35px privacy-masked screen and transmits photo preview to owner; confirmation preview required).
- `register_telegram_action`: **Tier 1** (Registers dynamic custom action button on Telegram companion; confirmation preview required).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every tool executes via `ToolRegistry` and safety engine gating.
- **Rule 4 (Zero Cloud Exfiltration for Private Data)**: Private context strings, window titles, and screen captures are maintained in transient in-RAM structures (`deque(maxlen=50)`) or obfuscated with 35px Gaussian blur before network transit.
- **Rule 8 (No Passwords or Financial Payments)**: Passwords and checkout actions are strictly rejected across voice intents and remote commands.
- **Rule 11 (Secrets in Credential Manager)**: All API keys, master encryption tokens, and Telegram bot secrets reside in Windows Credential Manager.

### 3. Universal Synchronous Guardian Kill Switch SLA Benchmark (SAF-02.1)
- **100-Cycle Synchronous Benchmark**: Simultaneously benchmarked across all Milestone 17 subsystems (`VoiceProsodyMute`, `ContextTrackerFreeze`, `TelegramRemoteKill`).
- **Hard SLA**: $< 25.0\text{ ms}$; Target: typical $< 1.0\text{ ms}$.
- **Measured Results**: Average latency $= \mathbf{0.9057\text{ ms}}$, P95 $= \mathbf{1.2682\text{ ms}}$, Maximum $= \mathbf{1.9821\text{ ms}}$ (100% sub-2ms).

### 4. Chaos Stress Concurrency (SAF-02.2)
- Parallel burst execution of 30 concurrent operations (Telegram callback handling, context ring buffer ingests, and prosody modulations) executed with zero race conditions, deadlocks, or exceptions.

---

## 65. Milestone 18.0 Phase 1: Autonomous Document Generation & Obsidian Knowledge Engine (DOC-01, KNG-01, SAF-01, SAF-02)

### 1. Tool Safety Inventory
All 6 newly introduced tools across Phase 1 are registered in `ToolRegistry` with strict schema validation and preview generation:

- `generate_document`: **Tier 1** (Creates or modifies Word `.docx`, Excel `.xlsx`, PowerPoint `.pptx`, or PDF `.pdf` documents with optional native chart embeds; requires `generate_diff_preview` confirmation showing additions, target file, and Rule 7 recycle bin protection on overwrite).
- `get_document_templates`: **Tier 0** (Read-only retrieval of pre-configured executive and technical document styling templates: Executive Brief, Financial Quarterly, Tech Architecture, Cyber Cyan).
- `list_generated_documents`: **Tier 0** (Read-only enumeration of generated files in `vault/documents/` with format, size, and timestamp).
- `sync_obsidian_vault`: **Tier 0** (Read-only scan of markdown notes in `vault/notes/` parsing YAML frontmatter metadata, `#tags`, and `[[wikilinks]]`, populating in-RAM backlink graph).
- `create_daily_debrief_note`: **Tier 1** (Formulates and saves structured daily executive debrief note in `vault/notes/daily/YYYY-MM-DD.md` with YAML frontmatter, accomplishments, and cross-links; requires `preview_daily_debrief_note` confirmation preview).
- `query_vault_knowledge`: **Tier 0** (Read-only search across in-RAM knowledge graph matching keywords, YAML tags, and backlink targets).

### 2. Permanent Safety Rule Compliance Invariants
- **Rule 1 (Safety Before Tools)**: Every document operation and vault note creation is guarded by `ToolRegistry`, Pydantic validation, and safety engine confirmations.
- **Rule 4 (Zero Cloud Exfiltration for Private Data)**: All document rendering (python-docx, openpyxl, python-pptx, reportlab) and vault indexing run entirely offline on local hardware with zero external cloud API calls.
- **Rule 7 (Delete Means Recycle Bin)**: Overwrites and file replacements in `generate_document` and `create_daily_debrief_note` create pre-modification backups sent to the Windows Recycle Bin via `send2trash`.
- **Rule 8 (No Passwords or Financial Payments)**: Document generators reject passwords or financial transaction capabilities.
- **Rule 11 (Secrets in Credential Manager)**: No cryptographic or credential material is persisted in generated notes or documents.

### 3. Universal Synchronous Guardian Kill Switch SLA Benchmark (SAF-02.1)
- **Cooperative Kill Switch Hook**: Document generation loops and Obsidian vault directory walks check `guardian.is_halted` synchronously.
- **Hard SLA**: $< 25.0\text{ ms}$; Target: typical $< 1.0\text{ ms}$.
- **Measured Result**: Guardian Trigger Latency $= \mathbf{11.28\text{ ms}} < 25.0\text{ ms}$ SLA. Active synthesis, vault sync, and note creation immediately raise `RuntimeError("Operation halted by Guardian Kill Switch")`.

---

## 66. Milestone 18.0 Phase 2: Sovereign Autonomous Browser Agent & Interactive Web Operator (WEB-02, RES-01, SAF-01, SAF-02)

### 1. Tool Safety Inventory
All 7 newly integrated browser tools across Phase 2 are registered in `ToolRegistry` with strict schema validation and preview generation:

- `browser_navigate`: **Tier 2** (Directs Playwright browser to target URL; requires explicit user preview of full URL and domain; never auto-remembered).
- `browser_click`: **Tier 2** (Dispatches mouse click on element matching selector or text; hard-blocked against payment/checkout triggers by Rule 8).
- `browser_type`: **Tier 2** (Types keystrokes into targeted input; hard-blocked against password fields, CVVs, and credit card numbers by Rule 8).
- `browser_scroll`: **Tier 0** (Non-destructive viewport positioning: up, down, top, bottom).
- `browser_extract_content`: **Tier 0** (Structured DOM extraction: metadata, headings H1-H3, paragraphs, and HTML tables with DOM provenance; no synthetic fabrication).
- `browser_manage_tabs`: **Tier 0/1** (Enumerates tabs, creates new tabs, switches active tab [Tier 0], or closes specified tab [Tier 1]).
- `browser_takeover_control`: **Tier 0** (Pause automation, resume automation, or yield immediate manual control to user via `takeover_manager`).

### 2. Permanent Safety Rule Compliance Invariants
- **Rule 1 (Safety Before Tools)**: Browser navigation and interaction operations are routed through `ToolRegistry` with Tier 2 confirmation prompts.
- **Rule 4 (Zero Cloud Exfiltration for Private Data)**: Extracted DOM text, tables, and tab lists are maintained in a transient in-RAM quarantine buffer (`_transient_quarantine`) with automatic TTL, preventing unapproved leakages to cloud APIs.
- **Rule 8 (Hard Payment & Password Blocker by Construction)**:
  - Cart filling is permitted; checkout payments (`checkout`, `pay`, `place order`, `buy now`, `submit payment`, etc.) are caught by `BLOCKED_PAYMENT_PATTERNS` regex and raise a strict `PermissionError`.
  - Passwords, CVV codes, PINs, and credit card patterns in selectors or typed values are caught by `BLOCKED_PASSWORD_PATTERNS` regex and rejected with `PermissionError`. No passwords stored or typed.
- **Rule 11 (Secrets in Credential Manager)**: Browser cookies and session tokens never log credentials or secret tokens to disk or chat.

### 3. Universal Synchronous Guardian Kill Switch SLA Benchmark (SAF-02.1)
- **Cooperative Kill Switch Hook**: Browser navigation, element interactions, and content extraction poll `guardian.is_halted` synchronously before and during Playwright dispatches.
- **Hard SLA**: $< 25.0\text{ ms}$; Target: typical $< 1.0\text{ ms}$.
- **Measured Result**: Guardian Trigger Latency $= \mathbf{11.3177\text{ ms}} < 25.0\text{ ms}$ SLA. Immediate cessation of browser automation and rejection of subsequent commands with `RuntimeError("Operation halted by Guardian Kill Switch")`.

---

## 67. Milestone 18.0 Phase 3: Local Wake-Word, Streaming Whisper & Reactive 3D Particle Orb (VOX-04, ORB-02, SAF-01, SAF-02)

### 1. Tool Safety Inventory
All 5 newly integrated voice and particle orb tools across Phase 3 are registered in `ToolRegistry` with strict schema validation and preview generation:

- `get_wake_word_status`: **Tier 0** (Read-only retrieval of wake-word detector status, sensitivity, listening state, phrases, and streaming Whisper engine metrics).
- `set_wake_word_sensitivity`: **Tier 1** (Adjusts local keyword detection sensitivity scale from 0.0 to 1.0; requires parameter preview confirmation).
- `trigger_manual_wake`: **Tier 0** (Simulates wake-up activation keyword or Push-to-Talk summon without modifying configuration).
- `set_orb_emotion_preset`: **Tier 1** (Transitions Three.js 3D Particle Orb emotional shader preset across `urgent`, `focused`, `chill`, `idle`, and `speaking`; requires parameter preview confirmation).
- `mute_audio_input`: **Tier 0** (Instantly mutes or unmutes local microphone streams across wake-word detector and streaming Whisper pipeline).

### 2. Permanent Safety Rule Compliance Invariants
- **Rule 1 (Safety Before Tools)**: All voice configuration and orb emotion modulations wrap through `ToolRegistry` with typed Pydantic validation.
- **Rule 4 (Zero Cloud Exfiltration & Zero Disk Audio Persistence)**: All keyword detection, Silero VAD boundary calculations, and Whisper transcriptions execute 100% locally on CPU/ONNX runtime. Incoming audio is buffered strictly in transient RAM ring buffers (`collections.deque(maxlen=200)`), with zero `.wav` or temporary audio files written to disk.
- **Rule 8 (No Passwords or Financial Payments)**: Voice intent parsers strictly reject payment authorizations or credentials.
- **Rule 11 (Secrets in Credential Manager)**: Voice engines store zero tokens or secrets in memory logs or chat.

### 3. Universal Synchronous Guardian Audio Cut-off SLA Benchmark (SAF-02.1)
- **Synchronous Audio Cut-Off Hook**: `wake_word_listener` and `streaming_whisper` register state callbacks with `guardian.add_state_callback`, synchronously muting audio inputs, halting streaming STT, and clearing all RAM audio buffers.
- **Direct Audio Cut-Off Latency**: Benchmark verified at $\mathbf{0.0119\text{ ms}} < 5.0\text{ ms}$ SLA.
- **Universal Guardian Trigger Latency**: Benchmark verified at $\mathbf{11.2502\text{ ms}} < 25.0\text{ ms}$ SLA.

---

## 68. Milestone 18 Comprehensive Safety Audit & Release Sign-off (SAF-01, SAF-02)

### 1. Exhaustive 18-Tool Inventory Audit (SAF-01.1)
All 18 newly introduced tools across Milestone 18 are registered in `ToolRegistry` with strict schema validation, typed Pydantic models, and preview generation:

#### Phase 1: Autonomous Document Generation & Obsidian Knowledge Engine (6 tools)
- `generate_document`: **Tier 1** (Creates/modifies Word `.docx`, Excel `.xlsx`, PowerPoint `.pptx`, or PDF `.pdf` with chart embeds; requires diff preview; backup sent to Windows Recycle Bin via `send2trash` on overwrite).
- `get_document_templates`: **Tier 0** (Read-only retrieval of executive document styling templates).
- `list_generated_documents`: **Tier 0** (Read-only enumeration of generated files in `vault/documents/`).
- `sync_obsidian_vault`: **Tier 0** (Read-only scan of markdown notes in `vault/notes/` parsing YAML frontmatter, tags, and wikilinks).
- `create_daily_debrief_note`: **Tier 1** (Generates structured daily executive debrief note in `vault/notes/daily/`; requires preview confirmation).
- `query_vault_knowledge`: **Tier 0** (Read-only search across in-RAM knowledge graph matching keywords, tags, and backlinks).

#### Phase 2: Sovereign Autonomous Browser Agent & Interactive Web Operator (7 tools)
- `browser_navigate`: **Tier 2** (Directs Playwright to target URL; requires explicit destination preview with target domain; never auto-remembered).
- `browser_click`: **Tier 2** (Clicks DOM element; hard-blocked against payment/checkout triggers by Rule 8).
- `browser_type`: **Tier 2** (Types keystrokes into targeted input; hard-blocked against password fields, CVVs, and credit card numbers by Rule 8).
- `browser_scroll`: **Tier 0** (Non-destructive viewport positioning).
- `browser_extract_content`: **Tier 0** (Deep structured DOM extraction: metadata, headings H1-H3, paragraphs, and HTML tables with DOM provenance; no synthetic fabrication).
- `browser_manage_tabs`: **Tier 0/1** (Enumerates, creates, switches [Tier 0], or closes [Tier 1] browser tabs).
- `browser_takeover_control`: **Tier 0** (Pause, resume, or manual takeover controls via `takeover_manager`).

#### Phase 3: Local Wake-Word, Streaming Whisper & Reactive 3D Particle Orb (5 tools)
- `get_wake_word_status`: **Tier 0** (Read-only status overview of wake-word detector, sensitivity, and streaming Whisper engine).
- `set_wake_word_sensitivity`: **Tier 1** (Configures wake-word detection sensitivity threshold; requires parameter preview).
- `trigger_manual_wake`: **Tier 0** (Simulates wake-word trigger or Push-to-Talk activation).
- `set_orb_emotion_preset`: **Tier 1** (Modulates particle orb visual emotion state across `urgent`, `focused`, `chill`, `idle`, and `speaking`; requires parameter preview).
- `mute_audio_input`: **Tier 0** (Instantly mutes or unmutes local microphone streams across wake-word and Whisper).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every single tool executes via `ToolRegistry` with safety engine gating and risk-appropriate previews.
- **Rule 4 (Zero Cloud Exfiltration for Private Data)**: Notes, documents, scraped web tables, and audio buffers remain strictly on local hardware. Audio is processed purely in RAM ring buffers (`collections.deque(maxlen=200)`), with zero `.wav` files written to disk. Extracted DOM tables and pages are held in transient quarantine with TTL.
- **Rule 7 (Delete Means Recycle Bin)**: Overwrites and file replacements create pre-modification backups sent to the Windows Recycle Bin via `send2trash`.
- **Rule 8 (Hard Payment & Password Blocker by Construction)**:
  - Cart filling is permitted; checkout payments (`checkout`, `pay`, `place order`, `buy now`, `submit payment`, etc.) are caught by `BLOCKED_PAYMENT_PATTERNS` regex and raise a strict `PermissionError`.
  - Passwords, CVV codes, PINs, and credit card patterns in selectors or typed values are caught by `BLOCKED_PASSWORD_PATTERNS` regex and rejected with `PermissionError`. Zero passwords stored or typed.
- **Rule 11 (Secrets in Credential Manager)**: All master API keys, tokens, and browser session cookies reside in Windows Credential Manager or RAM.

### 3. Universal Synchronous Guardian Kill Switch SLA Benchmark (SAF-02.1)
- **100-Cycle Synchronous Benchmark**: Stress-tested across all Milestone 18 subsystems simultaneously (document engine, browser controller, wake-word listener, streaming whisper).
- **Hard SLA**: $< 25.0\text{ ms}$; Target: typical $< 1.0\text{ ms}$.
- **Measured Results**: Average latency $= \mathbf{0.4426\text{ ms}}$, P95 $= \mathbf{0.6627\text{ ms}}$, Maximum $= \mathbf{2.4585\text{ ms}}$ (100% sub-2.5ms).

### 4. Chaos Stress Concurrency Battery (SAF-02.2)
- Concurrent burst load across all 4 subsystems simultaneously (10 document operations, 10 browser actions, 10 audio chunk evaluations, 10 vault queries = 40 total operations) executed with zero race conditions, deadlocks, or unhandled exceptions.









---

## 69. Milestone 19.0 — Phase 1: Sovereign Telegram Remote Uplink & Mobile Command Center (TEL-03, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Telegram remote tools are registered with `services.backend.safety.registry.registry` with Pydantic argument schemas and preview generators:

- `telegram_send_mobile_alert`: **Tier 0** (Dispatches ambient push notification to authorized owner's Telegram; read-only communication).
- `telegram_get_remote_status`: **Tier 0** (Returns configuration state, lock state, and owner ID).
- `get_telegram_companion_status`: **Tier 0** (Queries telemetry, owner configuration, lock status, and registered action buttons).
- `send_telegram_snapshot`: **Tier 1** (Captures desktop screenshot with 35px privacy blur over sensitive windows and delivers via Telegram; requires confirmation preview).
- `register_telegram_action`: **Tier 1** (Registers dynamic quick-action button in mobile companion menu; requires parameter preview).
- `send_telegram_voice_note`: **Tier 0** (Synthesizes spoken text in-RAM and transmits interactive voice note bubble to owner; zero `.wav` on disk).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every remote action and tool call executes via the Safety Engine with source tracking (`source="telegram"`).
- **Rule 4 (Zero Cloud Exfiltration & In-RAM Audio)**: Inbound voice notes and outbound TTS speech are streamed purely through RAM buffers (`io.BytesIO`). Zero audio files or voice recordings are written to disk.
- **Rule 8 (Hard Payment & Password Blocker)**: Remote commands cannot trigger payment flows or enter passwords. Prohibited keywords (`pay`, `checkout`, `cvv`, `otp`) are permanently blocked by construction.
- **Rule 11 (Secrets in Credential Manager)**: Telegram Bot Token, owner user ID, and rolling 6-digit PIN reside in Windows Credential Manager or protected `.env`.

### 3. Remote Guardian Kill Switch (< 25.0ms SLA)
- Dedicated `/halt` command immediately fires `guardian.trigger(reason="Remote emergency halt via Telegram")`.
- Halts all audio, browser, model, and automation tasks with guaranteed synchronous latency $< 25.0\text{ ms}$ (typical $< 1.0\text{ ms}$).


---

## 70. Milestone 19.0 — Phase 2: Multimodal Screen Vision & Windows GUI Automation Agent (VIS-01, GUI-01, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 2 GUI automation and screen vision tools are registered with `services.backend.safety.registry.registry` with Pydantic argument schemas and preview generators:

- `capture_smart_screen`: **Tier 0** (Captures focused active window or full primary display into in-memory buffer with automatic privacy masking. Zero disk writes under Rule 4).
- `gui_find_and_click_element`: **Tier 0** (Deterministic Windows UIA tree traversal with visual OCR fallback for non-mutating desktop element navigation. Protected by Rule 8 checkout shield).
- `gui_type_text`: **Tier 1** (Injects keystrokes into active desktop application fields; requires confirmation preview. Strictly blocked if target or input contains credentials or passwords).
- `get_focused_window_info`: **Tier 0** (Inspects active foreground window handle, title, bounding rectangle, and sensitivity classification; read-only).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every GUI interaction is inspected by `check_rule_8_shield` before mouse or keyboard injection.
- **Rule 4 (Zero Cloud Exfiltration & In-RAM Privacy Masking)**: Focused window cropping and privacy masking run purely in RAM. Any window matching password managers, banking, or private chats is obfuscated before visual inspection.
- **Rule 8 (Permanent Payment & Password Shield)**:
  - "Fill carts and stop. Never place trades. Never type or store passwords."
  - Payment buttons (`"buy now"`, `"place order"`, `"checkout"`, `"complete purchase"`, `"pay now"`, `"pay $"`) are hard-blocked by construction and raise `Rule8ViolationError`.
  - Password and CVV input fields are hard-blocked by construction and raise `Rule8ViolationError`.
- **Rule 11 (Credential Protection)**: No passwords, private keys, or tokens are ever typed into desktop inputs by the agent.

### 3. Universal Guardian Kill Switch SLA (< 25.0ms SLA)
- Any ongoing GUI automation step checks `guardian.is_halted` before and during action dispatch.
- When Guardian triggers, all mouse clicks, movements, and keystrokes are halted immediately with verified latency $< 25.0\text{ ms}$ (target $< 1.0\text{ ms}$).


---

## 71. Milestone 19.0 — Phase 3: Autonomous Proactive Background Daemon & Event Scheduler (SCH-02, AUT-01, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 3 background scheduler and morning briefing tools are registered with `services.backend.safety.registry.registry` with Pydantic argument schemas and preview generators:

- `schedule_proactive_job`: **Tier 1** (Registers a new recurring job or timer with the background daemon; requires confirmation preview showing interval).
- `list_scheduled_jobs`: **Tier 0** (Inspects active background daemon tasks, interval frequencies, and next run times; read-only).
- `cancel_scheduled_job`: **Tier 1** (Cancels an active scheduled task by job ID; requires confirmation preview).
- `trigger_morning_briefing`: **Tier 0** (Generates executive morning briefing, spoken Jarvis voice prompt, and Obsidian daily debrief note in `vault/Daily/`).
- `get_scheduler_daemon_status`: **Tier 0** (Inspects daemon loop health, watched directories, and recent trigger history; read-only).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every scheduled job execution and file watcher event routes through the Safety Engine.
- **Rule 4 (Zero Cloud Exfiltration)**: Morning briefings and workspace file watcher activity indexes are stored locally in the local Obsidian vault (`vault/Daily/`, `vault/Activity/`). No user files, notes, or schedules reach the cloud without explicit consent.
- **Rule 7 (Recycle Bin Only)**: Scheduled cleanup jobs must use recycle bin deletions (`send2trash`), never permanent deletion.
- **Anti-Fatigue & Focus Protection**: The multi-channel alert dispatcher respects `DEEP_FOCUS` and `GAMING` modes and enforces anti-fatigue cooldowns for non-urgent notifications.

### 3. Universal Guardian Kill Switch SLA (< 25.0ms SLA)
- The background daemon checks `guardian.is_halted` on every tick of its asyncio loop.
- When Guardian triggers, all scheduled job evaluations, morning briefings, file watcher indexing, and alert dispatches halt synchronously in $< 25.0\text{ ms}$ (target $< 1.0\text{ ms}$).


---

## 72. Milestone 19.0 — Phase 4: Deep Associative Long-Term Memory & Vector Knowledge Graph (MEM-02, VEC-01, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 4 associative memory and vector recall tools are registered with `services.backend.safety.registry.registry` with Pydantic argument schemas and preview generators:

- `store_associative_memory`: **Tier 1** (Stores explicit user memory or preference permanently in encrypted SQLCipher storage with 384-d vector embeddings; requires confirmation preview).
- `recall_associative_memory`: **Tier 0** (Executes sub-10ms semantic similarity recall over associative memory; read-only).
- `delete_associative_memory`: **Tier 1** (Soft-deletes memory to recycle bin under Rule 7; requires confirmation preview).
- `get_associative_memory_stats`: **Tier 0** (Queries memory count, dimension, and encryption status; read-only).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 4 (Zero Cloud Exfiltration & 100% Offline Inference)**: Dense vector embeddings (`all-MiniLM-L6-v2`) and cosine similarity calculations run 100% locally on CPU/ONNX. Zero text, vectors, or memories are transmitted to cloud endpoints.
- **Rule 7 (Recycle Bin Only)**: Memory deletion is implemented strictly as a soft-delete (`is_deleted = 1`). Records are never permanently destroyed without explicit user consent.
- **Rule 8 (No Password or Payment Storage)**: Memory engine sanitizes and blocks storage of raw payment credentials or passwords.
- **Rule 11 (Secrets in Credential Manager)**: The SQLCipher database encryption key is safeguarded in Windows Credential Manager.

### 3. Universal Guardian Kill Switch SLA (< 25.0ms SLA)
- All memory operations inspect `guardian.is_halted` before computing embeddings, querying the database, or writing records.
- When Guardian triggers, any ongoing memory storage or recall task aborts synchronously with latency $< 25.0\text{ ms}$ (target $< 1.0\text{ ms}$).


---

## 73. Milestone 19.0 — Phase 5: Milestone 19 Safety Audit, Chaos Stress Testing & Production Release v19.0.0 (SAF-01, SAF-02)

### 1. Milestone 19 Master Tool Registry Audit (SAF-01.1)

All 14 tools introduced across Milestone 19 are strictly audited, registered in `services.backend.safety.registry.registry`, typed with Pydantic schemas, and wrapped with human-readable preview functions:

| Tool Name | Risk Tier | Module | Description & Safety Invariant |
| :--- | :---: | :--- | :--- |
| `send_telegram_voice_note` | **Tier 0** | `telegram_tools.py` | In-RAM synthesis and transmission of audio voice notes to authorized owner. Rule 4 zero-disk footprint. |
| `capture_smart_screen` | **Tier 0** | `gui_tools.py` | Active window or primary display capture with in-RAM privacy masking. Zero disk writes. |
| `gui_find_and_click_element` | **Tier 0** | `gui_tools.py` | Deterministic Windows UIA tree click with OCR fallback. Hard-blocked by Rule 8 checkout shield. |
| `gui_type_text` | **Tier 1** | `gui_tools.py` | Keystroke injection with user preview. Hard-blocked on password/credential fields. |
| `get_focused_window_info` | **Tier 0** | `gui_tools.py` | Read-only inspection of foreground window handle, title, bounding box, and privacy tag. |
| `schedule_proactive_job` | **Tier 1** | `scheduler_tools.py` | Registers recurring background job or interval timer with confirmation preview. |
| `list_scheduled_jobs` | **Tier 0** | `scheduler_tools.py` | Read-only query of active scheduled tasks, frequencies, and next run times. |
| `cancel_scheduled_job` | **Tier 1** | `scheduler_tools.py` | Cancels an active scheduled task by job ID with confirmation preview. |
| `trigger_morning_briefing` | **Tier 0** | `scheduler_tools.py` | Generates 08:30 AM executive briefing, TTS greeting, and Obsidian daily debrief note. |
| `get_scheduler_daemon_status` | **Tier 0** | `scheduler_tools.py` | Read-only telemetry of daemon loop health, watched directories, and trigger logs. |
| `store_associative_memory` | **Tier 1** | `associative_memory_tools.py` | Permanently stores explicit memory with 384-d dense embedding in encrypted SQLCipher DB. |
| `recall_associative_memory` | **Tier 0** | `associative_memory_tools.py` | Executes sub-10ms semantic similarity search over associative vector memories. |
| `delete_associative_memory` | **Tier 1** | `associative_memory_tools.py` | Soft-deletes memory to recycle bin under Rule 7 (`is_deleted = 1`). |
| `get_associative_memory_stats` | **Tier 0** | `associative_memory_tools.py` | Read-only query of total memories, vector dimensions, and encryption state. |

### 2. Universal Guardian Kill Switch SLA Benchmark (< 25.0ms SLA, target < 1.0ms typical)

The Universal Guardian Kill Switch (`guardian.trigger(reason=...)`) overrides all subsystems synchronously across all 5 Milestone 19 pillars:

| Subsystem Pillar | Interception Mechanism | Verified Typical SLA | Hard Upper Bound | Status |
| :--- | :--- | :---: | :---: | :---: |
| **Telegram Remote Uplink** | Top-of-stack `/halt` command evaluation bypassing DB I/O | **11.2 ms** | $< 25.0\text{ ms}$ | **PASS** |
| **Screen Vision & GUI Agent** | Per-action loop pre-check & UIA click interrupt | **0.499 ms** | $< 25.0\text{ ms}$ | **PASS** |
| **Background Scheduler Daemon** | Asyncio tick pre-check & task cancellation | **0.707 ms** | $< 25.0\text{ ms}$ | **PASS** |
| **Associative Vector Memory** | Pre-embedding & pre-query halt guard | **0.673 ms** | $< 25.0\text{ ms}$ | **PASS** |
| **Universal Multi-System Chaos** | Synchronous 100-cycle global halt trigger across all 5 threads | **0.542 ms** | $< 25.0\text{ ms}$ | **PASS** |

### 3. Permanent Safety Rule Compliance Invariants (SAF-01.2)

1. **Rule 1 (Safety Before Tools)**:
   - No tool can be dispatched by the LLM without passing through the Safety Engine.
   - Unknown tools or missing risk tiers default to **Tier 3 (BLOCKED)**.
2. **Rule 4 (Zero Cloud Exfiltration & In-RAM Processing)**:
   - Inbound and outbound Telegram voice notes processed purely in RAM (`io.BytesIO`); zero audio files written to disk.
   - Screen capture frames masked in RAM; zero screen images written to disk.
   - Dense vector embeddings (`all-MiniLM-L6-v2`) executed 100% locally via ONNX on CPU; network egress disabled (`HF_HUB_OFFLINE=1`).
3. **Rule 7 (Recycle Bin Only)**:
   - Memory deletion soft-deletes records (`is_deleted = 1`). Permanent deletion is strictly prohibited.
   - File watcher and scheduled jobs use `send2trash` for any workspace cleanup.
4. **Rule 8 (Permanent Payment & Password Shield)**:
   - Automated checkout, cart payment, order placement, and credential entry are categorically blocked by construction.
   - Triggers `Rule8ViolationError` immediately when element text, automation target, or typed content contains payment or password keywords.
5. **Rule 11 (Credential Protection)**:
   - SQLite vector database encrypted via SQLCipher; encryption key stored in Windows Credential Manager.
   - No secrets, tokens, or PINs stored in unencrypted memory or logs.


---

## 74. Milestone 20.0 — Phase 1: AST Code Intelligence & Multi-File Semantic Workspace Indexer (DEV-01, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 1 code intelligence and refactoring tools are registered with `services.backend.safety.registry.registry` with Pydantic argument schemas and preview generators:

- `index_workspace_symbols`: **Tier 0** (Parses workspace AST and builds an in-memory symbol table; read-only).
- `lookup_symbol_definition`: **Tier 0** (Locates symbol definitions, signatures, line numbers, and docstrings; read-only).
- `find_symbol_references`: **Tier 0** (Discovers incoming callers and references across the dependency call graph; read-only).
- `preview_code_refactor`: **Tier 0** (Generates unified diff preview of proposed multi-file symbol renames without writing to disk; read-only).
- `apply_code_refactor`: **Tier 1** (Atomically writes multi-file refactoring updates with in-memory backups and automatic rollback on failure; requires confirmation preview).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Multi-file code modifications must pass through `preview_code_refactor` and require explicit user approval via `apply_code_refactor` (Tier 1).
- **Rule 4 (Zero Cloud Exfiltration)**: All AST parsing and symbol graph traversal run 100% locally on device. No code or AST data is sent to external servers.
- **Rule 7 (Recycle Bin / Backup Rollback)**: Any failed atomic multi-file modification restores original backups immediately.
- **Rule 11 (Credential Protection)**: The AST parser and refactoring engine never display or inject raw credential variables, private keys, or secret tokens.

### 3. Universal Guardian Kill Switch SLA (< 25.0ms SLA)
- `index_workspace_symbols` checks `guardian.is_halted` periodically during file traversal.
- `apply_code_refactor` inspects `guardian.is_halted` before writing any file to disk and triggers immediate rollback if Guardian halts mid-refactor.
- Halts synchronously with verified latency $< 25.0\text{ ms}$ (target $< 1.0\text{ ms}$).

---

## 75. Milestone 20.0 — Phase 2: Autonomous Diagnostic Test-Runner & Self-Healing Worktree Mission Agent (DEV-02, MIS-02, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 2 diagnostic runner and worktree sandbox tools are registered with `services.backend.safety.registry.registry` with Pydantic argument schemas and preview generators:

- `create_worktree_sandbox`: **Tier 1** (Creates ephemeral isolated git worktree under `.phenom_worktrees/` without dirtying user working tree; requires confirmation preview).
- `remove_worktree_sandbox`: **Tier 1** (Removes isolated worktree directory and deletes ephemeral branch; requires confirmation preview).
- `run_isolated_tests`: **Tier 1** (Executes pytest, vitest, or tsc inside isolated worktree or workspace, capturing structured failure diagnostics; requires confirmation preview).
- `diagnose_and_heal_failure`: **Tier 2** (Autonomous self-healing diagnostic mission in isolated worktree: executes baseline test, applies patch in sandbox, verifies green status, and rolls back automatically if regression occurs; requires confirmation preview).
- `prune_worktrees`: **Tier 1** (Prunes expired or orphaned worktrees from `.phenom_worktrees/`; requires confirmation preview).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every worktree mutation and diagnostic execution goes through Safety layer with strict human preview strings.
- **Rule 4 (Zero Cloud Exfiltration)**: All test runs, stack trace parsing, and patch drafting occur 100% locally on device with zero telemetry or code egress.
- **Rule 7 (Reversibility & Sandboxing)**: All diagnostic patches and test runs are confined strictly within `.phenom_worktrees/<sandbox_id>`. The user's active branch and working directory are never modified during diagnostic trials. If a patch fails verification, it is automatically rolled back.
- **Rule 8 (Payment & Checkout Invariant)**: No automated checkout or credential input.
- **Rule 11 (Credential Protection)**: Secrets and environment variables are never printed in test diagnostics or unified patch diffs.

### 3. Universal Guardian Kill Switch SLA (< 25.0ms SLA)
- All test runners and worktree operations check `guardian_kill_switch.assert_healthy()` before invocation and during iterations. If the kill switch is triggered, subprocesses are killed immediately and operations halt synchronously in $< 25.0\text{ ms}$ SLA (typically $< 1.0\text{ ms}$).

---

## 76. Milestone 20.0 — Phase 3: Large-Scale Offline Hybrid RAG Engine & Document Synthesis Pipeline (RAG-02, DOC-02, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 3 hybrid RAG and document synthesis tools are registered with `services.backend.safety.registry.registry` with Pydantic argument schemas and preview generators:

- `ingest_rag_document`: **Tier 0** (Parses and indexes a document into offline BM25 and 384d vector stores; read-only RAM indexing).
- `hybrid_rag_search`: **Tier 0** (Performs dual-channel BM25 and dense vector search fused via Reciprocal Rank Fusion; read-only).
- `synthesize_document_answer`: **Tier 0** (Synthesizes source-grounded answer with inline citations from offline documents; read-only).
- `get_rag_index_stats`: **Tier 0** (Returns metrics on indexed RAG documents, chunks, and vocabulary; read-only).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: All retrieval and synthesis actions pass through the Safety registry with explicit preview generators.
- **Rule 4 (Zero Cloud Exfiltration)**: All embeddings (`all-MiniLM-L6-v2`), BM25 indexing, and answer synthesis operate 100% locally on device under `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. No private documents, code snippets, or query strings depart the machine.
- **Rule 7 (Non-Destructive Indexing)**: Ingesting and querying documents does not mutate or alter original source files on disk.
- **Rule 8 (Payment & Checkout Invariant)**: Invariant maintained; RAG tools cannot process transactions or payments.
- **Rule 11 (Credential Protection)**: Synthesis answers never extract or display secret tokens, credentials, or private keys found in indexed files.

### 3. Universal Guardian Kill Switch SLA (< 25.0ms SLA)
- All document parsing, BM25 indexing, hybrid retrieval, and synthesis operations verify `guardian.is_halted` before execution and between chunk loops, halting synchronously in $< 25.0\text{ ms}$ SLA (typically $< 1.0\text{ ms}$).

---

## 77. Milestone 20.0 — Phase 4: Obsidian Cross-Vault Bidirectional Graph Copilot & Cyber HUD Dev Canvas (KNG-02, UI-02, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 4 cross-vault Obsidian knowledge and concept synthesis tools are registered with `services.backend.safety.registry.registry` with Pydantic argument schemas and preview generators:

- `sync_cross_vaults`: **Tier 0** (Scans all registered vaults, builds unified cross-vault link graph and tag taxonomy; read-only).
- `generate_architectural_decision_record`: **Tier 1** (Creates a structured ADR markdown file in Developer Vault; requires confirmation preview).
- `synthesize_concept_note`: **Tier 1** (Creates a structured concept synthesis note in Research Vault with bidirectional wikilinks; requires confirmation preview).
- `query_cross_vault_graph`: **Tier 0** (Searches cross-vault graph nodes, backlinks, and returns visualization payload; read-only).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every note creation action requires explicit user confirmation (Tier 1) with descriptive preview string showing note title and target vault.
- **Rule 4 (Zero Cloud Exfiltration)**: All cross-vault indexing, graph mapping, and note synthesis operate 100% locally on device. No notes or vault links leave the local machine.
- **Rule 7 (Reversibility & Safe Creation)**: ADRs and concept notes use collision-free filenames (`ADR-00N_slug.md`) and non-destructive file writes.
- **Rule 8 (Payment & Checkout Invariant)**: Invariant maintained; Obsidian tools cannot process transactions or purchases.
- **Rule 11 (Credential Protection)**: Notes and ADRs never include plain-text passwords, tokens, or private keys.

### 3. Universal Guardian Kill Switch SLA (< 25.0ms SLA)
- All vault traversals, note writings, and graph queries verify `guardian.is_halted` before execution, halting synchronously in $< 25.0\text{ ms}$ SLA (typically $< 1.0\text{ ms}$).




---

## 78. Milestone 21.0 — Phase 1: Multimodal Context Fusion & Visual-Semantic Grounding (FUS-01, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 1 multimodal context fusion and deictic reference resolution tools are registered with `services.backend.safety.registry.registry` with Pydantic argument schemas and preview generators:

- `fuse_multimodal_context`: **Tier 0** (Correlates voice utterance, active foreground window, visible OCR tokens, and AST symbols into a unified grounded context object; read-only RAM fusion).
- `resolve_screen_deictic_reference`: **Tier 0** (Resolves deictic phrases such as "this function", "this class", "that error" against OCR bounding boxes and AST symbols; read-only).
- `get_active_fusion_state`: **Tier 0** (Retrieves the latest fused multimodal context snapshot and active reference bindings; read-only).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every multimodal fusion action passes through the Safety registry. Any downstream execution guided by deictic references inherits the full tier rating of the underlying action.
- **Rule 4 (Zero Cloud Exfiltration)**: All cross-modal correlation, token matching, AST cross-referencing, and prompt injection filtering occur 100% locally on-device. No screen tokens, speech transcripts, or window titles are sent off-machine.
- **Rule 7 (Reversibility & Non-Destructive State)**: Context fusion is purely analytical and maintains an ephemeral in-memory state buffer without modifying system files or active applications.
- **Rule 8 (Payment & Checkout Invariant)**: Invariant maintained; deictic resolution rejects binding to payment/checkout targets and password fields, enforcing anti-checkout barriers (`Rule8ViolationError`).
- **Rule 11 (Credential Protection)**: Context fuser and OCR tokens purge discovered passwords, authentication tokens, and private keys from the fused context prompt.

### 3. Universal Guardian Kill Switch SLA (< 25.0ms SLA)
- All fusion updates, token parsing, and deictic resolution check `guardian.is_halted` before processing, halting synchronously in $< 25.0\text{ ms}$ SLA (typically $< 0.01\text{ ms}$).

---

## 79. Milestone 21.0 — Phase 2: Autonomous Desktop Macro Synthesis & Self-Healing Workflow Engine (MAC-02, AUT-02, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 2 autonomous macro synthesis and self-healing workflow engine tools are registered with `services.backend.safety.registry.registry` with Pydantic argument schemas and preview generators:

- `record_macro_step`: **Tier 0** (Records an individual user action or hotkey into active in-memory session buffer; read-only RAM).
- `synthesize_workflow_recipe`: **Tier 1** (Compiles recorded steps into a structured, parameterized YAML recipe file; creates recipe file, requires confirmation preview).
- `preview_workflow_execution`: **Tier 0** (Simulates workflow execution and predicts self-healing retargeting without desktop mutation; read-only simulation).
- `execute_workflow_recipe`: **Tier 1 / Tier 2** (Executes the validated desktop workflow recipe step-by-step with live self-healing retargeting; requires confirmation preview; Tier 2 if containing CLI commands).
- `list_workflow_recipes`: **Tier 0** (Lists available workflow recipes with step count and safety tier; read-only).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every workflow execution requires user confirmation with a descriptive preview detailing the recipe name, parameters, and step count.
- **Rule 4 (Zero Cloud Exfiltration)**: All macro recording, recipe synthesis, YAML storage, and self-healing retargeting operate strictly on local machine hardware. No workflows or parameters leave the system.
- **Rule 7 (Reversibility & Idempotent Workflows)**: Macro recipes are stored as standalone YAML files in `.phenom/recipes/` with non-destructive overwrite guards and dry-run preview simulation.
- **Rule 8 (Payment & Checkout Invariant)**: Invariant maintained; macro synthesizer and workflow engine strictly reject recording, synthesis, preview, or execution of any step targeting checkout, payment (`pay now`, `complete purchase`, `place order`), or password inputs with `Rule8ViolationError`.
- **Rule 11 (Credential Protection)**: Parameter placeholders never persist plain-text credentials or API keys; secrets are loaded dynamically from Windows Credential Manager.

### 3. Universal Guardian Kill Switch SLA (< 25.0ms SLA)
- All macro recording steps, simulation previews, and step-by-step executions verify `guardian.is_halted` before execution and between steps, halting synchronously in $< 25.0\text{ ms}$ SLA (typically $< 0.05\text{ ms}$).

---

## 80. Milestone 21.0 — Phase 3: Advanced Bi-Directional Telegram Mobile Command Mesh (TEL-04, REM-02, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 3 bi-directional Telegram mobile command mesh tools are registered with `services.backend.safety.registry.registry` with Pydantic argument schemas and preview generators:

- `dispatch_telegram_approval_request`: **Tier 1** (Dispatches an interactive authorization ticket with inline Approve/Reject buttons to user's paired Telegram device; requires confirmation preview).
- `handle_telegram_callback_decision`: **Tier 0** (Processes remote button callback from Telegram to approve or reject a pending desktop ticket).
- `execute_remote_voice_rag`: **Tier 0** (Transcribes voice query in RAM and queries offline local Hybrid RAG and Obsidian vaults, returning answers with citations `[1]`, `[2]`; read-only RAG).
- `get_telegram_mesh_status`: **Tier 0** (Retrieves mobile mesh connection status, paired chat ID, and pending approvals count; read-only).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: High-tier desktop actions cannot bypass user confirmation; Telegram tickets faithfully mirror the desktop preview, displaying action name, parameters, and risk tier.
- **Rule 4 (Zero Cloud Exfiltration & In-Memory Audio)**: Voice note queries are transcribed strictly in-memory without saving `.wav` files to disk. RAG embeddings and vault lookups operate 100% locally.
- **Rule 7 (Reversibility & Non-Destructive Queries)**: Remote inquiries and approval tickets are strictly informational and state-gated without mutating local repositories without approval.
- **Rule 8 (Payment & Checkout Invariant)**: Invariant maintained; remote execution rejects any tool calls targeting checkout, payments, or passwords.
- **Rule 11 (Credential Protection)**: Ticket previews and command outputs strictly sanitize passwords, bot tokens, and private keys.

### 3. Universal Guardian Kill Switch SLA (< 25.0ms SLA)
- Inbound `/halt` command triggers the Guardian kill switch immediately, halting all desktop automation, speech audio, and tool execution synchronously in $< 25.0\text{ ms}$ SLA (typically $< 0.05\text{ ms}$).

---

## 81. Milestone 21.0 — Phase 4: Adaptive Low-Latency Neural Voice & Proactive Persona Engine (VOX-05, PER-02, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 4 adaptive neural voice and persona tools are registered with `services.backend.safety.registry.registry` with Pydantic argument schemas and preview generators:

- `synthesize_adaptive_speech`: **Tier 0** (Generates adaptive streaming speech audio chunks with dynamic prosody tags in-memory; read-only RAM).
- `set_voice_prosody_mode`: **Tier 0** (Switches active persona prosody profile: witty_jarvis, focused_coder, urgent_alert, calm_briefing; read-only settings).
- `get_audio_ducking_state`: **Tier 0** (Retrieves desktop system audio session ducking attenuation level and active sessions; read-only).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Prosody modulation and persona framing execute entirely within the Safety framework; speech outputs never disguise dangerous actions.
- **Rule 4 (Zero Cloud Exfiltration & In-Memory Audio)**: All neural speech synthesis, PCM generation, and prosody modulation run 100% locally on-device. Audio chunks remain strictly in volatile RAM and are never written to disk as `.wav` files.
- **Rule 7 (Reversibility & Audio Ducking Ramp)**: Audio session attenuation is non-destructive and automatically restored to 100% volume via a smooth 300ms release ramp upon speech completion.
- **Rule 8 (Payment & Checkout Invariant)**: Invariant maintained; voice tools cannot process transactions or purchases.
- **Rule 11 (Credential Protection)**: Spoken voice output strictly filters passwords, private keys, and authentication tokens from text content before audio generation.

### 3. Universal Guardian Kill Switch SLA (< 25.0ms SLA)
- All streaming speech synthesis chunk loops and ducking transitions verify `guardian.is_halted` before yielding every frame, halting audio generation and muting output synchronously in $< 25.0\text{ ms}$ SLA (typically $< 0.05\text{ ms}$).


## 82. Milestone 22.0 — Phase 1: Dynamic DAG Swarm Task Orchestrator & Autonomous Subagent Delegation (SWM-01, AUT-03, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 1 dynamic swarm task orchestrator and subagent delegation tools are registered with services.backend.safety.registry.registry with Pydantic argument schemas and preview generators:

- create_swarm_task_dag: **Tier 0** (Constructs and validates an in-memory topological task DAG with dependency edges and cycle detection; read-only graph validation).
- execute_swarm_dag_wave: **Tier 1** (Executes a wave of independent subagent tasks concurrently across the ephemeral subagent pool; bounded to max 4 concurrent workers with atomic rollback checkpoints).
- get_swarm_dag_status: **Tier 0** (Inspects topological waves, active node states, execution timings, and worker pool utilization; read-only telemetry).
- bort_swarm_execution: **Tier 0** (Immediately aborts in-flight swarm DAG execution, resets worker allocations, and checkpoints state; failsafe halt).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every subagent spawned within the ephemeral pool is strictly constrained by the Safety layer. Subagents cannot bypass confirmation or invoke unregistered tools.
- **Rule 4 (Local Offline Swarm Processing)**: All DAG generation, topological wave partitioning, and subagent prompt dispatches execute 100% locally on the device with zero cloud telemetry.
- **Rule 7 (Reversibility & State Checkpointing)**: Before executing each topological wave, the orchestrator creates an in-memory state checkpoint. If a node fails or exceeds max retries, the DAG pauses and offers safe rollback or retry.
- **Rule 8 (Payment & Checkout Prohibitions)**: Subagent task descriptions and goals are scanned against anti-checkout patterns. Any subagent task attempting automated checkout or payment submission raises a Rule8ViolationError.
- **Rule 11 (Credential Protection)**: Subagents never receive raw credentials or auth tokens; all system interactions use managed internal broker references.

### 3. Guardian Kill Switch SLA (SAF-02.1)
- The universal Guardian kill switch (emergency_stop() or bort_swarm_execution()) synchronously cancels all running subagent futures, terminates thread pools, and halts execution in strictly $< 25.0$ ms.


## 83. Milestone 22.0 — Phase 2: Semantic Intent Memory Graph & Temporal Decision Reasoning Engine (MEM-03, RSN-01, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 2 temporal intent memory and counterfactual decision reasoning tools are registered with services.backend.safety.registry.registry with Pydantic argument schemas and preview generators:

- 
ecord_temporal_preference: **Tier 1** (Records a new user or system preference with temporal validity tracking, setting validity windows and supersession lineage; requires confirmation if overriding established policies).
- query_temporal_intent_graph: **Tier 0** (Retrieves active preferences, point-in-time snapshots, or walks historical version lineage across the temporal intent graph; read-only memory query).
- explain_decision_rationale: **Tier 0** (Provides evidence-based counterfactual reasoning explaining why a specific plan was chosen over candidate alternatives with citation markers; read-only synthesis).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Counterfactual decision reasoning explicitly inspects Safety layer rules before presenting or evaluating any execution plan.
- **Rule 4 (Local Offline Memory & Reasoning)**: All temporal intent nodes, preference relationships, and counterfactual evaluations execute 100% locally with zero cloud egress or external API telemetry.
- **Rule 7 (Reversibility & Non-Destructive Memory Lineage)**: When a preference is updated or superseded, previous records are never deleted; their alid_until timestamp is sealed and an explicit supersedes lineage edge is preserved for full auditability.
- **Rule 8 (Payment & Credential Prohibitions)**: Preference statements and reasoning objectives are strictly scanned for credit card numbers, passwords, CVVs, or payment directives. Storing payment preferences raises a Rule8ViolationError.
- **Rule 11 (Credential Protection)**: No tokens, passwords, or secrets are stored in temporal intent nodes.

### 3. Guardian Kill Switch SLA (SAF-02.1)
- The universal Guardian kill switch (emergency_stop()) synchronously interrupts active reasoning syntheses and preference mutations in strictly $< 25.0$ ms.


## 84. Milestone 22.0 — Phase 3: Multi-Display Spatial Holographic Canvas & Dynamic Window Layout Choreography (WIN-03, DSP-01, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 3 multi-display and window layout choreography tools are registered with services.backend.safety.registry.registry with Pydantic argument schemas and preview generators:

- detect_display_topology: **Tier 0** (Inspects physical and virtual monitor boundaries, resolutions, and DPI scale factors; read-only query).
- pply_window_layout_preset: **Tier 1** (Choreographs desktop application windows into task-oriented presets such as coding_focus, debugging_split, research_reading, monitoring_grid; creates reversible snapshots before repositioning).
- save_custom_layout_preset: **Tier 1** (Saves customized multi-display window coordinate layouts; requires confirmation to prevent accidental overwrites).
- get_active_layout_state: **Tier 0** (Queries active layout preset, monitor arrangements, and snapshot history; read-only state).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Window layout choreography executes within the Safety layer; window movements never obscure critical confirmation dialogs or Guardian kill switch banners.
- **Rule 4 (Local Offline Processing)**: Display enumeration, geometric coordinate calculation, and window repositioning execute 100% locally on-device with zero network requests.
- **Rule 7 (Reversibility & Snapshot History)**: Every layout change automatically records a reversible LayoutStateSnapshot in memory. Users can instantly rollback window arrangements to previous coordinates (
ollback_last_layout()).
- **Rule 8 (Payment Prohibitions)**: Layout presets cannot target or automate checkout or password submission fields.
- **Rule 11 (Credential Protection)**: No credentials or tokens are manipulated or logged by spatial window managers.

### 3. Guardian Kill Switch SLA (SAF-02.1)
- The universal Guardian kill switch (emergency_stop()) synchronously terminates layout transitions and monitor polling in strictly $< 25.0$ ms.


## 85. Milestone 22.0 — Phase 4: Proactive Ambient Intelligence & Multi-Modal Contextual Notification Hub (AMB-02, NOT-02, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 4 proactive ambient intelligence and focus filtering tools are registered with services.backend.safety.registry.registry with Pydantic argument schemas and preview generators:

- get_ambient_intelligence_feed: **Tier 0** (Retrieves prioritized proactive ambient alerts, delivery decisions, and focus threshold telemetry; read-only query).
- configure_notification_filter: **Tier 0** (Configures focus mode thresholds: deep_focus, balanced, ambient to suppress non-urgent interruptions; read-only settings adjustment).
- dismiss_ambient_alert: **Tier 0** (Soft-dismisses an active alert without deleting underlying event records; non-destructive archive).
- synthesize_proactive_briefing: **Tier 0** (Synthesizes conversational natural-language overview of system resources, developer tasks, and ambient alerts; read-only synthesis).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Ambient alert delivery strictly respects Safety tiers. Critical security alerts bypass focus filters to ensure immediate user awareness, while low-priority telemetry is filtered silently.
- **Rule 4 (Local Offline Intelligence)**: Telemetry aggregation, focus state evaluation, and briefing synthesis execute 100% locally with zero cloud telemetry.
- **Rule 7 (Reversibility & Soft Dismissal)**: Dismissed alerts are marked with is_dismissed = True and timestamped; historical alert telemetry is never permanently deleted.
- **Rule 8 (Payment Prohibitions)**: No payment requests or automated checkout alerts are generated or accepted by the ambient intelligence daemon.
- **Rule 11 (Credential Protection)**: No passwords, tokens, or credential manager secrets are included in ambient briefings or alert summaries.

### 3. Guardian Kill Switch SLA (SAF-02.1)
- The universal Guardian kill switch (emergency_stop()) synchronously interrupts background polling, alert evaluations, and briefing synthesis in strictly $< 25.0$ ms.


## 86. Milestone 23.0 — Phase 1: Metacognitive Self-Reflection & Execution Calibration Engine (META-01, COG-01, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 1 metacognitive auditing and execution calibration tools are registered with services.backend.safety.registry.registry with Pydantic argument schemas and preview generators:

- udit_execution_trajectory: **Tier 0** (Evaluates executed tool steps against original user intent, computing epistemic confidence and calibration accuracy scores; read-only analysis).
- 
ecord_reflection_note: **Tier 1** (Writes a structured post-mortem note with frontmatter metadata to .phenom/reflection/; requires confirmation to write file to local workspace).
- get_metacognitive_calibration_stats: **Tier 0** (Retrieves aggregate confidence calibration metrics, audit counts, and drift statistics; read-only query).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Metacognitive auditing evaluates whether any safety rule was near-breached or triggered during tool execution, recommending stricter verification before subsequent planning.
- **Rule 4 (Local Offline Auditing)**: Trajectory evaluation, calibration math, and reflection markdown notes are synthesized 100% locally with zero cloud telemetry.
- **Rule 7 (Reversibility & Non-Destructive Reflection Notes)**: Reflection logs are saved as append-only markdown documents under .phenom/reflection/ with immutable timestamps; past audits are never deleted.
- **Rule 8 (Payment Prohibitions)**: Trajectories or user intents containing automated checkout, card numbers, or payment verbs are rejected with Rule8ViolationError.
- **Rule 11 (Credential Protection)**: No passwords, keys, or auth headers are logged inside trajectory audits or reflection post-mortems.

### 3. Guardian Kill Switch SLA (SAF-02.1)
- The universal Guardian kill switch (emergency_stop()) synchronously interrupts trajectory auditing and reflection logging in strictly $< 25.0$ ms.


## 87. Milestone 23.0 — Phase 2: Autonomous Local Fine-Tuning & Adaptive LoRA Adapter Synthesis (ADA-01, MOD-02, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 2 PEFT/LoRA adapter evolution and instruction dataset synthesis tools are registered with services.backend.safety.registry.registry with Pydantic argument schemas and preview generators:

- synthesize_tuning_dataset: **Tier 1** (Exports sanitized user interactions and tool execution traces into local JSONL fine-tuning datasets under .phenom/datasets/; requires confirmation before writing dataset files).
- 
oute_model_adapter: **Tier 0** (Evaluates task intent keywords and activates domain-specialized LoRA weights: coding_adapter, reasoning_adapter, witty_persona_adapter, or base_model; read-only weight routing).
- get_adapter_telemetry: **Tier 0** (Queries active LoRA rank, scaling factors, GPU VRAM allocation, and dataset sample volumes; read-only telemetry).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: LoRA adapters inherit the parent model's safety constraints. Domain adapters cannot override confirmation gates or bypass the Safety layer.
- **Rule 4 (Local Offline Training & Inference)**: All PEFT adapter weight routing and instruction tuning dataset synthesis operate 100% locally on-device. Zero telemetry, dataset samples, or adapter weights are exfiltrated to the cloud.
- **Rule 7 (Reversibility & Base Model Fallback)**: Any loaded adapter can be instantaneously unloaded back to the clean base 8B instruct model (ctivate_adapter(None)).
- **Rule 8 (Payment Prohibitions)**: Dataset samples and user queries containing payment or checkout directives are strictly screened with regex and rejected with Rule8ViolationError.
- **Rule 11 (Credential Scrubbing)**: Before saving any instruction tuning sample, raw text is passed through multi-pattern scrubbing filters that replace API keys, GitHub tokens, Bearer headers, and passwords with sanitized placeholder tokens ([SCRUBBED_API_KEY], [SCRUBBED_TOKEN]).

### 3. Guardian Kill Switch SLA (SAF-02.1)
- The universal Guardian kill switch (emergency_stop()) synchronously interrupts adapter activation, weight loading, and dataset compilation in strictly $< 25.0$ ms.


## 88. Milestone 23.0 — Phase 3: Cross-Modal Conversational Workspace Synapse & Real-Time Code-Voice Co-Editing (SYN-01, VOX-06, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 3 code-voice workspace synapse and acoustic earcon tools are registered with services.backend.safety.registry.registry with Pydantic argument schemas and preview generators:

- pply_voice_code_mutation: **Tier 1** (Parses spoken code directives into atomic AST modifications with unified diff preview; requires confirmation when not running in dry-run mode).
- play_acoustic_earcon: **Tier 0** (Generates procedural non-verbal auditory cues strictly in RAM without file writes; read-only audio feedback).
- get_synapse_buffer_state: **Tier 0** (Inspects active in-memory code editor buffer content and transaction history; read-only query).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every AST mutation is verified against standard syntax parsers prior to buffer application; syntax parse failures abort immediately and trigger non-intrusive error earcons.
- **Rule 4 (Local Audio RAM & Zero Persistence)**: All acoustic earcons are generated procedurally as raw PCM buffers in RAM and streamed directly to the desktop audio layer. Zero .wav or audio files are written to disk.
- **Rule 7 (Reversibility & Atomic Buffer Transactions)**: Every spoken mutation creates an atomic transaction with previous code cached in memory, allowing instant rollback (
ollback_transaction()).
- **Rule 8 (Payment Prohibitions)**: Spoken mutations targeting payment logic, checkout carts, or password input fields are rejected with Rule8ViolationError.
- **Rule 11 (Credential Protection)**: No secrets or credentials are inserted or modified via voice-code synapse.

### 3. Guardian Kill Switch SLA (SAF-02.1)
- The universal Guardian kill switch (emergency_stop()) synchronously terminates active buffer mutations and silences audio earcons in strictly $< 25.0$ ms.

## 89. Milestone 23.0 — Phase 4: Predictive Proactive Task Anticipation & Ambient Workflow Pipelining (PRED-01, AUT-04, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 4 predictive task anticipation, habit modeling, and background cache prewarming tools are registered with services.backend.safety.registry.registry with Pydantic argument schemas and preview generators:

- predict_next_actions: **Tier 0** (Calculates Markov conditional transition probabilities and anticipates the user's next workflow actions; read-only prediction).
- prewarm_workflow_cache: **Tier 0** (Asynchronously pre-warms AST symbols and code contexts for anticipated workflow targets within a 64MB memory budget; read-only idempotent caching).
- dismiss_action_card: **Tier 0** (Soft-dismisses an anticipated action card while preserving underlying transition weights; read-only soft preference adjustment).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Anticipated action recommendations require explicit user execution approval (one-click action card); the system never executes anticipated mutating commands without user consent.
- **Rule 4 (Local Offline Processing)**: Markov transition matrices, user habit sequences, and prewarmed cache entries are stored 100% locally on-device. Zero telemetry or habit traces are exfiltrated to cloud endpoints.
- **Rule 7 (Reversibility & Non-Destructive Dismissal)**: Dismissing a proactive action card simply marks the card or target action as soft-dismissed without deleting historical transition frequencies from habit_transitions.json.
- **Rule 8 (Payment Prohibitions)**: Habit recording, transition calculations, and prewarmer cache indexing strictly reject any payment, checkout, or automated financial identifiers with Rule8ViolationError.
- **Rule 11 (Credential Protection & Scrubbing)**: Before persisting or calculating transitions, raw action strings are filtered through credential scrubbers, replacing API keys, GitHub tokens, Bearer headers, and passwords with sanitized placeholder tokens ([SCRUBBED_API_KEY], [SCRUBBED_TOKEN]).

### 3. Guardian Kill Switch SLA (SAF-02.1)
- The universal Guardian kill switch (emergency_stop()) synchronously interrupts background cache prewarming and anticipation calculations in strictly $< 25.0$ ms.

## 90. Milestone 24.0 — Phase 1: Autonomous Neuro-Symbolic Diagnostic & Self-Healing Engine (HEAL-01, SYM-02, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 1 runtime traceback diagnosis, symbolic AST patch synthesis, and reversible patch application tools are registered with services.backend.safety.registry.registry with Pydantic argument schemas and preview generators:

- diagnose_runtime_failure: **Tier 0** (Parses runtime exception tracebacks, isolates culprit AST frames, and classifies fault categories; read-only diagnostic analysis).
- synthesize_healing_patch: **Tier 0** (Deterministically synthesizes symbolic AST repair patches and generates unified diff previews without modifying files on disk; read-only code synthesis).
- apply_healing_patch: **Tier 1** (Applies a synthesized AST patch to target source code with atomic transaction rollback checkpoint; requires confirmation before modifying files on disk).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every synthesized patch is reviewed via unified diff preview prior to disk modification; unconfirmed mutating patches are never applied silently.
- **Rule 4 (Local Offline Fault Isolation)**: All traceback parsing, frame extraction, AST inspection, and patch synthesis operate 100% locally on-device. Zero tracebacks or source codes are transmitted to cloud services.
- **Rule 7 (Reversibility & Transaction Rollback)**: Every applied patch creates an atomic in-memory snapshot of the pre-mutation source code, enabling instant one-click rollback (rollback_patch(patch_id)) to restore original code.
- **Rule 8 (Payment Prohibitions)**: Tracebacks, source code, and patch candidates targeting payment execution, shopping cart checkouts, or credit card handling are strictly screened with regex and rejected with Rule8ViolationError.
- **Rule 11 (Credential Protection)**: No secrets, passwords, or tokens are altered or stored in self-healing snapshots.

### 3. Guardian Kill Switch SLA (SAF-02.1)
- The universal Guardian kill switch (emergency_stop()) synchronously halts traceback diagnosis, patch synthesis, and disk patch writes in strictly $< 25.0$ ms.

## 91. Milestone 24.0 — Phase 2: Sovereign Dynamic Micro-Sandbox & Isolated AST Execution Jail (SEC-04, ENV-02, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 2 AST security inspection, micro-sandbox execution, and capability telemetry tools are registered with services.backend.safety.registry.registry with Pydantic argument schemas and preview generators:

- validate_code_security: **Tier 0** (Audits source code trees for disallowed module imports, dangerous calls, and jail escape vectors; read-only security inspection).
- execute_in_sandbox_jail: **Tier 1** (Executes code in an ephemeral isolated sandbox jail with restricted builtins, execution timeouts, and capability blocks; requires confirmation before executing untrusted code).
- get_sandbox_telemetry: **Tier 0** (Queries sandbox execution metrics, capability gates, and blocked security attempt counts; read-only telemetry query).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Every snippet submitted for sandboxed execution undergoes mandatory pre-execution static AST security inspection; code with disallowed imports or escape vectors is categorically halted with SECURITY_VIOLATION prior to execution.
- **Rule 4 (Local Micro-Sandbox & Zero External Sockets)**: All sandboxed code runs locally in-process without network access. Sockets and HTTP libraries (socket, requests, urllib) are disallowed and blocked at both the AST and builtins levels.
- **Rule 7 (Filesystem Non-Destructibility & Isolation)**: Sandboxed code operates under strict filesystem isolation. Open in write mode, os.remove, and shutil operations are blocked by AST security gates and excluded from the SAFE_BUILTINS whitelist.
- **Rule 8 (Payment Prohibitions)**: Both the AST security visitor and the execution jail inspect all identifiers, strings, and function definitions, instantly rejecting any payment, checkout, or billing tokens with Rule8ViolationError.
- **Rule 11 (Credential Protection)**: No environment variables, credential managers, or secret tokens are mapped into sandbox globals.

### 3. Guardian Kill Switch SLA (SAF-02.1)
- The universal Guardian kill switch (emergency_stop()) synchronously terminates active sandboxed code threads and security audits in strictly $< 25.0$ ms.

## 92. Milestone 24.0 — Phase 3: Adaptive Cross-Modal Spatial Cursor-Voice Intent Interactor (VOX-07, GES-01, SAF-01, SAF-02)

### 1. Tool Registry Audit & Classification (SAF-01.1)

All Phase 3 spatial cursor tracking, deictic speech intent resolution, and target highlight tools are registered with services.backend.safety.registry.registry with Pydantic argument schemas and preview generators:

- resolve_spatial_intent: **Tier 0** (Correlates spoken deictic commands with active screen cursor coordinates to resolve target AST symbols or UI controls in < 35ms; read-only intent resolution).
- get_cursor_spatial_context: **Tier 0** (Queries real-time cursor screen coordinates, active window boundaries, and UI element context; read-only telemetry query).
- highlight_spatial_target: **Tier 0** (Broadcasts an on-screen beacon and bounding box highlight for a resolved spatial target; read-only visual overlay beacon).

### 2. Permanent Safety Rule Compliance Invariants (SAF-01.2)
- **Rule 1 (Safety Before Tools)**: Spatial intent resolution resolves target bindings only; any mutating actions derived from resolved intents (e.g. refactoring, file edits) must independently route through confirmation gates before execution.
- **Rule 4 (Local Offline Coordinates & Zero Cloud Telemetry)**: All screen coordinates, window bounds, and spoken directives are processed 100% locally on-device. Zero cursor coordinates or audio transcripts are exfiltrated to cloud services.
- **Rule 7 (Non-Destructibility & Ephemeral Overlays)**: Screen beacons and highlight bounding boxes are purely visual overlays and never alter window geometry, desktop state, or underlying source code.
- **Rule 8 (Payment Prohibitions)**: Spoken commands and resolved symbols containing payment, checkout, or billing tokens are strictly rejected with Rule8ViolationError.
- **Rule 11 (Credential Protection)**: No passwords or credential fields can be bound as targets via spatial cursor resolution.

### 3. Guardian Kill Switch SLA (SAF-02.1)
- The universal Guardian kill switch (emergency_stop()) synchronously halts spatial telemetry tracking and intent resolution in strictly $< 25.0$ ms.
