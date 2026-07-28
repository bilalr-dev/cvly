#!/usr/bin/env bash
set -e

echo ""
echo "  ======================================="
echo "            Cvly - Job Agent             "
echo "  ======================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required. Install it from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python $PYTHON_VERSION detected"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
    echo ""
    echo "No .env file found!"
    echo "Copy .env.example to .env and fill in your API keys:"
    echo ""
    echo "cp .env.example .env"
    echo "nano .env"
    echo ""
    exit 1
fi

mkdir -p output cache config frontend/static

(sleep 2 && python3 -m webbrowser "http://localhost:8000") &

echo ""
echo "Starting Cvly at http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
