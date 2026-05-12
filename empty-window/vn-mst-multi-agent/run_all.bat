@echo off
SET ROOT_DIR=%~dp0
echo ====================================================
echo    KHOI DONG ELITE-DA MULTI-AGENT SYSTEM
echo ====================================================

:: 1. Khoi dong Backend FastAPI
:: Su dung python -m uvicorn de dam bao chay dung moi truong venv
start cmd /k "echo Dang khoi dong Backend API... && cd /d %ROOT_DIR%backend-api && ..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: 2. Khoi dong Frontend React (Vite)
start cmd /k "echo Dang khoi dong Frontend React... && cd /d %ROOT_DIR%frontend && npm run dev"

echo ----------------------------------------------------
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo ----------------------------------------------------
echo He thong dang chay. Vui long khong dong cac cua so terminal.
pause
