# HANDOFF.md

**Hardening Pass 1 Status Report**  
- **Branch**: `hardening/pass-1`  
- **Date**: October 29, 2026  
- **Audit Findings Addressed**:
  - F1: WebSocket & REST Authentication (token in subprotocol, Origin validation, rate limiting)
  - F2: Complete Requirements Manifest & lockfile (`requirements.lock.txt`, audit script)
  - F3: Pytest & CI (`pytest.ini`, `conftest.py`, GitHub Actions workflow)
  - F4: Honest Documentation (`HANDOFF.md` rewrite)
  - F5: Python Version Guard (`>= 3.11` check in Electron `main.cjs`)
  - F6: Obsidian Vault isolation outside code repo & pre-commit scan guard
  - F7 & F8: Elimination of fabricated data across all integrations (`finance`, `live_data`, `news_briefing`, `research`), real Gmail IMAP over SSL (read-only `EXAMINE`, draft `IMAP APPEND`, strictly NO SMTP), and real Google Calendar API (reading/creating events, strictly NO edit/delete). Credentials secured in Windows Credential Manager under `Phenom/gmail-app-password` and `Phenom/google-calendar-token`.

---

## 1. Verified Test Results

### Local Windows Test Run
- **Test Command**: `python -m pytest -q`
- **Result**: **250 passed, 48 warnings** (0 failed, 0 errors in 108s).
- **Test Command**: python -m pytest services/backend/tests/

### End-to-End Smoke Verification
- **Command**: python scripts/smoke_test_suite.py
- **Result**: **11/11 Subsystems Verified (PASS)** in 40.06s.
- **Environment**: Python 3.11.9 (64-bit AMD64) on Windows 11.

### Secret Scanner Run
- **Command**: `python scripts/scan_secrets.py --all`
- **Result**: **222 tracked files scanned. 0 secrets or blocked files found.**

### Import Coverage Audit
- **Audit Command**: `python services/backend/scripts/audit_imports.py`
- **Result**: **34 third-party imports audited; 0 missing dependencies**. All imports declared in `requirements.txt`, `requirements-windows.txt`, and `requirements-dev.txt`.

### Desktop UI Build
- **Build Command**: `cd apps/desktop; npm run build`
- **Result**: **Clean TypeScript compilation (`tsc`) and Vite production bundle generated in 24.19s with 0 errors**.

---

## 2. Phase-by-Phase Verification Matrix

