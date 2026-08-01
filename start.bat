@echo off
setlocal enabledelayedexpansion
echo.
echo   =======================================
echo             Cvly - Job Agent
echo   =======================================
echo.

rem Cvly needs Python 3.10-3.12 - newer versions may not have prebuilt
rem wheels yet for some dependencies (e.g. pydantic-core), which forces a
rem source build that fails without a full Rust/MSVC toolchain.
set "PYCMD="

for %%V in (3.12 3.11 3.10) do (
    if not defined PYCMD (
        py -%%V --version >nul 2>nul
        if not errorlevel 1 set "PYCMD=py -%%V"
    )
)

if not defined PYCMD (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
    for %%v in (3.10 3.11 3.12) do (
        echo !PYVER! | findstr /b "%%v." >nul
        if not errorlevel 1 set "PYCMD=python"
    )
)

if not defined PYCMD (
    echo No compatible Python (3.10-3.12^) found. Attempting to install Python 3.12...
    where winget >nul 2>nul
    if errorlevel 1 (
        echo winget is not available on this system.
        echo Please install Python 3.10-3.12 manually from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo Automatic Python install failed.
        echo Please install Python 3.10-3.12 manually from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set "PYCMD=py -3.12"
)

echo Using: !PYCMD!

if not exist ".venv" (
    echo Creating virtual environment...
    !PYCMD! -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing dependencies...
set PIP_DISABLE_PIP_VERSION_CHECK=1
pip install -q -r requirements.txt

if not exist ".env" (
    echo.
    echo No .env file found — launching setup wizard...
    echo.
    !PYCMD! setup.py
    if not exist ".env" (
        echo Setup was cancelled. Cannot start without .env.
        pause
        exit /b 1
    )
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
