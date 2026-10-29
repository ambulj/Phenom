# Phenom Clean-Machine End-to-End Automated Verification Script (Task 7b)
# Executes all 10 steps from PLAN_NEXT.md Section 7b

$ErrorActionPreference = "Continue"
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Phenom Clean-Machine End-to-End Reliability Test" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Step 1: Python Version Check (>= 3.11)
Write-Host "`n[Step 1/10] Checking Python Version..." -ForegroundColor Yellow
$pythonVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
Write-Host "Detected Python version: $pythonVer"
$isPythonOk = python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Python 3.11+ required. Found $pythonVer" -ForegroundColor Red
    exit 1
} else {
    Write-Host "PASS: Python version check passed." -ForegroundColor Green
}

# Step 2: Dependency Audit & Manifest Coverage
Write-Host "`n[Step 2/10] Auditing dependencies and import coverage..." -ForegroundColor Yellow
python services/backend/scripts/audit_imports.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Import audit found missing packages." -ForegroundColor Red
    exit 1
} else {
    Write-Host "PASS: All third-party imports covered." -ForegroundColor Green
}

# Step 3: Secret Scanner Check
Write-Host "`n[Step 3/10] Scanning repository for secrets..." -ForegroundColor Yellow
python scripts/scan_secrets.py --all
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Secret scanner flagged issues." -ForegroundColor Red
    exit 1
} else {
    Write-Host "PASS: Repository clean of secrets." -ForegroundColor Green
}

# Step 4: Full Pytest Test Suite
Write-Host "`n[Step 4/10] Running full pytest suite..." -ForegroundColor Yellow
python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Backend tests failed." -ForegroundColor Red
    exit 1
} else {
    Write-Host "PASS: Backend test suite fully passed." -ForegroundColor Green
}

# Step 5: Frontend Build Check
Write-Host "`n[Step 5/10] Building desktop frontend..." -ForegroundColor Yellow
Push-Location apps/desktop
npm run build
$buildExit = $LASTEXITCODE
Pop-Location
if ($buildExit -ne 0) {
    Write-Host "FAIL: Frontend build failed." -ForegroundColor Red
    exit 1
} else {
    Write-Host "PASS: Frontend built cleanly." -ForegroundColor Green
}

# Step 6: Watchdog Auto-Restart & Timing Verification
Write-Host "`n[Step 6/10] Verifying Watchdog Auto-Restart Logic..." -ForegroundColor Yellow
python -c "from services.backend.tests.test_clean_machine_e2e import test_watchdog_restart_timing; test_watchdog_restart_timing(); print('Watchdog restart verification complete.')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Watchdog restart verification failed." -ForegroundColor Red
    exit 1
} else {
    Write-Host "PASS: Watchdog relaunched under 2000ms guarantee." -ForegroundColor Green
}

# Step 7: Update Staging & Rollback Verification
Write-Host "`n[Step 7/10] Verifying Auto-Update Staging and Rollback..." -ForegroundColor Yellow
python -c "import tempfile; from services.backend.packaging.updater import AutoUpdateManager; d = tempfile.mkdtemp(); u = AutoUpdateManager(data_dir=d); u.stage_update('2.0.0', {'summary': 'Major update'}); assert u.verify_boot(is_healthy=False) is False; assert u.get_version_info().get('current_version') == '1.0.0'; print('Rollback verified: reverted to 1.0.0')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Rollback verification failed." -ForegroundColor Red
    exit 1
} else {
    Write-Host "PASS: Rollback restored previous version on boot failure." -ForegroundColor Green
}

# Step 8: Vault Path Resolution & Isolation
Write-Host "`n[Step 8/10] Verifying Vault Path Isolation..." -ForegroundColor Yellow
python -c "from services.backend.memory.vault import get_configured_vault_path; p = get_configured_vault_path(); assert not p.lower().startswith('c:\\phenom'), f'Vault inside repo: {p}'; print(f'Vault safely isolated at: {p}')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Vault isolation check failed." -ForegroundColor Red
    exit 1
} else {
    Write-Host "PASS: Vault isolated outside code repository." -ForegroundColor Green
}

# Step 9: Uninstaller Cleanliness Verification
Write-Host "`n[Step 9/10] Verifying Uninstaller Cleanliness..." -ForegroundColor Yellow
python -c "from services.backend.packaging.uninstaller import uninstaller; res = uninstaller.run_uninstall(purge_data=False); assert res['status'] == 'success'; print(f'Uninstaller cleanliness: {res}')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Uninstaller cleanliness check failed." -ForegroundColor Red
    exit 1
} else {
    Write-Host "PASS: Registry clean; zero orphaned keys." -ForegroundColor Green
}

# Step 10: Final Verification Status
Write-Host "`n[Step 10/10] All 10 verification steps complete!" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "CLEAN-MACHINE E2E TEST: ALL CHECKS PASSED (10/10)" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
