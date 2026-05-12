# Multi-Agent CRM B2B Demo - Local Setup

## 1) Tao moi truong Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 2) Cai thu vien can thiet

```powershell
pip install --upgrade pip
pip install crewai langchain openai
```

## 3) Khai bao API key (khong hardcode)

```powershell
$env:OPENAI_API_KEY="sk-..."
```

## 4) Chay demo

- Chạy CRM B2B Demo:
```powershell
python crm_b2b_agent.py
```

- Chạy Market Research Demo:
```powershell
python market_research_agent.py
```

## Chay tu dong 1 lenh

```powershell
powershell -ExecutionPolicy Bypass -File .\run_local.ps1
```

Neu ban dung cmd:

```cmd
run_local.bat
```

## 5) Kiem tra ket qua mong doi

- Task 1: Nhan dien intent + trich xuat MST/ten doanh nghiep
- Task 2: Goi tool Search_Enterprise_Database tra ve thong tin CRM
- Task 3: Tao email phan hoi tieng Viet theo ERG, co dong cam va ca nhan hoa

## 6) Nang cap tiep theo (goi y)

- Tach mock_db ra file JSON/CSV de de quan ly
- Them logging cho tung task va luu output
- Them bo test cho extraction MST + intent classification
- Ket noi DB that (PostgreSQL/MySQL) thay cho mock data
