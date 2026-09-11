# Builds a standalone Agent Scaffolder.exe with PyInstaller.
#
# This does NOT bundle Node.js or Repomix — the exe still expects both
# installed separately (see README "Prerequisites" / the in-app error
# guidance added in 1.12 if they're missing). See ROADMAP.md
# "Distributable build" for why: bundling a full Node runtime was
# considered and deliberately deferred as a bigger, separate decision.
#
# Build-time only: pip install -r requirements-build.txt first. This is
# NOT required to just run the app from source (requirements-scaffolder.txt
# covers that).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

pyinstaller agent_scaffolder.py `
    --name "Agent Scaffolder" `
    --onefile `
    --windowed `
    --icon "icon\Agent.Scaffolder.ico" `
    --add-data "icon\Agent.Scaffolder.ico;icon" `
    --collect-all keyring `
    --hidden-import keyring.backends.Windows `
    --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed (exit $LASTEXITCODE)."
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Built: dist\Agent Scaffolder.exe"
Write-Host "projects.json / last_project.json / model_choice.json will be created next to wherever this exe is placed."
