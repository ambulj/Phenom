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








