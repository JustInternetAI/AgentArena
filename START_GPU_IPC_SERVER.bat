@echo off
REM Agent Arena - GPU-Accelerated IPC Server Startup Script
REM This script starts the Python IPC server with GPU-accelerated LLM backend

echo ========================================
echo Agent Arena - GPU IPC Server
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
python -c "import fastapi, uvicorn, llama_cpp" 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Required packages not installed!
    echo Please install dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo Starting GPU-Accelerated IPC Server...
echo ========================================
echo Model: Llama-2-7B Chat (Q4_K_M quantization)
echo GPU Acceleration: ENABLED (all layers)
echo Expected Speed: ~113 tokens/sec
echo Server Address: http://127.0.0.1:5000
echo.
echo Tools Available: 15+ (movement, inventory, world query)
echo Default Agent: gpu_agent_001
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

python run_ipc_server_with_gpu.py --gpu-layers -1

REM If server exits, pause so user can see error
if errorlevel 1 (
    echo.
    echo Server exited with error!
    pause
)
