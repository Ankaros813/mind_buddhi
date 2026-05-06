@echo off
cd /d "%~dp0"

where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  start "" pythonw "%~dp0tts_switch.py"
  exit /b 0
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  start "" python "%~dp0tts_switch.py"
  exit /b 0
)

echo Python was not found. Install Python or run tts_switch.py with an existing Python interpreter.
pause
