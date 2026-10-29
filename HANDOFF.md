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
- **Result**: **162 passed, 28 warnings in 160.82s** (0 failed, 0 errors).
- **Environment**: Python 3.11.9 (64-bit AMD64) on Windows 11.

### Secret Scanner Run
- **Command**: `python scripts/scan_secrets.py --all`
- **Result**: **163 tracked files scanned. 0 secrets or blocked files found.**

### Import Coverage Audit
- **Audit Command**: `python services/backend/scripts/audit_imports.py`
- **Result**: **33 third-party imports audited; 0 missing dependencies**. All imports declared in `requirements.txt`, `requirements-windows.txt`, and `requirements-dev.txt`.

### Desktop UI Build
- **Build Command**: `cd apps/desktop; npm run build`
- **Result**: **Clean TypeScript compilation (`tsc`) and Vite production bundle generated in 15.70s with 0 errors**.

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
