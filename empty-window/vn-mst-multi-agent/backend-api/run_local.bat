@echo off
setlocal

python -m venv .venv
if errorlevel 1 exit /b %errorlevel%

call .\.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b %errorlevel%

call .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b %errorlevel%

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo Da tao .env tu .env.example. Hay cap nhat OPENAI_API_KEY truoc khi chay lai.
  exit /b 0
)

call .\.venv\Scripts\python.exe crm_b2b_agent.py

endlocal
