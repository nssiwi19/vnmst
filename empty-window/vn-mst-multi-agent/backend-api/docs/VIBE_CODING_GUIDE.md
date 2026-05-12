# 🎯 Vibe Coding & AI-Assisted Development Guide

> **Đối tượng**: Thành viên team phát triển E14 CRM & các dự án AI  
> **Mục tiêu**: Áp dụng Vibe Coding workflow để tăng tốc phát triển phần mềm 3-5x

---

## 1. Vibe Coding là gì?

**Vibe Coding** là phương pháp phát triển phần mềm trong đó lập trình viên **mô tả ý tưởng bằng ngôn ngữ tự nhiên** và để AI tạo code, thay vì viết từng dòng thủ công.

```
Truyền thống:  Ý tưởng → Thiết kế → Code thủ công → Debug → Test → Deploy
Vibe Coding:   Ý tưởng → Prompt AI → Review code → Iterate → Deploy
```

### Triết lý cốt lõi

| Nguyên tắc | Mô tả |
|------------|-------|
| **Describe, Don't Code** | Mô tả _cái bạn muốn_, không phải _cách làm_ |
| **Iterate Rapidly** | Prompt → xem kết quả → sửa prompt → lặp lại |
| **AI as Pair Programmer** | AI viết code, bạn review và quyết định |
| **Context is King** | Prompt càng rõ context, code càng chính xác |

---

## 2. AI Coding Workflow (5 bước)

### Bước 1: Ý tưởng → User Story

Trước khi prompt AI, viết rõ user story:

```
AS A [vai trò]
I WANT [chức năng]
SO THAT [lợi ích]

Acceptance Criteria:
- [ ] Tiêu chí 1
- [ ] Tiêu chí 2
```

**Ví dụ E14 CRM:**
```
AS A support agent at Esgoo CRM
I WANT the system to auto-classify incoming B2B emails
SO THAT I can respond faster with personalized, data-driven replies

Acceptance:
- [ ] Classify intent (Hợp tác/Hỗ trợ/Khiếu nại)
- [ ] Extract MST/Company name
- [ ] Query real CRM database
- [ ] Generate empathetic email response
```

### Bước 2: Prompt Engineering

**Cấu trúc prompt hiệu quả:**

```
[CONTEXT] Mô tả dự án, tech stack, constraints
[TASK] Cái cần làm cụ thể
[FORMAT] Output mong muốn (code, markdown, JSON...)
[EXAMPLES] Ví dụ input/output nếu có
[CONSTRAINTS] Giới hạn, edge cases, điều KHÔNG làm
```

**Ví dụ thực tế:**

```
CONTEXT: CrewAI multi-agent system, Python 3.12, Groq Llama-3.3
TASK: Tạo agent "Data Verifier" kiểm tra số liệu từ Market Researcher
FORMAT: Python code với CrewAI Agent class
CONSTRAINTS:
- Không tự bịa số liệu
- Nếu dữ liệu mâu thuẫn, ghi nhận "KHÔNG CÓ DỮ LIỆU"
- max_iter=3
```

### Bước 3: Code Generation + Review

1. AI sinh code
2. **Review checklist:**
   - [ ] Code có chạy được không? (syntax check)
   - [ ] Logic có đúng business requirement không?
   - [ ] Có hardcoded values cần thay đổi không?
   - [ ] Error handling đã đủ chưa?
   - [ ] Security: có leak API key, SQL injection không?

### Bước 4: Iterate & Refine

```
Prompt sửa: "Code hoạt động nhưng thiếu retry logic khi API rate limit.
Thêm exponential backoff với max_retries=3, base_delay=2s."
```

### Bước 5: Test & Deploy

- Unit test cho từng function
- Integration test cho pipeline
- Smoke test trên staging
- Deploy (Docker → Render/HuggingFace)

---

## 3. Công cụ Vibe Coding

### IDE & AI Assistants

| Công cụ | Chức năng | Khi nào dùng |
|---------|-----------|-------------|
| **Cursor AI** | IDE tích hợp AI, auto-complete, chat | Code hàng ngày |
| **GitHub Copilot** | Inline code suggestions | Viết code mới |
| **Claude / ChatGPT** | Tư vấn kiến trúc, debug phức tạp | Thiết kế hệ thống |

