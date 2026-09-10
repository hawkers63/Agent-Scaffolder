@echo off
setlocal
cd /d "%~dp0"
set "PATH=C:\nvm4w\nodejs;%PATH%"
where py >nul 2>&1
if errorlevel 1 (
  python "%~dp0agent_scaffolder.py"
) else (
  py -3.11 "%~dp0agent_scaffolder.py"
)
if errorlevel 1 (
  echo.
  echo Agent Scaffolder exited with an error. Check Python 3.11 and dependencies.
  pause
)
endlocal
