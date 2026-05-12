python -m venv .venv
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

.\.venv\Scripts\python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

.\.venv\Scripts\python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Da tao .env tu .env.example. Hay cap nhat OPENAI_API_KEY truoc khi chay."
  exit 0
}

.\.venv\Scripts\python crm_b2b_agent.py
