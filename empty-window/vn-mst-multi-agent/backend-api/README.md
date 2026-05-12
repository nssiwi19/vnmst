---
title: E14CRM AI Agent
emoji: 📈
colorFrom: blue
colorTo: red
sdk: docker
sdk_version: "1.32.2"
python_version: "3.10"
app_file: app.py
pinned: false
---

# 📈 Esgoo CRM & AI Agent — Multi-Agent System

Hệ thống Multi-Agent AI xử lý nghiệp vụ CRM B2B và Nghiên cứu thị trường tự động, xây dựng trên nền tảng **CrewAI** + **Groq Llama-3.3**.

> **Tech Stack**: CrewAI · Groq Llama-3.3-70b · Streamlit · Supabase · DuckDuckGo Search · Docker

---

## 🏗️ Kiến trúc hệ thống

Hệ thống gồm **2 pipeline độc lập**, mỗi pipeline 3 agents chạy tuần tự (sequential) với cơ chế self-correction:

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │Market Research│  │ CRM B2B Resp │  │Data Analytics │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
└─────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐
│ Pipeline 1      │ │ Pipeline 2      │ │ Analytics Tool   │
│                 │ │                 │ │                  │
│ Researcher      │ │ Classifier      │ │ Upload CSV/Excel │
│   ↓ (memory)    │ │   ↓ (memory)    │ │ Supabase Sync    │
│ Verifier        │ │ DataAnalyst     │ │ Visualizations   │
│   ↓ (memory)    │ │   ↓ (memory)    │ │ Smart Filtering  │
│ Writer          │ │ ResponseWriter  │ │ Export Excel     │
└────────┬────────┘ └────────┬────────┘ └────────┬─────────┘
         │                   │                    │
         ▼                   ▼                    ▼
┌──────────────────────────────────────────────────────────┐
│                   Supabase (PostgreSQL)                   │
│  ┌──────────────┐  ┌─────────────────────────────────┐   │
│  │ company      │  │ Lookup: dia_chi, nganh_nghe      │   │
│  │ (100K+ DN)   │  │ xa_phuong (Dữ liệu nền)         │   │
│  └──────────────┘  └─────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### Pipeline 1: Market Research (`market_research_agent.py`)

| Agent | Vai trò | Tools |
|-------|---------|-------|
| **Researcher** | Thu thập dữ liệu thực từ Internet + DB | DuckDuckGo, Supabase query |
| **Verifier** | Kiểm tra logic, loại bỏ mâu thuẫn | — |
| **Writer** | Viết báo cáo Markdown chuyên nghiệp | — |

### Pipeline 2: CRM B2B Response (`crm_b2b_agent.py`)

| Agent | Vai trò | Tools |
|-------|---------|-------|
| **Classifier** | Phân loại intent + trích xuất MST/Tên DN | — |
| **DataAnalyst** | Tra cứu CRM database | Supabase query |
| **ResponseWriter** | Soạn email phản hồi B2B thấu cảm | — |

---

## 🤖 Lý do chọn LLM: Groq Llama-3.3-70b-versatile

Cả 2 pipeline **thống nhất** sử dụng cùng 1 LLM để đảm bảo consistency:

| Tiêu chí | Groq Llama-3.3-70b |
|----------|-------------------|
| **Tốc độ** | ~200 tokens/s (nhanh nhất thị trường nhờ Groq LPU) |
| **Chi phí** | Miễn phí qua Groq Cloud (rate limit 30 req/min) |
| **Tiếng Việt** | Chất lượng tốt cho NLP, phân loại intent, viết email |
| **Context** | 32K tokens — đủ cho email B2B + CRM data |
| **Tool Calling** | Hỗ trợ native function calling |

---

## 🔧 Tool Calling

| Tool | File | Chức năng |
|------|------|-----------|
| `search_enterprise_database` | `crm_b2b_agent.py` | Query bảng `doanh_nghiep` trên Supabase bằng MST hoặc Tên |
| `internet_search_tool` | `market_research_agent.py` | Tìm kiếm Internet qua DuckDuckGo (không bịa số liệu) |
| `search_uploaded_dataset` | `market_research_agent.py` | Query bảng `market_research_dataset` trên Supabase |

> **Lưu ý**: Agent được thiết kế để **luôn gọi tool** lấy dữ liệu thực thay vì tự sinh số liệu (hallucination prevention).

---

## 🛡️ Self-Correction & Error Handling

