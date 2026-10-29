# Phenom Project Roadmap & Task Verification Checklist

In strict adherence to project rules, an item in this checklist is marked complete (`[x]`) **only** when its concrete evidence (command output, test result, or screenshot) is permanently attached or linked. Unverified tasks remain strictly unchecked (`[ ]`).

---

## Hardening Pass 1: Core Reliability & Security (Tasks 1–6)

### [x] Task 1: Authenticate WebSocket & Lock Down HTTP Surface (Fixes F1)
- **Status:** COMPLETE & VERIFIED
- **Commit:** `dd206bf task 1: authenticate websocket and lock down http surface`
- **Key Files:** [preload.cjs](file:///c:/Phenom/apps/desktop/electron/preload.cjs), [main.cjs](file:///c:/Phenom/apps/desktop/electron/main.cjs), [main.py](file:///c:/Phenom/services/backend/main.py), [test_ws_auth.py](file:///c:/Phenom/services/backend/tests/test_ws_auth.py)
- **Evidence Attached:**
  - Fast-failing authentication: WebSocket connection without `Sec-WebSocket-Protocol: phenom.<token>` is closed with code `4401`.
  - Origin allowlist validation: Rejects non-app origins; localhost allowed only when `PHENOM_DEV=1`.
  - REST endpoints protected with Bearer token authentication; `/health` returns minimal `{"status":"ok"}`.
  - Test suite result:
    ```powershell
    python -m pytest services/backend/tests/test_ws_auth.py -v
    # 9 passed in 1.48s
    ```

---

### [x] Task 2: Complete & Reproducible Dependencies (Fixes F2)
- **Status:** COMPLETE & VERIFIED
- **Commit:** `c92cfab task 2: make dependencies complete and reproducible`
- **Key Files:** [audit_imports.py](file:///c:/Phenom/services/backend/scripts/audit_imports.py), [requirements.txt](file:///c:/Phenom/services/backend/requirements.txt), [requirements-windows.txt](file:///c:/Phenom/services/backend/requirements-windows.txt), [requirements-dev.txt](file:///c:/Phenom/services/backend/requirements-dev.txt), [requirements.lock.txt](file:///c:/Phenom/services/backend/requirements.lock.txt)
- **Evidence Attached:**
  - Clean venv verification (`.venv-clean`): `pip check` confirmed zero broken requirements.
  - AST Import Audit:
    ```powershell
    python services/backend/scripts/audit_imports.py
    # Audited 33 third-party imports across C:\Phenom\services\backend...
    # SUCCESS: 0 missing dependencies! All third-party imports are covered by requirements.
    ```

---

### [x] Task 3: Test Infrastructure & Continuous Integration (Fixes F3)
- **Status:** COMPLETE & VERIFIED
- **Commit:** `44ae842 task 3: fix test setup and add ci`
- **Key Files:** [pytest.ini](file:///c:/Phenom/pytest.ini), [conftest.py](file:///c:/Phenom/services/backend/tests/conftest.py), [.github/workflows/ci.yml](file:///c:/Phenom/.github/workflows/ci.yml)
- **Evidence Attached:**
  - Automated skip logic for `windows_only` and PortAudio-dependent tests on non-Windows/CI runners.
  - Dual CI matrix jobs configured for Windows and Ubuntu runners.
  - Local execution proof:
    ```powershell
    python -m pytest services/backend/tests/test_safety.py services/backend/tests/test_router.py
    # 16 passed in 1.12s
    ```

---

### [x] Task 4: Python Version Guard & Installer Prerequisites (Fixes F5)
- **Status:** COMPLETE & VERIFIED
- **Commit:** `200b65e task 4: python version guard and installer prerequisites`
- **Key Files:** [pythonVersion.cjs](file:///c:/Phenom/apps/desktop/electron/pythonVersion.cjs), [main.cjs](file:///c:/Phenom/apps/desktop/electron/main.cjs), [FirstRunWizard.tsx](file:///c:/Phenom/apps/desktop/src/components/FirstRunWizard.tsx)
- **Evidence Attached:**
  - Parse and validation test:
    ```powershell
    node apps/desktop/test_python_version.js
    # [PASS] Parsed Python 3.11.9: { major: 3, minor: 11, patch: 9 }
    # [PASS] Version check >= 3.11: true
    # [PASS] Python 3.10.8 rejected: false
    # [PASS] System Python detected: Python 3.11.9
    ```
  - Uncommitted `__pycache__` check: `git ls-files | findstr pycache` returns 0 tracked files.

---

### [x] Task 5: Rewrite HANDOFF.md Honestly (Fixes F4)
- **Status:** COMPLETE & VERIFIED
- **Commit:** `556ae4c task 5: rewrite handoff.md honestly`
- **Key File:** [HANDOFF.md](file:///c:/Phenom/HANDOFF.md)
- **Evidence Attached:**
  - Removed ungrounded claims ("100% complete", "Known issues: None").
  - Grounded verification matrix documenting exact commit references, test coverage, and active known issues.

---

### [x] Task 6: External Vault, Commit Guard & Dynamic Git Permissions (Fixes F6)
- **Status:** COMPLETE & VERIFIED
- **Commit:** `0726480 task 6: move vault out of repo and add commit guard`
- **Key Files:** [config.toml](file:///c:/Phenom/config.toml), [vault.py](file:///c:/Phenom/services/backend/memory/vault.py), [git_tools.py](file:///c:/Phenom/services/backend/tools/git_tools.py), [scan_secrets.py](file:///c:/Phenom/scripts/scan_secrets.py), [install_hooks.ps1](file:///c:/Phenom/scripts/install_hooks.ps1)
- **Evidence Attached:**
  - Fixed Vault Path Across Directories:
    ```powershell
    # Working dir: C:\Phenom -> Resolved Vault Path: C:\Users\sauja\Documents\Phenom\vault
    # Working dir: C:\Users\sauja -> Resolved Vault Path: C:\Users\sauja\Documents\Phenom\vault
    # Working dir: C:\Users\sauja\AppData\Local\Temp -> Resolved Vault Path: C:\Users\sauja\Documents\Phenom\vault
    # PASS: All 3 working directories resolve to identical vault path: C:\Users\sauja\Documents\Phenom\vault
    ```
  - Code Repo Git Status: Shows 0 files from vault.
  - Secret Scanner & Pre-Commit Hook:
    ```powershell
    # Test staged .env -> Exit Code 1 (Blocked: '*.env')
    # Test staged nvapi- secret -> Exit Code 1 (Blocked: 'NVIDIA API Key')
    # Tracked repo scan: 157 tracked files scanned. 0 secrets found.
    ```
  - Nightly Push Against Throwaway Private Remote: Verified commit and push; code repository remote collision strictly refused.
  - Dynamic Git Permissions: Vault repo operations auto-approved (Tier 0); code repo operations require physical confirmation (Tier 2).
  - Test suite result:
    ```powershell
    python -m pytest services/backend/tests/test_vault_git.py services/backend/tests/test_secret_scan.py
    # 36 passed in 1.45s
    ```

---

### [x] Task 6b: Remove Fabricated Data & Real Gmail / Calendar Integration (Fixes F7, F8)
- **Status:** COMPLETE & VERIFIED
- **Commit:** `163a222 task 6b: remove fabricated data and make gmail and calendar integration real`
- **Key Files:** [finance.py](file:///c:/Phenom/services/backend/integrations/finance.py), [live_data.py](file:///c:/Phenom/services/backend/integrations/live_data.py), [news_briefing.py](file:///c:/Phenom/services/backend/integrations/news_briefing.py), [research.py](file:///c:/Phenom/services/backend/integrations/research.py), [google_workspace.py](file:///c:/Phenom/services/backend/integrations/google_workspace.py), [SettingsPanel.tsx](file:///c:/Phenom/apps/desktop/src/components/panels/SettingsPanel.tsx), [FirstRunWizard.tsx](file:///c:/Phenom/apps/desktop/src/components/FirstRunWizard.tsx), [test_no_fabricated_data.py](file:///c:/Phenom/services/backend/tests/test_no_fabricated_data.py), [test_real_workspace.py](file:///c:/Phenom/services/backend/tests/test_real_workspace.py)
- **Evidence Attached:**
  - Zero fabricated constants in production code: automated grep check proves 0 occurrences of `65000.0`, `185.50`, `142.85`, `"Partly Cloudy"`, `"MF-SCRAPED-001"`, `msg_001`, `event_sample_1`.
  - Offline integrations return typed error records with `ok: False`, `stale: True`, and `None` metrics.
  - Stale and unavailable quotes never trigger watchlist alerts (> 15 min freshness guard).
  - Morning briefing skips unauthenticated Gmail with exact message: `"Email summary skipped: Gmail integration is not connected or authenticated."`
  - Code-level prohibitions enforced: `send_email` raises `EmailSendingProhibitedError` (strictly no SMTP), `delete_calendar_event` and `edit_calendar_event` raise `CalendarModificationProhibitedError`.
  - Real Gmail IMAP over SSL with read-only `EXAMINE` and RFC 5322 draft creation via `IMAP APPEND` to Drafts.
  - Real Google Calendar API integration via REST endpoints.
  - Windows Credential Manager integration for `Phenom/gmail-app-password` and `Phenom/google-calendar-token`.
  - Test suite result:
    ```powershell
    python -m pytest services/backend/tests/test_no_fabricated_data.py services/backend/tests/test_real_workspace.py
    # 12 passed in 23.98s
    ```

---

## Hardening Pass 2: Architecture & Hardening Specifications (Task 7)

### [x] Task 7: Architectural Planning (`PLAN_NEXT.md`)
- **Status:** COMPLETE & VERIFIED
- **Commit:** `e0f48e2 task 7: produce next phase hardening plan`
- **Key Files:** [PLAN_NEXT.md](file:///c:/Phenom/PLAN_NEXT.md), [ARCHITECTURE.md](file:///c:/Phenom/ARCHITECTURE.md)
- **Evidence Attached:**
  - Produced 11-section comprehensive blueprint covering 7a through 7k.
  - Updated [ARCHITECTURE.md](file:///c:/Phenom/ARCHITECTURE.md) Section 3 with new cloud escalation and privacy rules.

---

### [x] Task 7a: Safety Tier 3 Limits, Guardrails & Injection Defense
- **Status:** COMPLETE & VERIFIED
- **Commit:** `task 7a: safety tier 3 limits guardrails and prompt injection defense`
- **Key Files:** [path_guard.py](file:///c:/Phenom/services/backend/safety/path_guard.py), [taint.py](file:///c:/Phenom/services/backend/safety/taint.py), [engine.py](file:///c:/Phenom/services/backend/safety/engine.py), [file_tools.py](file:///c:/Phenom/services/backend/tools/file_tools.py), [cleanup_organizer.py](file:///c:/Phenom/services/backend/memory/cleanup_organizer.py), [test_safety_guardrails.py](file:///c:/Phenom/services/backend/tests/test_safety_guardrails.py)
- **Evidence Attached:**
  - Automated path traversal defense rejects `..`, junction escapes, ADS syntax, and reserved Windows device names.
  - System directories (`C:\Windows`, `C:\Program Files`, `C:\ProgramData`, System root, sensitive `.ssh`/`.aws`/`.azure`) and the Phenom code repository are strictly protected from write and delete operations.
  - Atomic batch size cap: Bulk/destructive operations (`organize_downloads_apply`, `recycle_delete`) enforce a strict 10-item maximum, rejecting larger batches with `BatchLimitExceededError`.
  - Prompt-injection defense: Full 30-string injection attack corpus successfully caught and tagged with taint flag.
  - Taint escalation: Tainted context invalidates remembered folder approvals, escalates Tier 1 to Tier 2 explicit preview, and injects a prominent security warning banner.
  - Test suite result:
    ```powershell
    python -m pytest services/backend/tests/test_safety_guardrails.py
    # 37 passed in 0.46s
    ```

---

### [x] Task 7b: Reliability: Clean-Machine End-to-End Test in a VM and Watchdog Verification
- **Status:** COMPLETE & VERIFIED
- **Commit:** `task 7b: clean machine end to end test and watchdog verification`
- **Key Files:** [main.cjs](file:///c:/Phenom/apps/desktop/electron/main.cjs), [uninstaller.py](file:///c:/Phenom/services/backend/packaging/uninstaller.py), [test_clean_machine_e2e.py](file:///c:/Phenom/services/backend/tests/test_clean_machine_e2e.py), [test_clean_machine.ps1](file:///c:/Phenom/scripts/test_clean_machine.ps1)
- **Evidence Attached:**
  - Watchdog auto-restart: Backend process exit handler in `apps/desktop/electron/main.cjs` relaunches backend using detected Python executable within 1500 ms (< 2000 ms SLA requirement), with max 5 attempts and graceful shutdown guard (`isQuitting`).
  - Auto-update rollback: `AutoUpdateManager` in `services/backend/packaging/updater.py` atomic rollback verified upon simulated boot verification failure (`verify_boot(is_healthy=False)` restores version 1.0.0 from backup and sets state to `rolled_back`).
  - Uninstaller cleanliness: `PhenomUninstaller` in `services/backend/packaging/uninstaller.py` removes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\PhenomAssistant` and `HKCU\Software\Phenom`, proving zero orphaned registry keys (`clean: True`, `run_key_present: False`, `app_key_present: False`).
  - Vault isolation: Clean-machine check verifies vault path is safely outside the code repository root.
  - Complete 10-step automated verification suite:
    ```powershell
    powershell -ExecutionPolicy Bypass -File scripts/test_clean_machine.ps1
    # [Step 1/10] Checking Python Version... PASS (Python 3.11.9)
    # [Step 2/10] Auditing dependencies and import coverage... PASS (33 third-party imports audited; 0 missing dependencies)
    # [Step 3/10] Scanning repository for secrets... PASS (166 tracked files scanned; 0 secrets or blocked files found)
    # [Step 4/10] Running full pytest suite... PASS (162 passed in 160.82s)
    # [Step 5/10] Building desktop frontend... PASS (Vite built in 7.61s)
    # [Step 6/10] Verifying Watchdog Auto-Restart Logic... PASS (Watchdog relaunched under 2000ms guarantee)
    # [Step 7/10] Verifying Auto-Update Staging and Rollback... PASS (Rollback restored previous version on boot failure)
    # [Step 8/10] Verifying Vault Path Isolation... PASS (Vault isolated outside code repository)
    # [Step 9/10] Verifying Uninstaller Cleanliness... PASS (Registry clean; zero orphaned keys)
    # [Step 10/10] All 10 verification steps complete! CLEAN-MACHINE E2E TEST: ALL CHECKS PASSED (10/10)
    ```

---

### [ ] Task 7c: Voice: Hindi/Hinglish Accuracy & Speaker Verification
- **Status:** PLANNED (Awaiting Implementation Approval)
- **Required Evidence:**
  - Benchmark report of faster-whisper model sizes on Intel Core i5 showing latency vs. WER.
  - Speaker verification evaluation report on 50 owner utterances showing FAR $< 1.5\%$ and FRR $< 3.5\%$.
  - Single-button voice data wipe test demonstrating zero byte residue on disk.

---

### [ ] Task 7d: Performance on 6 to 8 GB VRAM & Adaptive Loading
- **Status:** PLANNED (Awaiting Implementation Approval)
- **Required Evidence:**
  - Profiling log: Time to First Token $< 2$ s, idle RAM $< 1$ GB.
  - Adaptive unloading verification: VRAM drops below 100 MB when game executable launches.
  - Stress test report demonstrating automated FIFO snapshot pruning when storage exceeds 45 GB.

---

### [ ] Task 7e: Screen Control Safety UX
- **Status:** PLANNED (Awaiting Implementation Approval)
- **Required Evidence:**
  - Visual screenshot of 4px colored overlay border during mouse/keyboard automation.
  - Automated test demonstrating instant automation pause ($< 15$ ms) upon user mouse movement.
  - Audio playback verification for start, stop, and halt chimes.

---

### [ ] Task 7f: Router & Privacy Classifier with Multi-Provider Fallback
- **Status:** PLANNED (Awaiting Implementation Approval)
- **Required Evidence:**
  - Evaluation report on 100-prompt multilingual benchmark showing $100\%$ precision on known-private data (zero false negatives).
  - Rate-limit cascade test demonstrating seamless failover from NVIDIA Nemotron to secondary free tiers and local 8B.

---

### [ ] Task 7g: Telegram Workflow & Remote PIN Security
- **Status:** PLANNED (Awaiting Implementation Approval)
- **Required Evidence:**
  - Screenshot obfuscation proof showing 35px blur applied over sensitive desktop windows.
  - PIN lifecycle verification: Lockout after 3 failed tries; message auto-deletion via Telegram API within 15 seconds.
  - Local audio transcription and TTS voice message replies verified.

---

### [ ] Task 7h: Orb, Panel & Conversational Voice UX
- **Status:** PLANNED (Awaiting Implementation Approval)
- **Required Evidence:**
  - Three.js particle LOD test showing particle reduction from 15,000 (60 fps) to freeze state under GPU load.
  - Spoken "Good Morning" briefing execution transcript under 60 seconds with full text committed to vault daily log.
  - Proof that voice commands cannot alter security tiers or protected rules.

---

### [ ] Task 7i: Coding Agent Safety & Typosquat Protection
- **Status:** PLANNED (Awaiting Implementation Approval)
- **Required Evidence:**
  - Workspace isolation proof showing original project directory unmodified during execution.
  - Typosquatting detection test flagging 20/20 suspicious package names.
  - Guardian kill switch test terminating active coding runner and all child processes.

---

### [ ] Task 7j: Gaming Mode & Notification Digest
- **Status:** PLANNED (Awaiting Implementation Approval)
- **Required Evidence:**
  - Detection log triggering gaming mode on game executables and full-screen DirectX/Vulkan apps.
  - Exclusions verified for browsers, video players, presentations, and remote desktop.
  - "What did I miss" digest audio proof summarizing missed alerts with zero OTP or private message leaks.

---

### [ ] Task 7k: Providers, Usage Panel, Onboarding, Reset & Uninstall
- **Status:** PLANNED (Awaiting Implementation Approval)
- **Required Evidence:**
  - Usage panel displaying daily/monthly call counts and load history from encrypted SQLite database.
  - Zero-drift self-help test generating tool capabilities directly from `registry.list_all()`.
  - Four granular reset tests (Settings, Memory, Voice, Factory) with verification of erased artifacts.
  - Secret scanner verification on export ZIP archive demonstrating zero credential leakage.

---

### [ ] Task 7l: Confirmations, Meeting Mode, Self-Check & Safe Mode
- **Status:** PLANNED (Awaiting Implementation Approval)
- **Required Evidence:**
  - One-line confirmation formatting invariant test proving exact target and quantity for all Tier 2/3 requests.
  - Preconditions re-validation test: proving modified files, changed mode, or engaged kill switch halts late approvals.
  - Safe alternative engine test: proving declined tools are never repeated and untrusted suggestions are rejected.
  - Meeting mode display-affinity test: proving `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` excludes Phenom windows from capture.
  - Daily self-check execution test: proving Telegram status omits paths/keys and critical alerts speak aloud.
  - Automated 7-day rollback test on simulated post-update boot check failure.
  - Safe mode test: proving `--safe-mode` locks execution to Tier 0 read-only tools and disables all cloud endpoints.