| Phase | Scope | What Was Actually Verified | What Was NOT Verified & Reason | Verification Command |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0: Spikes** | Core Link & Encryption | WebSocket typed framing, state transitions (`idle` → `thinking` → `speaking`), token stream cancellation, and SQLCipher encryption. | Live Nemotron API cloud streaming (Nemotron API key not configured in environment). | `pytest services/backend/tests/test_memory.py -q` |
| **Phase 1: Core & Safety** | Safety Engine & Guardian | 4-tier risk classification, tool registration, preview generation, UI confirmation handlers, action logging, and Guardian kill switch trigger/resume. | Physical keyboard interrupt while Python GIL is locked by C extensions (tested via asyncio cancellation and keyboard hook handlers). | `pytest services/backend/tests/test_safety.py services/backend/tests/test_final_safety_audit.py -q` |
| **Phase 2: Voice & Persona** | Voice Pipeline | Sentence-by-sentence TTS streaming, barge-in stop latency (< 50ms), hotkey conflict validation, and hard safety refusal of spoken approvals. | Physical microphone wake-word detection in an ambient noisy room (verified using synthetic in-memory audio buffers). | `pytest services/backend/tests/test_voice.py -q` |
| **Phase 3: Tools & Automation** | OS & Browser Automation | File sandboxing (create, read, copy, list, recycle), app listing, Playwright scripted navigation, dry-run cart filling, blocked checkout/pay actions, and in-RAM screen capture. | Live monetary purchases on real e-commerce sites (permanently blocked by construction under Rule 8). | `pytest services/backend/tests/test_tools.py services/backend/tests/test_automation.py -q` |
| **Phase 4: Memory & RAG** | Encrypted Memory & Vault | SQLCipher schema roundtrips, vector store dense similarity search, Obsidian vault notes sync, photo EXIF read-only indexing, and reversible downloads cleanup. | Full filesystem scan across massive production drives (> 100k files; tested against isolated directory trees). | `pytest services/backend/tests/test_memory_phase4.py -q` |
| **Phase 5: Modes & Integrations** | Assistant Personas & Feeds | Work/Study/Chill mode profiles, scheduler cron persistence in SQLCipher, watchlist stock/crypto quotes, tech news RSS parsing, and multi-format document generation (.docx, .xlsx, .pptx, .pdf). | Live financial trades (permanently prohibited under Rule 5) and live Google Workspace OAuth token exchange. | `pytest services/backend/tests/test_phase5.py -q` |
| **Phase 6: Remote Bridge** | Telegram Remote Access | Telegram client message formatting, strict owner whitelist enforcement, non-owner rejection and security logging, remote inline button approvals, and remote locking. | Live network connection to official Telegram Bot API servers (tested via MockTelegramClient because no real bot token is stored in Credential Manager). | `pytest services/backend/tests/test_phase6.py -q` |
| **Hardening Pass 1** | Security & Reproducibility | WebSocket token authentication via `Sec-WebSocket-Protocol`, Origin validation, rate limiting (5 failures / 60s), REST token protection, clean venv installation from `requirements.lock.txt`, and Python >= 3.11 startup guard. | Electron installer runtime bundle on non-Windows developer machines. | `pytest services/backend/tests/test_ws_auth.py services/backend/tests/test_requirements_cover_imports.py -q` |

---

## 3. Honest List of Known Issues and Limitations

1. **WebSocket Session Token Lifetime**:
   The WebSocket endpoint requires a cryptographic 32-byte session token generated at Electron startup (`PHENOM_SESSION_TOKEN`). If the desktop app crashes or restarts, a new token is generated. Any detached background task running across restarts cannot broadcast back to the frontend until a new authenticated WebSocket handshake is established.
2. **Heavy Dependencies & CUDA Download Size**:
   PyTorch with CUDA 12.4 acceleration (`torch==2.6.0+cu124`) is ~2.5 GB. Fresh installation on low-bandwidth networks requires significant time. For CI and non-GPU environments, lightweight CPU PyTorch wheels are documented and utilized.
3. **OS-Specific Features on Linux/macOS**:
   Windows-specific tests (`windows_only`) rely on `pywin32`, Windows Credential Manager (`win32cred`), `win32com`, `keyboard`, `mouse`, and `uiautomation`. These tests automatically skip when run on Linux or macOS. Cross-platform CI tests only the cross-platform core.
4. **Standalone Python Interpreter Bundling**:
   `electron-builder` packages the desktop UI and backend Python scripts into `extraResources/backend`, but does not bundle a standalone Python executable. The target Windows host must have Python >= 3.11 installed. The startup check in `main.cjs` detects Python and alerts the user if missing.
5. **Local LLM Model Availability**:
   Private on-device text generation relies on Ollama running on `http://127.0.0.1:11434` with `llama3.1:8b` installed. If Ollama is not running, Phenom alerts the user via the First-Run Wizard and chat interface.
6. **Physical Audio Hardware in Headless CI**:
   Tests tagged `needs_audio` require an initialized PortAudio device. Headless CI runners without virtual audio loopbacks automatically skip these tests.

---

## 4. Exact Steps to Reproduce from a Fresh Clone