Hệ thống có **3 lớp** bảo vệ chống lỗi:

### Lớp 1: Agent-level (`max_iter=5`)
Mỗi agent được phép retry tối đa 5 lần nếu tool trả lỗi hoặc output chưa đạt yêu cầu.

### Lớp 2: Crew-level (`memory=True`, `max_retry_on_error=2`)
- **Memory**: Short-term memory giữa các task trong cùng 1 run, giúp agent sau tham khảo context từ agent trước
- **Retry**: CrewAI tự động retry toàn bộ task nếu thất bại (tối đa 2 lần)

### Lớp 3: Application-level (`retry_with_backoff`)
- Exponential backoff (2s → 4s → 8s) khi gặp API rate limit
- Guardrail validation kiểm tra output trước khi trả về:
  - **CRM**: Kiểm tra không rỗng, không chứa `[placeholder]`, có chữ ký Esgoo
  - **Research**: Kiểm tra có Markdown heading, đủ dài, không leak lỗi tool

```python
# Ví dụ: Nếu output CRM chứa [Tên của bạn] → cảnh báo QA
validation = validate_crm_output(raw_output)
if not validation["valid"]:
    return "⚠️ QA: " + issues + "\n\n" + output
```

---

## 🗄️ Database (Supabase — PostgreSQL)

Hệ thống kết nối **trực tiếp** đến Supabase thực (không mock data trong agent tools):

| Bảng | Mô tả | Số bản ghi |
|------|-------|------------|
| `company` | Kho dữ liệu DN (ma_so_thue, ten_cong_ty, ma_tinh, ma_nganh...) | 100,000+ |
| `dia_chi` | Danh mục Tỉnh/Thành phố (HN, HCM) | 2 |
| `nganh_nghe` | Danh mục 334 ngành nghề kinh doanh | 334 |
| `chat_logs` | Lịch sử chat Streamlit | Dynamic |

> **Graceful degradation**: `data_analytics_tool.py` có `get_mock_data()` làm fallback khi Supabase không kết nối được — chỉ ảnh hưởng dashboard hiển thị, **không** ảnh hưởng agent pipeline.

---

## 🚀 Cài đặt & Chạy

### Chạy Local

```bash
# 1. Clone repo
git clone https://github.com/<your-username>/E14-CRM.git
cd E14-CRM

# 2. Tạo môi trường ảo
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

# 3. Cài dependencies
pip install -r requirements.txt

# 4. Cấu hình API keys
cp .env.example .env
# Sửa .env: điền GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY

# 5. Chạy ứng dụng
streamlit run app.py
```

### Chạy với Docker

```bash
docker build -t esgoo-crm .
docker run -p 7860:7860 --env-file .env esgoo-crm
```

### Deploy lên Render/HuggingFace

Xem chi tiết tại [README_RENDER_DEPLOYMENT.md](README_RENDER_DEPLOYMENT.md).

---

## 📁 Cấu trúc dự án

```
CRM/
├── app.py                      # Streamlit UI (3 tabs: Research, CRM, Analytics)
├── crm_b2b_agent.py            # Pipeline 2: CRM B2B Response (3 agents)
├── market_research_agent.py    # Pipeline 1: Market Research (3 agents)
├── agent_utils.py              # Shared: retry, validation, logging
├── database.py                 # Supabase client initialization
├── data_analytics_tool.py      # Data Analytics Dashboard
├── test_supabase.py            # Integration test cho Supabase
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container cho deploy
├── .env.example                # Template biến môi trường
├── docs/
│   ├── VIBE_CODING_GUIDE.md    # Hướng dẫn Vibe Coding & AI Workflow
│   └── AGENT_ARCHITECTURE.md   # Tài liệu kiến trúc Multi-Agent
└── README.md                   # File này
```

---

## 📚 Tài liệu bổ sung

- [Vibe Coding & AI Coding Workflow Guide](docs/VIBE_CODING_GUIDE.md) — Hướng dẫn áp dụng AI-assisted development cho team
- [Agent Architecture Deep Dive](docs/AGENT_ARCHITECTURE.md) — Kiến trúc kỹ thuật chi tiết multi-agent system
- [Local Setup Guide](README_LOCAL_SETUP.md) — Hướng dẫn cài đặt local
- [Render Deployment Guide](README_RENDER_DEPLOYMENT.md) — Hướng dẫn deploy lên Render.com