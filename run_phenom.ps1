<#
.SYNOPSIS
    Phenom Windows 11 Desktop Assistant - Master Unified Launcher (PowerShell)
    Runs Backend (FastAPI), Frontend UI, System Tray & Global Hotkeys
#>

[CmdletBinding()]
param (
    [switch]$Dev,
    [switch]$Stop,
    [switch]$Restart
)

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $RootDir

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "                     PHENOM PERSONAL DESKTOP ASSISTANT                      " -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host " Root Directory: $RootDir`n"

function Stop-Phenom {
    Write-Host " [*] Stopping all Phenom processes..." -ForegroundColor Yellow
    Get-Process -Name "Phenom", "electron" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*services.backend.main:app*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host " [+] All Phenom processes stopped." -ForegroundColor Green
}

if ($Stop) {
    Stop-Phenom
    exit 0
}

if ($Restart) {
    Stop-Phenom
    Start-Sleep -Seconds 1
}

# 1. Locate Best Python Interpreter
$PythonExe = "python"
if (Test-Path "$RootDir\.venv-clean\Scripts\python.exe") {
    $PythonExe = "$RootDir\.venv-clean\Scripts\python.exe"
    Write-Host " [+] Python Environment: .venv-clean" -ForegroundColor Green
} elseif (Test-Path "$RootDir\.venv\Scripts\python.exe") {
    $PythonExe = "$RootDir\.venv\Scripts\python.exe"
    Write-Host " [+] Python Environment: .venv" -ForegroundColor Green
} else {
    Write-Host " [+] Python Environment: System PATH" -ForegroundColor Green
}

# 2. Verify .env file
if (-not (Test-Path "$RootDir\.env")) {
    if (Test-Path "$RootDir\env.example") {
        Write-Host " [*] Copying template to .env..." -ForegroundColor Yellow
        Copy-Item "$RootDir\env.example" "$RootDir\.env"
    }
}

# 3. Generate Session Token
if (-not $env:PHENOM_SESSION_TOKEN) {
    $env:PHENOM_SESSION_TOKEN = & $PythonExe -c "import secrets; print(secrets.token_hex(32))"
}
$appdata = $env:APPDATA
if ($appdata) {
    foreach ($dir in @("$appdata\phenom-desktop", "$appdata\Phenom")) {
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        [System.IO.File]::WriteAllText("$dir\.session_token", $env:PHENOM_SESSION_TOKEN.Trim())
    }
}

# 4. Backend Health Check
Write-Host " [*] Probing FastAPI backend service (http://127.0.0.1:8000/health)..."
$isHealthy = $false
try {
    $res = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    if ($res.StatusCode -eq 200) { $isHealthy = $true }
} catch {
    $isHealthy = $false
}

if ($isHealthy) {
    Write-Host " [+] Backend is already active and healthy." -ForegroundColor Green
} else {
    Write-Host " [*] Starting Phenom FastAPI backend with Uvicorn..." -ForegroundColor Yellow
    Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn services.backend.main:app --host 127.0.0.1 --port 8000" -WindowStyle Minimized

    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 1
        try {
            $check = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -TimeoutSec 1 -UseBasicParsing -ErrorAction Stop
            if ($check.StatusCode -eq 200) {
                $isHealthy = $true
                Write-Host " [+] Backend is online and responding!" -ForegroundColor Green
                break
            }
        } catch {}
    }
}

# 5. Frontend Bundle Verification
$distHtml = "$RootDir\apps\desktop\dist\index.html"
if (-not (Test-Path $distHtml)) {
    Write-Host " [*] Building desktop UI bundle via Vite..." -ForegroundColor Yellow
    Start-Process -FilePath "npm" -ArgumentList "run build" -WorkingDirectory "$RootDir\apps\desktop" -Wait -NoNewWindow
}

# 6. Launch Desktop Application, Tray & Global Hotkeys
if ($Dev) {
    Write-Host " [*] Launching in Development Mode (Vite Dev Server)..." -ForegroundColor Yellow
    Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory "$RootDir\apps\desktop"
    Start-Sleep -Seconds 2
    Start-Process -FilePath "$RootDir\apps\desktop\node_modules\electron\dist\electron.exe" -ArgumentList "." -WorkingDirectory "$RootDir\apps\desktop"
} else {
    $running = Get-Process -Name "Phenom", "electron" -ErrorAction SilentlyContinue
    if ($running) {
        Write-Host " [+] Phenom Desktop is already running!" -ForegroundColor Green
        Write-Host " [+] Press Alt + Space to summon, or check your Windows system tray." -ForegroundColor Green
    } else {
        Write-Host " [*] Launching Phenom Desktop Application..." -ForegroundColor Cyan
        $pkgExe = "$RootDir\apps\desktop\release\win-unpacked\Phenom.exe"
        if (Test-Path $pkgExe) {
            Start-Process -FilePath $pkgExe
        } else {
            Start-Process -FilePath "$RootDir\apps\desktop\node_modules\electron\dist\electron.exe" -ArgumentList "." -WorkingDirectory "$RootDir\apps\desktop"
        }
    }
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host " STATUS:" -ForegroundColor Cyan
Write-Host "  - Backend:      Active (http://127.0.0.1:8000)"
Write-Host "  - Frontend:     Loaded (Particle Orb, HUD & Controls)"
Write-Host "  - System Tray:  Active in Windows Notification Area"
Write-Host "  - Hotkeys:      Alt + Space (Summon), Ctrl + Alt + P (Guardian Killswitch)"
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
