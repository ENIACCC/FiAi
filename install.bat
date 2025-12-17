@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo               FiAi Project - Dependency Installer
echo ========================================================
echo.

:: 1. Backend Installation
echo [1/2] Installing Backend Dependencies...
cd backend
if exist requirements.txt (
    pip install -r requirements.txt
    if !errorlevel! equ 0 (
        echo [SUCCESS] Backend dependencies installed.
    ) else (
        echo [ERROR] Failed to install backend dependencies.
        pause
        exit /b %errorlevel%
    )
) else (
    echo [WARNING] requirements.txt not found in backend directory.
)
cd ..
echo.

:: 2. Frontend Installation
echo [2/2] Installing Frontend Dependencies...
cd fronted
if exist package.json (
    call npm install
    if !errorlevel! equ 0 (
        echo [SUCCESS] Frontend dependencies installed.
    ) else (
        echo [ERROR] Failed to install frontend dependencies.
        pause
        exit /b %errorlevel%
    )
) else (
    echo [WARNING] package.json not found in fronted directory.
)
cd ..

echo.
echo ========================================================
echo        Installation Complete! Ready to Start.
echo ========================================================
pause
