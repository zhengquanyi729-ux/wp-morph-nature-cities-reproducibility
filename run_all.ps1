# WP-MORPH journal reproducibility package - Windows PowerShell launcher.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\run_all.ps1
#
# The script does not hide errors: the exit code of run_all.py is propagated.

$ErrorActionPreference = "Stop"

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $PackageRoot

Write-Host "Package root : $PackageRoot"

# Prefer the conda environment described in environment.yml, when available.
$Conda = Get-Command conda -ErrorAction SilentlyContinue
if ($Conda) {
    $envList = & conda env list 2>$null
    if ($envList -match "wp-morph-repro") {
        Write-Host "Activating conda environment 'wp-morph-repro' ..."
        & conda run -n wp-morph-repro python --version
        & conda run --no-capture-output -n wp-morph-repro python run_all.py
        exit $LASTEXITCODE
    }
}

Write-Host "No conda environment named 'wp-morph-repro' found; using the active interpreter."
python run_all.py
exit $LASTEXITCODE
