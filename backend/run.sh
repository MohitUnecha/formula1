#!/bin/bash
# F1 Analytics Backend — Local Startup
# Usage: ./run.sh  (or: bash run.sh)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../.venv" ]; then
    source ../.venv/bin/activate
fi

# Install deps if needed
pip install -q -r requirements.txt 2>/dev/null

# Check .env
if [ ! -f ".env" ]; then
    echo "⚠  No .env file found. Copy .env.example and fill in your keys."
    exit 1
fi

echo "🏎  Starting F1 Analytics API on http://0.0.0.0:8000"
echo "📖  Docs at http://localhost:8000/docs"

exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
