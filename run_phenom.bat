@echo off
title Phenom AI Assistant Launcher

REM ============================================================================
REM Phenom Windows 11 Desktop Assistant - Master Unified Launcher
REM Runs Backend (FastAPI), Frontend UI, System Tray and Global Hotkeys
REM ============================================================================

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo.
echo ============================================================================
echo                      PHENOM PERSONAL DESKTOP ASSISTANT
echo ============================================================================
echo  Root Directory: %ROOT_DIR%
echo.

REM Handle CLI flags: --stop, --restart, --dev
if /i "%~1"=="--stop" goto do_stop
if /i "%~1"=="/stop" goto do_stop
if /i "%~1"=="--restart" goto do_restart
if /i "%~1"=="/restart" goto do_restart

:do_start
REM ----------------------------------------------------------------------------
REM 1. Locate Best Python Interpreter (.venv-clean, .venv, or system)
REM ----------------------------------------------------------------------------
set "PYTHON_EXE="
if exist "%ROOT_DIR%.venv-clean\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%.venv-clean\Scripts\python.exe"
    echo  [+] Python Environment: .venv-clean
) else if exist "%ROOT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%.venv\Scripts\python.exe"
    echo  [+] Python Environment: .venv
) else (
    set "PYTHON_EXE=python"
    echo  [+] Python Environment: System PATH
)

REM ----------------------------------------------------------------------------
REM 2. Verify or Setup Environment Variables (.env)
REM ----------------------------------------------------------------------------
if not exist "%ROOT_DIR%.env" (
    if exist "%ROOT_DIR%env.example" (
        echo  [*] No .env found. Copying template from env.example...
        copy "%ROOT_DIR%env.example" "%ROOT_DIR%.env" >nul
    )
)

REM ----------------------------------------------------------------------------
REM 3. Generate or Preserve Secure Session Token
REM ----------------------------------------------------------------------------
if not defined PHENOM_SESSION_TOKEN (
    for /f "tokens=*" %%T in ('"%PYTHON_EXE%" -c "import secrets; print(secrets.token_hex(32))" 2^>nul') do (
        set "PHENOM_SESSION_TOKEN=%%T"
    )
)
if not exist "%APPDATA%\phenom-desktop" mkdir "%APPDATA%\phenom-desktop" 2>nul
if not exist "%APPDATA%\Phenom" mkdir "%APPDATA%\Phenom" 2>nul
if defined PHENOM_SESSION_TOKEN (
    <nul set /p="%PHENOM_SESSION_TOKEN%" > "%APPDATA%\phenom-desktop\.session_token"
    <nul set /p="%PHENOM_SESSION_TOKEN%" > "%APPDATA%\Phenom\.session_token"
)

REM ----------------------------------------------------------------------------
REM 4. Backend Health Check and Startup
REM ----------------------------------------------------------------------------
echo  [*] Probing FastAPI backend service: http://127.0.0.1:8000/health
curl.exe -s --fail http://127.0.0.1:8000/health >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo  [+] Backend is already active and healthy.
    goto backend_done
)

echo  [*] Starting Phenom FastAPI backend with Uvicorn...
start "Phenom Backend" /min "%PYTHON_EXE%" -m uvicorn services.backend.main:app --host 127.0.0.1 --port 8000

REM Poll up to 15 seconds for backend to become ready
for /l %%i in (1,1,15) do (
    curl.exe -s --fail http://127.0.0.1:8000/health >nul 2>&1
    if not errorlevel 1 (
        echo  [+] Backend is online and responding!
        goto backend_done
    )
    ping 127.0.0.1 -n 2 >nul
)
echo  [WARN] Backend taking longer than expected to report healthy. Continuing launch...

:backend_done
REM ----------------------------------------------------------------------------
REM 5. Frontend Bundle Verification
REM ----------------------------------------------------------------------------
if not exist "%ROOT_DIR%apps\desktop\dist\index.html" (
    echo  [*] Frontend bundle not found. Building desktop UI via Vite...
    call npm --prefix "%ROOT_DIR%apps\desktop" run build
)

REM ----------------------------------------------------------------------------
REM 6. Launch Desktop Application, Tray and Global Hotkeys
REM ----------------------------------------------------------------------------
if /i "%~1"=="--dev" (
    echo  [*] Launching in Development Mode [Vite and Electron]...
    start "Phenom Vite Dev" /d "%ROOT_DIR%apps\desktop" npm run dev
    ping 127.0.0.1 -n 3 >nul
    cd /d "%ROOT_DIR%apps\desktop"
    start "" "node_modules\electron\dist\electron.exe" .
    goto finish
)

REM Check if Phenom GUI process is already running
tasklist /fi "imagename eq Phenom.exe" 2>nul | find /i "Phenom.exe" >nul
if not errorlevel 1 (
    echo  [+] Phenom Desktop is already running!
    echo  [+] Press Alt + Space to summon, or check your Windows system tray.
    goto finish
)

tasklist /fi "imagename eq electron.exe" 2>nul | find /i "electron.exe" >nul
if not errorlevel 1 (
    echo  [+] Phenom Desktop [Electron] is already running!
    echo  [+] Press Alt + Space to summon, or check your Windows system tray.
    goto finish
)

echo  [*] Launching Phenom Desktop Application...
if exist "%ROOT_DIR%apps\desktop\release\win-unpacked\Phenom.exe" (
    start "" /d "%ROOT_DIR%apps\desktop\release\win-unpacked" "%ROOT_DIR%apps\desktop\release\win-unpacked\Phenom.exe"
) else (
    start "" /d "%ROOT_DIR%apps\desktop" "%ROOT_DIR%apps\desktop\node_modules\electron\dist\electron.exe" .
)

:finish
echo.
echo ============================================================================
echo  STATUS:
echo   - Backend:      Active (http://127.0.0.1:8000)
echo   - Frontend:     Loaded (Particle Orb, HUD and Controls)
echo   - System Tray:  Active in Windows Notification Area
echo   - Hotkeys:      Alt + Space (Summon), Ctrl + Alt + P (Guardian Killswitch)
echo ============================================================================
echo.
ping 127.0.0.1 -n 3 >nul
exit /b 0

REM ----------------------------------------------------------------------------
REM Helper Routines: Stop and Restart
REM ----------------------------------------------------------------------------
:do_stop
echo  [*] Stopping all Phenom processes...
taskkill /f /im Phenom.exe 2>nul
taskkill /f /im electron.exe 2>nul
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*services.backend.main:app*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" 2>nul
echo  [+] All Phenom processes stopped.
exit /b 0

:do_restart
call :do_stop
ping 127.0.0.1 -n 2 >nul
goto do_start
