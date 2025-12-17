@echo off
echo ==========================================
echo       FiAi Project Launcher
echo ==========================================

echo [1/2] Starting Django Backend...
start "FiAi Backend" cmd /k "cd backend && python manage.py runserver"

echo [2/2] Starting Frontend...
start "FiAi Frontend" cmd /k "cd fronted && npm run dev"

echo ==========================================
echo    Services are starting in new windows
echo    Backend: http://127.0.0.1:8000
echo    Frontend: http://localhost:5173
echo ==========================================
pause
