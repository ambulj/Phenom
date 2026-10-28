# Phenom: Personal Windows 11 Desktop Assistant

Phenom is a private, local-first personal AI assistant built for Windows 11. It pairs an Electron + React desktop frontend with a high-performance Python FastAPI backend over an authenticated local WebSocket.

---

## 1. Prerequisites

- **Operating System**: Windows 11 (64-bit)
- **Python Version**: **Python 3.11 or newer** (tested on Python 3.11.9, x64)
- **Node.js**: Node 20+ with npm
- **GPU**: NVIDIA GPU with CUDA support (8 GB VRAM recommended)
- **Ollama**: Installed and running locally for on-device LLM inference

---

## 2. Installation & Setup

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

## 3. Configuration & Secrets

Phenom stores credentials and sensitive keys inside **Windows Credential Manager** (`target: Phenom/*`) to prevent tokens and secrets from ever touching code, logs, memory, or Git.

- **First-Run Wizard**: When launching Phenom for the first time, complete the onboarding setup dialog to configure:
  - NVIDIA Cloud API key (build.nvidia.com for Nemotron)
  - Telegram bot token & owner ID (for secure remote bridge)
- **Database Encryption**: The local SQLCipher database key is generated and stored in Windows Credential Manager under `Phenom/db-key`.

---

## 4. Running Phenom

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

## 5. Verification & Tests

### Audit Imports
Ensure 100% of third-party imports in `services/backend/` are declared in requirements:
```powershell
python services/backend/scripts/audit_imports.py
```

### Run Backend Test Suite
```powershell
pytest -q
```

---

## 6. Continuous Integration (CI) Coverage

GitHub Actions runs continuous integration workflows across two matrices on every push and pull request:

| Runner | Scope | Covered | Excluded / Not Covered |
| --- | --- | --- | --- |
| **Windows (`windows-latest`)** | Full Windows assistant surface | Import audit, safety tier enforcement, WebSocket authentication, rate limiting, kill switch, Windows automation, scheduler, and Telegram bridge | `needs_gpu` (requires local NVIDIA GPU with CUDA 12.4), `slow` (heavy live model inference benchmarks) |
| **Ubuntu (`ubuntu-latest`)** | Cross-platform core | Core API routes, schemas, protocol serialization, router heuristics, memory encryption roundtrips, and policy audits | `windows_only` (win32 APIs, Credential Manager, uiautomation, mouse hooks), `needs_audio` (PortAudio hardware), `needs_gpu` |

