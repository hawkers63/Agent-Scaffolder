@echo off
setlocal
cd /d "%~dp0"
set "PATH=C:\nvm4w\nodejs;%PATH%"
rem Cheaper model while iterating during development (see README "Model and data
rem handling"). Delete this line, or set AGENT_SCAFFOLDER_MODEL yourself before
rem launching, to go back to the claude-sonnet-5 default.
set "AGENT_SCAFFOLDER_MODEL=claude-haiku-4-5"
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
