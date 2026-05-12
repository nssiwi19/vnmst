# 🏛️ Agent Architecture — Technical Deep Dive

> Tài liệu kỹ thuật chi tiết về kiến trúc Multi-Agent System trong E14 CRM.

---

## 1. Agent Design Pattern

### Sequential Pipeline

Hệ thống sử dụng **Sequential Pipeline Pattern** — các agent chạy tuần tự, output của agent trước là input cho agent sau:

```
User Input
    │
    ▼
┌─────────┐     context      ┌─────────┐     context      ┌─────────┐
│ Agent 1  │ ──────────────→  │ Agent 2  │ ──────────────→  │ Agent 3  │
│          │                  │          │                  │          │
│ Classify │  memory bridge   │ Analyze  │  memory bridge   │ Generate │
│ + Extract│                  │ + Query  │                  │ + Validate│
└─────────┘                  └─────────┘                  └─────────┘
                                  │
                                  ▼ tool call
                           ┌──────────────┐
                           │  Supabase DB  │
                           └──────────────┘
```

### Role / Goal / Backstory Pattern

Mỗi agent được định nghĩa bởi 3 thuộc tính CrewAI:

```python
Agent(
    role="...",      # Chức danh — AI biết mình là ai
    goal="...",      # Mục tiêu — AI biết mình cần làm gì
    backstory="...", # Bối cảnh — AI biết tại sao mình làm việc này
)
```

**Tại sao cần cả 3?** LLM sử dụng 3 thuộc tính này để xây dựng "persona" nhất quán trong suốt quá trình xử lý. Backstory đặc biệt quan trọng để tránh hallucination.

---

## 2. Tool Calling Flow

### Cách agent gọi tool

```
Agent nhận task description
    │
    ├── LLM phân tích: "Cần dữ liệu DN? → Gọi tool"
    │
    ▼
LLM sinh tool call: search_enterprise_database("0314456789")
    │
    ▼
CrewAI intercept → gọi hàm Python thực tế
    │
    ▼
Hàm Python → query Supabase → trả về string
    │
    ▼
LLM nhận kết quả → tiếp tục reasoning
    │
    ▼
Output cuối cùng
```

### Tool Implementation

Mỗi tool là một hàm Python bọc bởi decorator `@tool`:

```python
@tool("search_enterprise_database")
def search_enterprise_database(mst_or_name: str) -> str:
    """Docstring = mô tả cho LLM biết khi nào gọi tool này."""
    # Logic query Supabase
    response = supabase.table("doanh_nghiep").select("*").eq("ma_so_thue", query).execute()
    return str(response.data[0])
```

**Quan trọng**: Docstring của tool được LLM đọc để quyết định có gọi tool hay không. Viết docstring rõ ràng = agent gọi tool chính xác hơn.

---

## 3. Self-Correction Mechanism

### 3 lớp bảo vệ

```
┌──────────────────────────────────────────┐
│ Lớp 3: Application Retry                 │
│ retry_with_backoff(max=3, delay=2s)       │
│ ┌──────────────────────────────────────┐  │
│ │ Lớp 2: Crew Retry                    │  │
│ │ max_retry_on_error=2, memory=True     │  │
│ │ ┌──────────────────────────────────┐  │  │
│ │ │ Lớp 1: Agent Self-Correction     │  │  │
│ │ │ max_iter=5 (retry within task)    │  │  │
│ │ └──────────────────────────────────┘  │  │
│ └──────────────────────────────────────┘  │
│                                           │
│ Guardrail Validation (post-processing)    │
│ validate_crm_output() / validate_report() │
└──────────────────────────────────────────┘
```

### Lớp 1: Agent `max_iter`

Khi tool trả lỗi hoặc output chưa đạt, agent tự retry:

```
Iteration 1: Agent gọi tool("ABC") → "Không tìm thấy"
Iteration 2: Agent thử lại tool("ABC Company") → Tìm thấy!
```

### Lớp 2: Crew `memory` + `max_retry_on_error`

- **Memory**: Agent 3 truy cập context từ Agent 1 và 2 qua short-term memory, không cần truyền toàn bộ output text
- **Retry**: Nếu Agent 2 crash (ví dụ tool timeout), Crew retry toàn bộ task 2

### Lớp 3: Application `retry_with_backoff`

```python
@retry_with_backoff(max_retries=3, base_delay=2.0)
def run_b2b_crm(email_content: str) -> str:
    # Attempt 1: OK → return
    # Attempt 1: Rate limit → wait 2s
    # Attempt 2: OK → return
    # Attempt 2: Rate limit → wait 4s
    # Attempt 3: OK → return
    # Attempt 3: Fail → raise AgentRetryError
```

### Guardrail Validation

Post-processing kiểm tra chất lượng output:

```python
# CRM Pipeline
validate_crm_output(result):
  ✓ Không rỗng
  ✓ Không chứa [placeholder]
  ✓ Có chữ ký Esgoo CRM
  ✓ Độ dài >= 50 ký tự

# Research Pipeline
validate_markdown_report(result):
  ✓ Có heading Markdown (#)
  ✓ Độ dài >= 100 ký tự
  ✓ Không leak lỗi tool
```

---

## 4. Data Flow

### CRM B2B Pipeline

```
Email đối tác (text)
    │
    ▼ [Task 1: Classifier]
{'intent': 'Khiếu nại', 'entity': '0314456789'}
    │
    ▼ [Task 2: DataAnalyst] → tool call → Supabase (table: company)
{'ma_so_thue': '0314456789', 'ten_cong_ty': 'CT Minh Tuấn', ...}
    │
    ▼ [Task 3: ResponseWriter]
"Kính gửi Anh Tuấn, Công ty Minh Tuấn..."
    │
    ▼ [Guardrail Validation]
Output hợp lệ → return cho Streamlit UI
```

### Market Research Pipeline

```
Topic (text): "Thị trường AI Việt Nam 2024"
    │
    ▼ [Task 1: Researcher] → DuckDuckGo + Supabase
Dữ liệu thô: "Thị trường AI VN đạt 800M USD..."
    │
    ▼ [Task 2: Verifier]
Dữ liệu đã xác thực (loại bỏ mâu thuẫn)
    │
    ▼ [Task 3: Writer]
# Báo cáo Thị trường AI Việt Nam
## 1. Tóm tắt...
    │
    ▼ [Guardrail Validation]
Markdown hợp lệ → return cho Streamlit UI
```

---

## 5. Configuration Reference

### Agent Config

| Param | Giá trị | Mô tả |
|-------|---------|-------|
| `llm` | `groq/llama-3.3-70b-versatile` | Model dùng chung |
| `max_iter` | 3-5 | Số lần self-correction tối đa |
| `verbose` | `True` | Log chi tiết quá trình reasoning |
| `allow_delegation` | `False` | Không cho phép agent ủy quyền |

### Crew Config

| Param | Giá trị | Mô tả |
|-------|---------|-------|
| `process` | `Process.sequential` | Chạy tuần tự |
| `memory` | `True` | Short-term memory giữa tasks |
| `max_retry_on_error` | 2 | Retry task khi crash |
| `verbose` | `True` | Log chi tiết |

### Retry Config

| Param | Giá trị | Mô tả |
|-------|---------|-------|
| `max_retries` | 3 | Số lần retry application-level |
| `base_delay` | 2.0s | Delay ban đầu |
| `max_delay` | 30.0s | Delay tối đa |
