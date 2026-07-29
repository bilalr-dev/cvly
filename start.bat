@echo off
echo.
echo   =======================================
echo             Cvly - Job Agent
echo   =======================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python 3 is required. Install it from https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q -r requirements.txt

if not exist ".env" (
    echo.
    echo No .env file found!
    echo Copy .env.example to .env and fill in your API keys.
    pause
    exit /b 1
)

if not exist "output" mkdir output
if not exist "cache" mkdir cache
if not exist "config" mkdir config
if not exist "frontend\static" mkdir frontend\static

echo.
echo Starting Cvly at http://localhost:8000
echo Press Ctrl+C to stop
echo.

start "" http://localhost:8000
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
