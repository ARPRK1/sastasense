@echo off
REM ---- Deal Aggregator: one-click start for Windows ----
cd /d "%~dp0backend"

if not exist ".venv" (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat

echo Installing dependencies (first run only)...
pip install -q -r requirements.txt

echo.
echo Starting Deal Aggregator at http://localhost:8000
echo Press Ctrl+C to stop.
echo.
start "" http://localhost:8000
uvicorn app:app --port 8000
