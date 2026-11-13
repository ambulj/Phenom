@echo off
TITLE Phenom Sovereign OS (Windows 11)
echo =====================================================================
echo  PHENOM SOVEREIGN OS — Windows 11 Enterprise Architecture
echo =====================================================================

:: Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python 3.11 is required but not found in PATH.
    pause
    exit /b 1
)

:: Activate Virtual Environment if present
if exist ".venv-clean\Scripts\activate.bat" (
    echo [*] Activating Python virtual environment (.venv-clean)...
    call .venv-clean\Scripts\activate.bat
)

:: Set Default Environment Variables
set PHENOM_DEV=1
if not defined PHENOM_MASTER_KEY set PHENOM_MASTER_KEY=phenom_sovereign_omni_key_v40

echo [*] Starting Phenom FastAPI Sovereign Backend on port 8000...
start "Phenom Backend" /B python -m uvicorn services.backend.main:app --host 127.0.0.1 --port 8000

echo [*] Launching Desktop Cyber Command Center HUD...
cd apps\desktop
call npm run electron:start

echo [*] Phenom Session Concluded.