### AI Frameworks (cho sản phẩm)

| Framework | Chức năng | Dùng trong E14 |
|-----------|-----------|---------------|
| **CrewAI** | Multi-agent orchestration | ✅ 2 pipeline |
| **LangChain** | LLM chain, memory, tools | Tham khảo |
| **Streamlit** | Rapid UI prototyping | ✅ Dashboard |

### LLM APIs

| Provider | Model | Ưu điểm |
|----------|-------|---------|
| **Groq** | Llama-3.3-70b | Nhanh nhất, miễn phí |
| **OpenAI** | GPT-4o | Chất lượng cao nhất |
| **Google** | Gemini Pro | Multimodal, context dài |

---

## 4. Best Practices

### ✅ DO (Nên làm)

1. **Prompt rõ ràng, có context** — AI không đọc được suy nghĩ của bạn
2. **Review TỪNG dòng code AI sinh ra** — AI có thể hallucinate
3. **Commit thường xuyên** — Mỗi thay đổi nhỏ = 1 commit
4. **Viết test trước (TDD)** — Cho AI biết acceptance criteria
5. **Giữ prompt history** — Để team đồng bộ cách prompt

### ❌ DON'T (Không nên)

1. **Copy-paste không đọc** — AI code có thể chứa bug tinh vi
2. **Prompt quá chung chung** — "Viết cho tôi 1 app CRM" → quá mơ hồ
3. **Bỏ qua error handling** — AI thường viết happy path
4. **Hardcode secrets** — Luôn dùng `.env` + environment variables
5. **Dùng AI cho security-critical code** — Luôn review bởi senior

---

## 5. Case Study: E14 CRM

### Quá trình xây dựng bằng Vibe Coding

#### Phase 1: Scaffolding (30 phút)
```
Prompt: "Tạo CrewAI project với 3 agents (Classifier, DataAnalyst, 
ResponseWriter) xử lý email B2B. Dùng Groq Llama-3.3. 
Output: Python files + Streamlit UI."
```
→ AI sinh ra skeleton `crm_b2b_agent.py` + `app.py`

#### Phase 2: Tool Integration (1 giờ)
```
Prompt: "Thêm @tool search_enterprise_database query Supabase 
bảng doanh_nghiep. Tìm bằng MST (exact match) hoặc Tên (ilike). 
Trả về dict Python."
```
→ AI tạo tool + Supabase query logic

#### Phase 3: Self-Correction (45 phút)
```
Prompt: "Agents chạy sequential thuần, thiếu error handling. Thêm:
1. max_iter=5 cho mỗi agent
2. memory=True cho Crew
3. retry_with_backoff decorator cho API rate limit
4. Output validation (không placeholder, có signature)"
```
→ AI tạo `agent_utils.py` + upgrade cả 2 pipeline

#### Phase 4: Documentation (30 phút)
```
Prompt: "Viết README.md hoàn chỉnh: kiến trúc, LLM rationale, 
tool calling, self-correction, setup guide, project structure."
```
→ AI sinh README + docs

**Tổng thời gian**: ~3 giờ (so với ~2-3 ngày code thủ công)

---

## 6. Hướng dẫn áp dụng cho Team

### Tuần 1: Làm quen
- [ ] Cài Cursor AI hoặc GitHub Copilot
- [ ] Thực hành prompt engineering cơ bản
- [ ] Code 1 function nhỏ hoàn toàn bằng AI

### Tuần 2: Ứng dụng
- [ ] Dùng AI refactor 1 module có sẵn
- [ ] Viết unit test bằng AI
- [ ] Review code AI cho nhau (peer review)

### Tuần 3: Nâng cao
- [ ] Thiết kế kiến trúc module mới bằng AI
- [ ] Tích hợp AI agent vào workflow
- [ ] Đo lường productivity (trước vs sau)

### Tuần 4: Chia sẻ
- [ ] Mỗi thành viên chia sẻ 1 tip/trick
- [ ] Tạo prompt library cho team
- [ ] Đánh giá và cải tiến workflow

---

## 📎 Tham khảo

- [CrewAI Documentation](https://docs.crewai.com/)
- [Groq API Docs](https://console.groq.com/docs/)
- [Cursor AI](https://cursor.sh/)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
