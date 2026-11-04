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
