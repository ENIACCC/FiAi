@echo off
setlocal

title FiAi Project Launcher
echo ========================================================
echo                  Starting FiAi Project
echo ========================================================
echo.

:: Check directories
if not exist "backend" (
    echo [ERROR] 'backend' directory not found!
    pause
    exit /b 1
)
if not exist "fronted" (
    echo [ERROR] 'fronted' directory not found!
    pause
    exit /b 1
)

:: 1. Start Backend
echo [1/2] Launching Backend Server (Django)...
cd backend
start "FiAi Backend Server" cmd /k "echo Starting Django... && python manage.py runserver 0.0.0.0:8000"
cd ..

:: 2. Start Frontend
echo [2/2] Launching Frontend Server (Vite)...
cd fronted
start "FiAi Frontend Server" cmd /k "echo Starting Vite... && npm run dev"
cd ..

echo.
echo ========================================================
echo                 Services Launching...
echo.
echo    - Backend API: http://localhost:8000
echo    - Frontend UI: http://localhost:5173
echo.
echo    Please do not close the popped-up command windows.
echo ========================================================
pause
