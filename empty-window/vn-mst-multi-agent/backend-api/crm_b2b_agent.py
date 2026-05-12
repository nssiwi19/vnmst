"""
crm_b2b_agent.py — Pipeline xử lý email B2B tự động.

Pipeline: Classifier → DataAnalyst → ResponseWriter (3 agents, sequential)

LLM: Groq Llama-3.3-70b-versatile
  Lý do chọn: Tốc độ inference nhanh (~200 tokens/s), miễn phí qua Groq Cloud,
  chất lượng tiếng Việt tốt, thống nhất với market_research_agent.py.

Self-correction: max_iter, memory, max_retry_on_error, guardrail validation.

Database Schema (Supabase):
  - company: ma_so_thue (PK), ten_cong_ty, so_dien_thoai, email, ma_nganh, ma_tinh, xa_phuong_id, so_nha
  - dia_chi: ma_tinh (PK), ten_tinh
  - nganh_nghe: ma_nganh (PK), ten_nganh
  - xa_phuong: id (PK), ten_xa_phuong, ma_tinh
  - v_company: View join company + dia_chi + nganh_nghe + xa_phuong
"""

import ast
import os
import re
from typing import Optional

from crewai import Agent, Crew, Process, Task, LLM
from crewai.tools import tool
from dotenv import load_dotenv

from agent_utils import (
    retry_with_backoff,
    validate_crm_output,
    setup_agent_logger,
)

try:
    from database import supabase
except ImportError:
    supabase = None

# 1. Cấu hình API Key & LLM
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError(
        "Thiếu GROQ_API_KEY hợp lệ. Hãy tạo file .env từ .env.example."
    )

main_llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY
)

logger = setup_agent_logger("crm_b2b")


# 2. Tool truy xuất dữ liệu doanh nghiệp từ Supabase
@tool("search_enterprise_database")
def search_enterprise_database(mst_or_name: str) -> str:
    """
    Truy vấn CSDL doanh nghiệp từ Supabase bằng MST hoặc Tên công ty.
    Trả về: MST, Tên công ty, SĐT, Email, Ngành nghề, Tỉnh/Thành, Địa chỉ.
    """
    query = (mst_or_name or "").strip()
    if not query:
        return "Không tìm thấy dữ liệu do truy vấn rỗng."

    if not supabase:
        return "Lỗi: Không kết nối được Supabase. Kiểm tra .env"

    # Bảng chính: company (PK: ma_so_thue)
    # Bảng lookup: dia_chi (ma_tinh → ten_tinh), nganh_nghe (ma_nganh → ten_nganh)
    TABLE_NAME = "company"
    SELECT_COLS = "ma_so_thue, ten_cong_ty, so_dien_thoai, email, ma_nganh, ma_tinh, so_nha"

    try:
        # Tìm kiếm bằng MST (exact match) hoặc tên công ty (ilike)
        if any(c.isdigit() for c in query) and len(query) >= 10:
            response = supabase.table(TABLE_NAME).select(SELECT_COLS).eq("ma_so_thue", query).execute()
        else:
            response = supabase.table(TABLE_NAME).select(SELECT_COLS).ilike("ten_cong_ty", f"%{query}%").execute()

        data = response.data
        if not data or len(data) == 0:
            # Fallback: thử tìm bằng ilike nếu lần đầu dùng eq
            fallback = supabase.table(TABLE_NAME).select(SELECT_COLS).ilike("ten_cong_ty", f"%{query}%").execute()
            if fallback.data and len(fallback.data) > 0:
                data = fallback.data
            else:
                return f"Không tìm thấy doanh nghiệp khớp '{query}' trong CRM."

        record = data[0]

        # Enrich: lookup tên tỉnh/thành từ bảng dia_chi
        ma_tinh = record.get("ma_tinh")
        if ma_tinh:
            try:
                tinh_resp = supabase.table("dia_chi").select("ten_tinh").eq("ma_tinh", ma_tinh).execute()
                if tinh_resp.data:
                    record["ten_tinh_thanh"] = tinh_resp.data[0]["ten_tinh"]
            except Exception:
                record["ten_tinh_thanh"] = ma_tinh  # fallback: dùng mã

        # Enrich: lookup tên ngành nghề từ bảng nganh_nghe
        ma_nganh = record.get("ma_nganh")
        if ma_nganh:
            try:
                nganh_resp = supabase.table("nganh_nghe").select("ten_nganh").eq("ma_nganh", ma_nganh).execute()
                if nganh_resp.data:
                    record["ten_nganh_nghe"] = nganh_resp.data[0]["ten_nganh"]
            except Exception:
                record["ten_nganh_nghe"] = ma_nganh  # fallback: dùng mã

        return str(record)
    except Exception as e:
        return f"Lỗi truy vấn Supabase: {str(e)}"


