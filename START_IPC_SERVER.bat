@echo off
REM Agent Arena - IPC Server Startup Script
REM This script starts the Python IPC server for Godot-Python communication

echo ========================================
echo Agent Arena - Starting IPC Server
echo ========================================
echo.

cd /d "%~dp0\python"

REM Check if venv exists
if not exist "venv\" (
    echo ERROR: Python virtual environment not found!
    echo Please run: python -m venv venv
    echo Then install dependencies: venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate venv
echo Activating Python virtual environment...
call venv\Scripts\activate.bat

REM Check if required packages are installed
python -c "import fastapi, uvicorn" 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Required packages not installed!
    echo Installing dependencies...
    pip install fastapi uvicorn
    if errorlevel 1 (
        echo.
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo.
echo Starting IPC Server...
echo Server will be available at: http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python run_ipc_server.py

REM If server exits, pause so user can see error
if errorlevel 1 (
    echo.
    echo Server exited with error!
    pause
)