```powershell
# 1. Clone repository and check out hardening branch
git clone https://github.com/ambulj/Phenom.git
cd Phenom
git checkout hardening/pass-1

# 2. Create clean Python 3.11 virtual environment
py -3.11 -m venv .venv
.venv\Scripts\activate

# 3. Install locked dependencies
pip install -r services/backend/requirements.lock.txt

# 4. Verify dependency coverage (must output 0 missing)
python services/backend/scripts/audit_imports.py

# 5. Run backend test suite (must pass 73 tests)
python -m pytest -q

# 6. Verify Python version guard logic
node apps/desktop/test_python_version.js

# 7. Install and build desktop application
npm install
npm --prefix apps/desktop install
npm --prefix apps/desktop run build

# 8. Start development stack
npm run dev
```


---

## 5. Owner Operational Decisions (Rounds 8-19 Locked In)

### Core Assistant & Daily Routines (Rounds 8-13)
- **Morning Briefing**: On-demand triggered via 'Good morning Phenom' or Telegram greeting.
- **Desktop UI**: Subtle floating particle orb with auto-dock to screen edge; full window & media controls.
- **Coding Sandbox**: Local workspace subprocess with strict path boundary & execution timeouts.
- **Browser Automation**: Open web browsing via Playwright with Tier 2 confirmations for interactive actions.
- **Telegram Remote**: Full remote control (git tasks, test suites, health checks) with urgent system alerts only.
- **Microphone & Wake Word**: Dual-mode (Local wake word 'Hey Phenom' + Push-to-Talk Ctrl+Space).
- **Obsidian Vault**: Structured folders (Daily Notes, Projects, Study/Research, People/Entities); local-only.
- **Local GPU Runtime**: Ollama with Llama-3.1-8B-Instruct (4-bit quantized, ~5.5 GB VRAM).
- **Vision & Screen**: Automatic background screen context during active coding/debugging sessions.
- **Storage & Reports**: Generated documents stored in ~/Documents/Phenom/ with ISO timestamps; transient caches purged after 7 days; action logs retained indefinitely.
- **Personality & Tone**: High banter! Sharp comebacks, treats Abhi like Tony Stark, banter-heavy Romanized Hinglish.
- **Study Mode**: Deep technical dive with exhaustive architectural breakdowns, formal equations, and complete code.
- **Emergency Halt**: Triple-tap Escape for immediate Guardian Kill Switch halt.
- **Offline Mode**: Seamless local offline mode (automatic fallback to local Ollama & offline TTS).

