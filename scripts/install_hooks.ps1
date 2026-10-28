# Phenom Git Pre-Commit Hook Installer
# Installs scripts/scan_secrets.py as a git pre-commit hook in .git/hooks/pre-commit

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$hooksDir = Join-Path $repoRoot ".git\hooks"
$preCommitFile = Join-Path $hooksDir "pre-commit"

if (-not (Test-Path $hooksDir)) {
    Write-Error "Git hooks directory not found at $hooksDir. Is this a git repository?"
    exit 1
}

$hookContent = @"
#!/usr/bin/env sh
# Phenom Pre-Commit Secret Scanner
python scripts/scan_secrets.py --staged
"@

# Write UTF-8 hook without BOM
[System.IO.File]::WriteAllText($preCommitFile, $hookContent.Replace("`r`n", "`n"), [System.Text.UTF8Encoding]::new($false))

Write-Host "Phenom pre-commit hook successfully installed at: $preCommitFile"
Write-Host "Staged commits will now be scanned for secrets, .env files, database files, and vault notes."
