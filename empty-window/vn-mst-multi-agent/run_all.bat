@echo off
echo Dang khoi dong Elite-DA Project (Giao dien & AI CRM)...

:: Chạy Frontend
start "FRONTEND (React)" cmd /k "cd frontend && npm install && npm run dev"

:: Chạy Backend
start "BACKEND (AI CRM)" cmd /k "cd backend-api && pip install -r requirements.txt && streamlit run app.py"

echo Da kich hoat Frontend va Backend. Du lieu se duoc lay truc tiep tu Supabase.
