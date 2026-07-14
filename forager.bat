@echo off
REM Forager launcher per Windows
REM Uso: forager.bat [start|init|doctor|backup|update]

setlocal
cd /d "%~dp0"
if not exist .venv (
  echo Setup iniziale...
  python -m venv .venv
  .venv\Scripts\pip install -q --upgrade pip
  .venv\Scripts\pip install -q -r requirements.txt
)
.venv\Scripts\python forager %*
