@echo off
REM Initialize Git repository and push to GitHub (Windows)

setlocal EnableDelayedExpansion

echo ==========================================
echo   Agent Arena - GitHub Initialization
echo ==========================================
echo.

set "REPO_URL=https://github.com/JustInternetAI/AgentArena.git"

REM Check if git is installed
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: git is not installed
    exit /b 1
)

REM Initialize repository if not already done
if not exist ".git" (
    echo Initializing git repository...
    git init
    echo [OK] Git repository initialized
) else (
    echo [OK] Git repository already initialized
)

REM Configure git user
echo.
echo Configuring git user...
set /p GIT_NAME="Enter your name (e.g., Justin Madison): "
set /p GIT_EMAIL="Enter your email: "

git config user.name "%GIT_NAME%"
git config user.email "%GIT_EMAIL%"
echo [OK] Git user configured

REM Add remote if not exists
git remote | findstr /C:"origin" >nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Adding remote origin...
    git remote add origin "%REPO_URL%"
    echo [OK] Remote added: %REPO_URL%
) else (
    echo [OK] Remote 'origin' already exists
)

REM Show status
echo.
echo ==========================================
echo Repository Status:
echo ==========================================
git status

REM Ask to commit and push
echo.
set /p CONFIRM="Ready to commit and push? (y/n): "
if /i "%CONFIRM%"=="y" (
    echo.
    echo Adding files...
    git add .

    echo Creating commit...
    git commit -m "Initial commit: Agent Arena framework - Godot C++ GDExtension module with core simulation classes - Python agent runtime with LLM backend support - Tool system (world query, movement, inventory) - Memory infrastructure (short-term and RAG) - Comprehensive documentation and setup guides - Apache 2.0 license with founder attribution - GitHub workflows and issue templates Founded by Andrew Madison and Justin Madison Maintained by JustInternetAI"

    echo.
    echo Pushing to GitHub...
    git branch -M main
    git push -u origin main

    echo.
    echo ==========================================
    echo [OK] Repository pushed to GitHub!
    echo ==========================================
    echo.
    echo Next steps:
    echo 1. Visit: https://github.com/JustInternetAI/AgentArena
    echo 2. Configure repository settings (topics, about, etc.^)
    echo 3. Review and merge any dependabot PRs
    echo 4. Create your first release (v0.1.0^)
    echo.
    echo See GITHUB_SETUP.md for detailed configuration instructions
) else (
    echo.
    echo Skipped. When ready, run:
    echo   git add .
    echo   git commit -m "Initial commit"
    echo   git push -u origin main
)

echo.
pause
