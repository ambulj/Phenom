# Phenom: Personal Windows 11 Desktop Assistant

> [!WARNING]
> **Experimental Software**: Phenom controls your PC, mouse, keyboard, and filesystem. Review the [Safety Model](SAFETY.md) and configure allowed folders before running.

Phenom is a private, local-first personal AI assistant built for Windows 11. It pairs an Electron + React desktop frontend with a high-performance Python FastAPI backend over an authenticated local WebSocket.

---

## 1. Architecture & Safety Model

Phenom is engineered around a defense-in-depth safety layer designed so that the language model never calls an operating system tool directly:

1. **4-Tier Risk Model**:
   - **Tier 0 (Read-Only)**: Allowed automatically, logged in encrypted action log (e.g., read file in allowed paths, inspect screen OCR in RAM, get weather).
   - **Tier 1 (Reversible)**: Requires single confirmation or folder-remembered rule (e.g., create file, save Gmail draft, write note).
   - **Tier 2 (Destructive/External)**: Explicit visual confirmation required with full preview and one-line summary invariant; never remembered (e.g., recycle-bin delete, browser automation, desktop action plan).
   - **Tier 3 (Blocked/System-Level)**: Blocked by default; requires physical typed confirmation on desktop; permanently forbidden from remote approval (e.g., photo deletion/modification, payments, checkout completion, OTP entry, financial trading, changing system settings).
2. **Guardian Kill Switch**:
   - Global hardware hotkey (`Ctrl+Alt+Pause`) and desktop UI button that asynchronously and synchronously terminates model streaming, child process trees, and OS automation immediately.
3. **Untrusted-Content Taint Tracking**:
   - Reading external untrusted content (web pages, emails, PDFs, OCR text) flags the conversation turn chain, forcing explicit user confirmation on all subsequent tool calls to defeat indirect prompt injection.
4. **Privacy Router & PII Redaction**:
   - Local-first inference (Ollama Llama 3.1 8B). Cloud escalation (NVIDIA Nemotron, Groq, OpenRouter) is permitted strictly for non-private content. Private data (files, emails, screen text, Indian PII like Aadhaar/PAN/UPI, credentials) never transits to cloud models without explicit previewed approval.

---

## 2. Honest Limitations

- **Windows 11 Native Integration**: Native automation, Credential Manager access, audio loopbacks, and display affinity capture exclusion require Windows 11.
- **Hardware Requirements**: Private local inference requires an NVIDIA GPU (8 GB VRAM recommended) running Ollama (`llama3.1:8b`). CPU fallback is functional but slower.
- **Coding Agent Execution**: The coding agent executes directly on the host PC. Protections include working inside an isolated project workspace copy (`%USERPROFILE%\Projects\PhenomWorkspaces`), snapshot rollbacks, typosquat package guards, and process tree kill switch termination.
- **Physical Room Acoustics**: Wake-word performance depends on physical room acoustics, microphone hardware, and ambient noise levels.

---

## 3. Prerequisites

- **Operating System**: Windows 11 (64-bit)
- **Python Version**: **Python 3.11 or newer** (tested on Python 3.11.9, x64)
- **Node.js**: Node 20+ with npm
- **GPU**: NVIDIA GPU with CUDA support (8 GB VRAM recommended)
- **Ollama**: Installed and running locally for on-device LLM inference

---

## 4. Installation & Setup

### A. Clone and Virtual Environment
```powershell
git clone https://github.com/ambulj/Phenom.git
cd Phenom

# Create a clean Python 3.11 virtual environment
py -3.11 -m venv .venv
.venv\Scripts\activate
```

### B. Python Backend Dependencies
Install from the locked dependency manifest:
```powershell
pip install -r services/backend/requirements.lock.txt
```
Or install directly for Windows development:
```powershell
pip install -r services/backend/requirements-dev.txt
```

#### PyTorch with NVIDIA CUDA
If you have an NVIDIA GPU, install PyTorch with CUDA acceleration (CUDA 12.4):
```powershell
pip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 --extra-index-url https://download.pytorch.org/whl/cu124
```

### C. Playwright Browser Installation
Initialize the automated browser sandbox for web tasks:
```powershell
playwright install chromium
```

### D. Ollama Models
Pull the primary local model used for private on-device generation:
```powershell
ollama pull llama3.1:8b
```

### E. Desktop UI Dependencies
Install npm packages for root and desktop:
```powershell
npm install
npm --prefix apps/desktop install
```

---

## 5. Configuration & Secrets

Phenom stores credentials and sensitive keys inside **Windows Credential Manager** (`target: Phenom/*`) to prevent tokens and secrets from ever touching code, logs, memory, or Git.

- **First-Run Wizard**: When launching Phenom for the first time, complete the onboarding setup dialog to configure:
  - NVIDIA Cloud API key (build.nvidia.com for Nemotron)
  - Telegram bot token & owner ID (for secure remote bridge)
- **Database Encryption**: The local SQLCipher database key is generated and stored in Windows Credential Manager under `Phenom/db-key`.

---

## 6. Running Phenom

### Development Mode
Runs the FastAPI backend and Vite frontend concurrently with hot-reloading:
```powershell
npm run dev
```

### Running Electron Desktop
```powershell
npm --prefix apps/desktop run dev
npm --prefix apps/desktop run electron:start
```

---

## 7. Verification & Tests

### Audit Imports
Ensure 100% of third-party imports in `services/backend/` are declared in requirements:
```powershell
python services/backend/scripts/audit_imports.py
```

### Run Backend Test Suite
```powershell
pytest -q
```

### End-to-End Smoke Verification
Run the 11-subsystem smoke benchmark suite:
```powershell
python scripts/smoke_test_suite.py
```

---

## 8. Continuous Integration (CI) Coverage

GitHub Actions runs continuous integration workflows across two matrices on every push and pull request:

| Runner | Scope | Covered | Excluded / Not Covered |
| --- | --- | --- | --- |
| **Windows (`windows-latest`)** | Full Windows assistant surface | Import audit, safety tier enforcement, WebSocket authentication, rate limiting, kill switch, Windows automation, scheduler, and Telegram bridge | `needs_gpu` (requires local NVIDIA GPU with CUDA 12.4), `slow` (heavy live model inference benchmarks) |
| **Ubuntu (`ubuntu-latest`)** | Cross-platform core | Core API routes, schemas, protocol serialization, router heuristics, memory encryption roundtrips, and policy audits | `windows_only` (win32 APIs, Credential Manager, uiautomation, mouse hooks), `needs_audio` (PortAudio hardware), `needs_gpu` |

---

## 9. License

This project is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for full details.

Copyright 2026 ambulj.
