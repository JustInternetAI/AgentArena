@echo off
REM Complete setup script for Agent Arena on Windows

setlocal EnableDelayedExpansion

echo ========================================
echo   Agent Arena Setup Script
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Check prerequisites
echo Checking prerequisites...

where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: git is not installed
    exit /b 1
)

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: python is not installed
    exit /b 1
)

where cmake >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: cmake is not installed
    exit /b 1
)

echo [OK] All prerequisites found
echo.

REM Setup godot-cpp
echo Setting up godot-cpp...
call "%SCRIPT_DIR%\setup_godot_cpp.bat"
echo [OK] godot-cpp setup complete
echo.

REM Build C++ module
echo Building C++ module...
cd /d "%PROJECT_ROOT%\godot"

if not exist "build" mkdir build
cd build

cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release

if %ERRORLEVEL% NEQ 0 (
    echo Error: Build failed
    exit /b 1
)

echo [OK] C++ module built
echo.

REM Setup Python environment
echo Setting up Python environment...
cd /d "%PROJECT_ROOT%\python"

if not exist "venv" (
    python -m venv venv
)

call venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo Error: Python setup failed
    exit /b 1
)

echo [OK] Python environment ready
echo.

REM Create necessary directories
echo Creating project directories...
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"
if not exist "%PROJECT_ROOT%\replays" mkdir "%PROJECT_ROOT%\replays"
if not exist "%PROJECT_ROOT%\metrics" mkdir "%PROJECT_ROOT%\metrics"
if not exist "%PROJECT_ROOT%\models" mkdir "%PROJECT_ROOT%\models"

echo [OK] Directories created
echo.

REM Run tests
echo Running tests...
cd /d "%PROJECT_ROOT%\tests"
pytest -v
echo.

echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Next steps:
echo 1. Download a model to models/ directory
echo 2. Update configs/backend/llama_cpp.yaml with model path
echo 3. Open the project in Godot 4
echo 4. Run: python python\test_agent.py
echo.
echo See docs/quickstart.md for detailed instructions
echo.
pause
