#!/usr/bin/env bash
# =====================================================================
#  PHENOM SOVEREIGN OS — Native Kali Linux Dual-Boot Launcher
# =====================================================================

set -e

echo "====================================================================="
echo " PHENOM SOVEREIGN OS — Native Kali Linux Architecture"
echo "====================================================================="

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 is required. Please run: sudo apt install python3 python3-pip"
    exit 1
fi

# Check Node & npm
if ! command -v npm &> /dev/null; then
    echo "[!] Node.js & npm are required for CyberHUD. Please run: sudo apt install nodejs npm"
    exit 1
fi

# Detect Virtual Environment
if [ -d ".venv" ]; then
    echo "[*] Activating local virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -d ".venv-clean" ]; then
    echo "[*] Activating local virtual environment (.venv-clean)..."
    source .venv-clean/bin/activate
fi

# Set Environment Variables
export PHENOM_DEV=1
export PHENOM_PLATFORM="linux_kali"
if [ -z "$PHENOM_MASTER_KEY" ]; then
    export PHENOM_MASTER_KEY="phenom_sovereign_omni_key_v40"
fi

echo "[*] Starting Phenom Sovereign Backend (port 8000)..."
python3 -m uvicorn services.backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cleanup() {
    echo ""
    echo "[*] Shutting down Phenom processes..."
    kill -TERM "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
    echo "[+] Phenom Session Cleanly Terminated."
}
trap cleanup EXIT INT TERM

echo "[*] Launching Desktop Cyber Command Center HUD..."
cd apps/desktop
npm run electron:start || npm run dev
