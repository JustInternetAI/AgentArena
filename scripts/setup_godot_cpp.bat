@echo off
REM Setup script for godot-cpp dependency on Windows

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "EXTERNAL_DIR=%PROJECT_ROOT%\external"

echo Setting up godot-cpp...

REM Create external directory
if not exist "%EXTERNAL_DIR%" mkdir "%EXTERNAL_DIR%"

REM Clone godot-cpp if not present
if not exist "%EXTERNAL_DIR%\godot-cpp" (
    echo Cloning godot-cpp...
    git clone --recursive https://github.com/godotengine/godot-cpp.git "%EXTERNAL_DIR%\godot-cpp"
    cd /d "%EXTERNAL_DIR%\godot-cpp"
    git checkout 4.2
    git submodule update --init --recursive
) else (
    echo godot-cpp already exists, updating...
    cd /d "%EXTERNAL_DIR%\godot-cpp"
    git pull
    git submodule update --init --recursive
)

echo godot-cpp setup complete!
pause