### Advanced Toolchains & Multimodal UX (Rounds 14-19)
- **Email Drafting**: Authentic concise voice matching Abhi's direct writing style (minimal corporate fluff).
- **Calendar Management**: Smart calendar companion with 15-minute buffers between meetings and conflict detection.
- **Screen Sampling**: Event-triggered OCR captures on terminal failure or IDE syntax error highlights.
- **Window Snapping**: Workflow layout presets (e.g. 'Setup coding mode' snaps IDE to 60%, terminal to 40%).
- **Git & GitHub**: Autonomous pre-push quality gate running tests, linter, and secret scanner before PR drafting.
- **Audio Ducking**: Auto-lower media volume by 70% during TTS synthesis or speech input; focus playlist launching.
- **Hardware Governor**: Auto-offload GPU VRAM when 3D game launches; pause background indexing on low battery.
- **Barge-in Interruption**: Ultra-fast speech cutoff within 50ms upon speech recognition or push-to-talk tap.
- **Telegram Media**: Full multi-modal processing (Whisper voice transcription, voice replies, photo/document OCR).
- **Shell Runner**: PowerShell 7 (pwsh.exe) primary subprocess runner with PowerShell 5.1 fallback.
- **Local RAG Embedding**: Local ONNX runtime using ll-MiniLM-L6-v2 (< 5ms on CPU, zero GPU VRAM consumption).
- **Orb & HUD Styling**: Electric Cyan (#00E5FF) and Amber Gold (#FFB300) palette with anchored transparent HUD cards and selectable particle modes (reactive dynamics, minimal halo, wireframe core).
- **Clipboard Intelligence**: Smart developer clipboard auto-detecting stack traces, regex, JSON, and git URLs.
- **GPU Gaming Fallback**: Dynamic fallback to Cloud Nemotron if online, or lightweight CPU Q4 GGUF if offline.
- **Health Reminders**: Subtle 1-sentence spoken voice nudges during focus gaps ('Hydrate, Abhi; coffee is not water').
- **Disaster Recovery**: Automated daily encrypted snapshot archives of SQLite memory, vault, and config with 30-day retention.

- **Morning Briefing**: On-demand triggered via 'Good morning Phenom' or Telegram greeting.
- **Desktop UI**: Subtle floating particle orb with auto-dock to screen edge; full window & media controls.
- **Coding Sandbox**: Local workspace subprocess with strict path boundary & execution timeouts.
- **Browser Automation**: Open web browsing via Playwright with Tier 2 confirmations for interactive actions.
- **Telegram Remote**: Full remote control (git tasks, test suites, health checks) with urgent system alerts only.
- **Microphone & Wake Word**: Dual-mode (Local wake word 'Hey Phenom' + Push-to-Talk Ctrl+Space).
- **Obsidian Vault**: Structured folders (Daily Notes, Projects, Study/Research, People/Entities); local-only.
- **Local GPU Runtime**: Ollama with Llama-3.1-8B-Instruct (4-bit quantized, ~5.5 GB VRAM).
- **Vision & Screen**: Automatic background screen context during active coding/debugging sessions.
- **Storage & Reports**: Generated documents stored in ~/Documents/Phenom/ with ISO timestamps; transient caches purged after 7 days; action logs retained indefinitely.
- **Personality & Tone**: High banter! Sharp comebacks, treats Abhi like Tony Stark, banter-heavy Romanized Hinglish.
- **Study Mode**: Deep technical dive with exhaustive architectural breakdowns, formal equations, and complete code.
- **Emergency Halt**: Triple-tap Escape for immediate Guardian Kill Switch halt.
- **Offline Mode**: Seamless local offline mode (automatic fallback to local Ollama & offline TTS).

### Multi-Agent Coordination, UX & Context (Rounds 20-22)
- **Multi-Agent Coordination**: Specialist subagents (Test Architect, Code Reviewer, Security Auditor, Docs Writer) synthesized by Phenom.
- **Obsidian Graph & Wikilinks**: Deep bidirectional [[Topic]] and [[Project]] wikilinks for interactive Obsidian Graph View.
- **Telegram Commands**: Natural conversation by default, with optional power shortcuts (/status, /test, /git, /halt).
- **Package Manager**: Adaptive auto-detection (uv/pip for Python, pnpm/npm for Node, cargo for Rust).
- **Context Compaction & Escalation**: Dual approach (auto-compact local turns; escalate to Cloud Nemotron 128k context for massive diffs/logs).
- **Terminal Execution UI**: Collapsible live streaming console drawer with syntax highlighting.
- **Voice Linguistic Accent**: Modern Urban Indian / Tech-Savvy developer with natural metro Hinglish idioms ('sorted', 'scene', 'phod diya').
- **Incremental Indexing**: File-watcher incremental vector embedding within 2 seconds of file save.
- **Global Summon UI**: Raycast / Spotlight style centered glassmorphic command palette on Alt+Space.
- **Audit Log Drawer**: Integrated 1-click HUD drawer to inspect chronological action logs, tool tiers, and rollbacks.
- **Test Generation Policy**: Test-driven pairing (automatically authoring matching test suites for every new module).
- **Screen Border Overlay**: Dynamic pulsing Electric Cyan while active, Amber on Tier 2 confirmation, Crimson on Guardian halt.

### Core Safety, Wake Word & Vision Reasoning (Round 23)
- **Wake Word Sensitivity**: Strict 0.65+ confidence threshold with 500ms sliding confirmation window to eliminate false triggers from media/conversations.
- **Memory Decay Policy**: Spaced relevance weighting (frequently referenced profile/rules stay permanent; transient notes decay after 14 days).
- **Screen & Vision Reasoning**: Dual OCR + Vision approach (fast local Windows OCR for exact code/text, paired with multimodal vision model for layout/diagram interpretation).
- **Administrative Privileges**: Strict Windows UAC elevation required for any elevated commands; zero bypass of Windows security gates.

### Phase 4 & Phase 5 Architecture Decisions (Rounds 24-25)
- **Daily Engineering Notes**: Structured template (## 🎯 Focus & Goals, ## 🔨 Code & Commits, ## 🧠 Technical Learnings, ## 📌 Follow-ups).
- **RAG Source Citations**: Exact clickable wikilinks to note headers or lines (e.g. [[Architecture#L42]]).
- **Financial Watchlist Tracking**: ±3% intraday swing threshold alerts + daily 04:00 PM IST market closing summary (Rule 5: informational only, never trade/recommend).
- **Document Generation Styling**: Modern Executive visual branding (clean typography, styled tables, callout blocks, executive summary covers).
- **Photo Indexing**: Read-only EXIF + local AI visual tagging (receipt, diagram, screenshot) stored encrypted in SQLCipher (Rule 6: never edit/move).
- **Reversible Cleanup**: Windows Recycle Bin only (Rule 7) with an automated rollback manifest note created in Obsidian.
- **News Aggregation**: Curated feeds across Hacker News, ArXiv AI, GitHub Trending, and Indian business headlines.
- **Adaptive Modes**: Work (code & high banter), Study (deep technical rigor & ambient focus audio), Chill (relaxed banter & music control).

### Phase 6 & Phase 7 Remote, Packaging & Resilience (Rounds 26-31)
- **Telegram Pairing Handshake**: Desktop QR code / 6-digit PIN handshake (/pair <PIN>).
- **Remote Lock & Emergency Halt**: Windows workstation lock (
undll32.exe user32.dll,LockWorkStation) + Guardian kill switch.
- **Remote Inline Approvals**: Interactive [✅ Approve] / [❌ Deny] buttons with 60s timeout.
- **Remote File Retrieval**: Unrestricted filesystem delivery up to 50MB (excluding system files & secrets).
- **Remote Screen Inspection**: Redacted screenshot with passwords, OTPs, and credit cards auto-blacked out.
- **Telegram Voice Duplex**: Voice note transcription (Whisper) + spoken audio reply (Sarvam/voice engine).
- **Non-Owner Security**: Silent drop stranger message + push alert to Abhi's desktop & Telegram.
- **Packaging Format**: Dual distribution (NSIS installer with startup registration + portable unpacked directory).
- **Auto-Update**: Silent automatic update applied on idle restart with 7-day rollback safeguard.
- **Smart Watchdog**: Auto-restart backend within 3s, sanitize crash dump (zero PII), notify in HUD.
- **Guarded Reset**: Encrypted backup ZIP created before any reset, preserving Obsidian vault notes.
- **System Startup**: Auto-launch on Windows login minimized to tray with floating docked Orb.
- **Telemetry Policy**: Zero external telemetry; crash logs stored strictly local in ~/Documents/Phenom/logs/.
- **Multi-Monitor Display**: Summon Command Palette and HUD on whichever monitor holds the active mouse cursor.
- **Local Plugins**: Support custom Python tools in ~/Documents/Phenom/plugins/ wrapped by Safety layer.
- **Cloud Stall Fallback**: Graceful local downgrade to 8B model if cloud connection stalls > 10s.
- **Refactoring Waves**: Staged dependency wave execution with git checkpoints for large refactors.
- **Prompt Injection Defense**: Sanitize & proceed (strip adversarial instruction patterns and continue).
- **Speaker Verification**: Voiceprint enrollment to filter out ambient background conversations/media.
- **IDE File Conflict**: 3-way diff comparison in HUD when local file changes concurrently.
- **Low Power Profile**: Throttle LLM threads and set Orb to Low LOD when battery < 20%.
- **Wake Word Debounce**: 2-second debounce & 10s cooldown on rapid fluttering triggers.
- **Large Remote Delivery**: Chunked 45MB ZIP delivery for files exceeding 50MB.
