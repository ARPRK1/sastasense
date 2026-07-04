#!/usr/bin/env bash
# ---- Deal Aggregator: one-click start for macOS / Linux ----
set -e
cd "$(dirname "$0")/backend"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "Installing dependencies (first run only)..."
pip install -q -r requirements.txt

echo
echo "Starting Deal Aggregator at http://localhost:8000  (Ctrl+C to stop)"
echo
uvicorn app:app --port 8000