def _extract_mst_or_company_name(task1_output: str) -> Optional[str]:
    """Heuristic bóc tách MST/Tên công ty từ kết quả Task 1."""
    if not task1_output:
        return None
    mst_match = re.search(r"\b\d{10,14}\b", task1_output)
    if mst_match:
        return mst_match.group(0)
    company_match = re.search(r"(Công ty[^.,\n]+)", task1_output, re.IGNORECASE)
    if company_match:
        return company_match.group(1).strip()
    return None


# 3. Agents (max_iter=5 cho self-correction)
classifier_agent = Agent(
    role="B2B Intent & Entity Classifier",
    goal="Phân loại intent và trích xuất MST/Tên công ty từ email đối tác.",
    backstory="Chuyên gia phân tích văn bản B2B, luôn bóc tách MST hoặc Tên công ty chính xác.",
    verbose=True,
    allow_delegation=False,
    llm=main_llm,
    max_iter=5,
)

data_agent = Agent(
    role="Enterprise Data Analyst",
    goal="Tra cứu thông tin doanh nghiệp trong CSDL bằng tool search_enterprise_database.",
    backstory="Nắm giữ quyền truy cập kho doanh nghiệp VN. Luôn lấy từ DB, không bịa.",
    tools=[search_enterprise_database],
    verbose=True,
    allow_delegation=False,
    llm=main_llm,
    max_iter=5,
)

response_agent = Agent(
    role="Chuyên viên Hỗ trợ Đối tác - Esgoo CRM",
    goal=(
        "Viết email phản hồi B2B chuyên nghiệp. "
        "Bạn là nhân viên Esgoo CRM, đang trả lời khách hàng."
    ),
    backstory=(
        "Partner Support Specialist tại Esgoo CRM. Khách hàng là các doanh nghiệp B2B. "
        "Luôn ký tên 'Đội ngũ hỗ trợ kỹ thuật - Esgoo CRM'."
    ),
    verbose=True,
    allow_delegation=False,
    llm=main_llm,
    max_iter=5,
)

# 4. Tasks
task1 = Task(
    description=(
        'Phân tích email: "{enterprise_email}". '
        "Xác định vấn đề, phân loại intent (Hợp tác/Hỗ trợ/Khiếu nại), "
        "trích xuất MST hoặc Tên công ty."
    ),
    expected_output=(
        "JSON: {'intent':'...','issue_summary':'...','entity':'...'}"
    ),
    agent=classifier_agent,
)

task2 = Task(
    description=(
        "Lấy entity từ Task 1, truyền vào search_enterprise_database "
        "để truy vấn CRM. Nếu không chuẩn JSON, tự bóc tách MST/Tên."
    ),
    expected_output="Dữ liệu chi tiết doanh nghiệp từ Database.",
    agent=data_agent,
)

task3 = Task(
    description=(
        "Viết email phản hồi B2B hoàn chỉnh dựa trên email gốc + dữ liệu Task 2.\n"
        "QUY TẮC: 1) Đại diện Esgoo CRM. 2) Gửi đích danh. "
        "3) KHÔNG dùng [placeholder]. 4) Thấu cảm theo ngành nghề. "
        "5) Lộ trình xử lý 3 bước."
    ),
    expected_output="Email B2B tiếng Việt, ký tên Esgoo CRM.",
    agent=response_agent,
)


# 5. Hàm chạy pipeline (retry + guardrail)
@retry_with_backoff(max_retries=3, base_delay=2.0, logger=logger)
def run_b2b_crm(email_content: str) -> str:
    """
    Chạy CRM B2B pipeline với self-correction:
    - memory=True, max_retry_on_error=2 (CrewAI level)
    - retry_with_backoff (application level)
    - guardrail validation trước khi trả kết quả
    """
    crew = Crew(
        agents=[classifier_agent, data_agent, response_agent],
        tasks=[task1, task2, task3],
        process=Process.sequential,
        verbose=True,
        memory=True,
        max_retry_on_error=2,
    )

    logger.info("Bắt đầu CRM pipeline cho email: %s...", email_content[:80])
    result = crew.kickoff(inputs={"enterprise_email": email_content})
    raw = result.raw if hasattr(result, 'raw') else str(result)

    validation = validate_crm_output(raw)
    if not validation["valid"]:
        logger.warning("Validation: %s", "; ".join(validation["issues"]))
        warning = "⚠️ QA: " + "; ".join(validation["issues"]) + "\n\n---\n\n"
        return warning + validation["sanitized"]

    logger.info("CRM pipeline hoàn tất OK")
    return validation["sanitized"]


if __name__ == "__main__":
    test_email = """
    Kính gửi đội ngũ hỗ trợ,
    Tôi là Tuấn từ Công ty CP Bán lẻ Minh Tuấn (MST: 0314456789).
    Hệ thống cửa hàng bị lỗi khi gọi API đối soát dữ liệu.
    Ảnh hưởng thanh toán khách hàng tại quầy. Mong kiểm tra gấp.
    """
    print("Khởi động CRM Auto-Classification & Response...\n")
    result = run_b2b_crm(test_email)
    print("\n" + "=" * 50)
    print(" EMAIL PHẢN HỒI TỰ ĐỘNG:")
    print("=" * 50)
    print(result)
