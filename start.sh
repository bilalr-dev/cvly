#!/usr/bin/env bash
set -e

echo ""
echo "  ======================================="
echo "            Cvly - Job Agent             "
echo "  ======================================="
echo ""

# Cvly needs Python 3.10-3.12 - newer versions may not have prebuilt wheels
# yet for some dependencies (e.g. pydantic-core), which forces a source
# build that fails without a full Rust/C toolchain.
supported_version() {
    case "$1" in
        3.10|3.11|3.12) return 0 ;;
        *) return 1 ;;
    esac
}

PYBIN=""
for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" &> /dev/null; then
        ver=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if supported_version "$ver"; then
            PYBIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYBIN" ]; then
    echo "No compatible Python (3.10-3.12) found. Attempting to install Python 3.12..."
    if command -v brew &> /dev/null; then
        brew install python@3.12
        PYBIN="$(brew --prefix python@3.12)/bin/python3.12"
    elif command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3.12 python3.12-venv
        PYBIN="python3.12"
    else
        echo "Could not find a package manager to auto-install Python."
        echo "Please install Python 3.10-3.12 manually from https://www.python.org/downloads/"
        exit 1
    fi
fi

echo "Using $PYBIN ($("$PYBIN" --version))"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    "$PYBIN" -m venv .venv
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

(sleep 2 && "$PYBIN" -m webbrowser "http://localhost:8000") &

echo ""
echo "Starting Cvly at http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
