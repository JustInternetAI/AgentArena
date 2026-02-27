@echo off
REM Agent Arena - Claude Agent (Anthropic API)
REM Starts the Python IPC server with Claude as the decision-making LLM
REM Then open Godot, load scenes/foraging.tscn, press F5, then SPACE

echo ========================================
echo Agent Arena - Claude Agent (Anthropic)
echo ========================================
echo.

REM Check for API key
if "%ANTHROPIC_API_KEY%"=="" (
    echo ERROR: ANTHROPIC_API_KEY is not set!
    echo.
    echo To set it permanently ^(recommended, only need to do this once^):
    echo   1. Start menu ^> search "environment variables"
    echo   2. Edit the system environment variables ^> Environment Variables
    echo   3. Under User variables ^> New
    echo   4. Name: ANTHROPIC_API_KEY   Value: sk-ant-...
    echo.
    echo Or set it for this session only:
    echo   set ANTHROPIC_API_KEY=sk-ant-...
    echo.
    echo Get a key at: https://console.anthropic.com
    pause
    exit /b 1
)

cd /d "%~dp0"

REM Check if .venv exists (project root venv)
if exist ".venv\" (
    echo Activating .venv...
    call .venv\Scripts\activate.bat
    goto :check_deps
)

REM Check if python/venv exists (legacy venv)
if exist "python\venv\" (
    echo Activating python\venv...
    call python\venv\Scripts\activate.bat
    goto :check_deps
)

echo ERROR: No Python virtual environment found!
echo Please run: python -m venv .venv
echo Then install dependencies: .venv\Scripts\pip install agent-arena-sdk anthropic
pause
exit /b 1

:check_deps
REM Check if required packages are installed
python -c "import agent_arena_sdk, anthropic" 2>nul
if errorlevel 1 (
    echo.
    echo Installing required packages...
    pip install agent-arena-sdk anthropic
    if errorlevel 1 (
        echo.
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo.
echo Model  : claude-sonnet-4-20250514 (change with --model flag)
echo Server : http://127.0.0.1:5000
echo Debug  : http://127.0.0.1:5000/debug
echo Cost   : ~$0.10 per 100-tick run (Sonnet)
echo.
echo Next steps:
echo   1. Open Godot and load scenes/foraging.tscn
echo   2. Press F5 to run the scene
echo   3. Press SPACE to start the simulation
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

cd /d "%~dp0\starters\claude"
python run.py --debug %*

REM If server exits, pause so user can see error
if errorlevel 1 (
    echo.
    echo Server exited with error!
    pause
)
