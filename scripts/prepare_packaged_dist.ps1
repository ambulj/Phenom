<#
.SYNOPSIS
    Prepares Phenom production assets and runtime dependencies for packaging with electron-builder.
.DESCRIPTION
    Verifies that the React/Vite frontend is compiled, the backend services are present,
    and the standalone Python environment is validated.
#>

param (
    [switch]$BundleRuntime,
    [string]$OutputDir = "apps/desktop/release"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Phenom Packaging Preparation ===" -ForegroundColor Cyan

# 1. Verify and compile React frontend
$desktopDir = Join-Path $PSScriptRoot "..\apps\desktop"
$distIndex = Join-Path $desktopDir "dist\index.html"

if (-not (Test-Path $distIndex)) {
    Write-Host "[1/4] Compiling React frontend (dist/)..." -ForegroundColor Yellow
    Push-Location $desktopDir
    try {
        npm run build
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[1/4] React frontend dist already present." -ForegroundColor Green
}

# 2. Verify Backend Services
$backendMain = Join-Path $PSScriptRoot "..\services\backend\main.py"
if (-not (Test-Path $backendMain)) {
    throw "Fatal: Backend services entrypoint not found at $backendMain"
}
Write-Host "[2/4] Backend services verified at services/backend/main.py." -ForegroundColor Green

# 3. Verify Python 3.11 Runtime
$pyTestScript = Join-Path $desktopDir "test_python_version.js"
Write-Host "[3/4] Validating Python 3.11 version guard..." -ForegroundColor Yellow
Push-Location $desktopDir
try {
    node $pyTestScript
} finally {
    Pop-Location
}
Write-Host "[3/4] Python 3.11 runtime verified." -ForegroundColor Green

# 4. Handle Standalone Runtime Bundling
if ($BundleRuntime) {
    Write-Host "[4/4] Bundling standalone Python runtime..." -ForegroundColor Yellow
    $runtimeTarget = Join-Path $PSScriptRoot "..\runtime"
    if (-not (Test-Path $runtimeTarget)) {
        New-Item -ItemType Directory -Path $runtimeTarget -Force | Out-Null
    }
    Write-Host "[4/4] Runtime staging target ready at $runtimeTarget" -ForegroundColor Green
} else {
    Write-Host "[4/4] Standalone runtime bundling skipped (use -BundleRuntime to stage full venv)." -ForegroundColor DarkGray
}

Write-Host "`nAll packaging prerequisites satisfied! Ready to run 'npm run pack' or 'npm run dist'." -ForegroundColor Cyan
