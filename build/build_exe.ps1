# Build the standalone Windows executable for Trimble Converter.
#
# Produces dist\Trimble Converter.exe -- a single file with Python, the
# converter, the dashboard, and all fonts bundled. No Python install needed.
#
# Usage (from the repo root):
#   pip install pyinstaller
#   powershell -ExecutionPolicy Bypass -File build\build_exe.ps1

$ErrorActionPreference = "Stop"

# Always build from the repo root (parent of this script's folder).
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Building Trimble Converter.exe ..." -ForegroundColor Cyan

# --onefile      : one self-contained .exe
# --windowed     : no console window (clean double-click; the app is a GUI)
# --add-data     : bundle the brand fonts and the web dashboard so the frozen
#                  exe finds them (matches brand._fonts_dir and gui._web_index)
# --collect-all  : pull in pywebview + its .NET (pythonnet/clr_loader) backend
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name "Trimble Converter" `
    --add-data "ductsort\fonts;ductsort\fonts" `
    --add-data "ductsort\web;ductsort\web" `
    --collect-submodules reportlab `
    --collect-all webview `
    --collect-all clr_loader `
    --hidden-import clr `
    run.py

Write-Host ""
Write-Host "Done. Executable is at: $root\dist\Trimble Converter.exe" -ForegroundColor Green
Write-Host "Ship that single .exe (or attach it to a GitHub Release)." -ForegroundColor Green
