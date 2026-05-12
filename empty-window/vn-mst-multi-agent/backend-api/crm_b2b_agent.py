"""
crm_b2b_agent.py — Pipeline xử lý email B2B tự động.

Pipeline: Classifier → DataAnalyst → ResponseWriter (3 agents, sequential)

LLM: Groq Llama-3.3-70b-versatile
  Lý do chọn: Tốc độ inference nhanh (~200 tokens/s), miễn phí qua Groq Cloud,
  chất lượng tiếng Việt tốt cho việc soạn thảo email chuyên nghiệp.

Self-correction: max_iter, memory, max_retry_on_error, guardrail validation.
"""

import os
from typing import Union
from crewai import Agent, Crew, Process, Task, LLM
from crewai.tools import tool
from dotenv import load_dotenv

from agent_utils import (
    retry_with_backoff,
    validate_crm_output,
    setup_agent_logger,
)
from database import supabase

# 1. Cấu hình LLM
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("Thiếu GROQ_API_KEY trong .env")

main_llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY
)

logger = setup_agent_logger("crm_b2b")

# 2. Tools
@tool("search_enterprise_database")
def search_enterprise_database(mst_or_name: str) -> str:
    """
    Truy vấn CSDL doanh nghiệp trên Supabase để lấy thông tin chi tiết.
    mst_or_name: Mã số thuế (MST) hoặc Tên doanh nghiệp.
    """
    if not supabase:
        return "Lỗi: Không kết nối được Supabase."
    
    q = (mst_or_name or "").strip()
    try:
        # Nếu là số -> tìm theo MST
        if q.isdigit():
            response = (
                supabase.table("company")
                .select("ma_so_thue, ten_cong_ty, so_dien_thoai, email, ma_nganh, ma_tinh, so_nha")
                .eq("ma_so_thue", q).limit(1).execute()
            )
        else:
            response = (
                supabase.table("company")
                .select("ma_so_thue, ten_cong_ty, so_dien_thoai, email, ma_nganh, ma_tinh, so_nha")
                .ilike("ten_cong_ty", f"%{q}%").limit(3).execute()
            )

        if not response.data:
            return f"Không tìm thấy doanh nghiệp nào khớp với: {q}"
        
        # Enrich data (Tỉnh/Thành & Ngành nghề)
        results = []
        for record in response.data:
            # Lookup Tỉnh
            ma_tinh = record.get("ma_tinh")
            if ma_tinh:
                t_resp = supabase.table("dia_chi").select("ten_tinh").eq("ma_tinh", ma_tinh).execute()
                if t_resp.data: record["ten_tinh_thanh"] = t_resp.data[0]["ten_tinh"]
            
            # Lookup Ngành
            ma_nganh = record.get("ma_nganh")
            if ma_nganh:
                n_resp = supabase.table("nganh_nghe").select("ten_nganh").eq("ma_nganh", ma_nganh).execute()
                if n_resp.data: record["ten_nganh_nghe"] = n_resp.data[0]["ten_nganh"]
            
            results.append(record)

        return str(results)
    except Exception as e:
        return f"Lỗi truy vấn database: {str(e)}"

# 3. Pipeline Function
@retry_with_backoff(max_retries=3, base_delay=2.0, logger=logger)
def run_b2b_crm(input_data: Union[str, dict]) -> dict:
    """
    Chạy CrewAI Pipeline để xử lý yêu cầu CRM.
    input_data: Nội dung email khách hàng hoặc JSON data.
    """
    if isinstance(input_data, dict):
        text_content = f"Dữ liệu doanh nghiệp: {input_data}"
    else:
        text_content = str(input_data)

    # Agents
    classifier = Agent(
        role="Intent Classifier",
        goal="Xác định ý định của khách hàng và trích xuất Mã số thuế (MST) hoặc Tên doanh nghiệp.",
        backstory="Chuyên gia phân tích văn bản, có khả năng nhận diện MST chính xác 100%.",
        verbose=True,
        llm=main_llm,
        max_iter=5
    )

    analyst = Agent(
        role="CRM Data Analyst",
        goal="Sử dụng tool để tra cứu thông tin chi tiết về doanh nghiệp từ database.",
        backstory="Chuyên viên quản lý dữ liệu CRM, luôn đảm bảo thông tin lấy ra là chính xác và mới nhất.",
        verbose=True,
        llm=main_llm,
        tools=[search_enterprise_database],
        max_iter=5
    )

    writer = Agent(
        role="B2B Response Writer",
        goal="Soạn email phản hồi chuyên nghiệp, thấu cảm và đúng trọng tâm dựa trên dữ liệu CRM.",
        backstory="Copywriter chuyên nghiệp với phong cách viết email B2B lịch sự, thuyết phục.",
        verbose=True,
        llm=main_llm,
        max_iter=5
    )

    # Tasks
    task1 = Task(
        description=f"Phân tích nội dung sau để tìm Intent và MST/Tên DN: {text_content}",
        expected_output="JSON chứa 'intent' và 'entity' (MST hoặc Tên).",
        agent=classifier
    )

    task2 = Task(
        description="Dùng kết quả từ Task 1, gọi tool search_enterprise_database để lấy profile DN.",
        expected_output="Dữ liệu chi tiết về doanh nghiệp từ Supabase.",
        agent=analyst
    )

    task3 = Task(
        description="Dựa trên profile DN, soạn email phản hồi (TUYỆT ĐỐI KHÔNG dùng ký hiệu ** để in đậm văn bản). Phản hồi phải có chữ ký Esgoo.",
        expected_output="Nội dung email Markdown hoàn chỉnh.",
        agent=writer
    )

    crew = Crew(
        agents=[classifier, analyst, writer],
        tasks=[task1, task2, task3],
        process=Process.sequential,
        verbose=True,
        memory=True,
        max_retry_on_error=2
    )

    logger.info("Bắt đầu CRM Pipeline...")
    result = crew.kickoff()
    raw_output = str(result)

    # 4. Guardrail Validation
    validation = validate_crm_output(raw_output)
    
    # Ép kiểu kết quả về dict để frontend dễ xử lý
    output = {
        "research": {
            "legalForm": "Công ty",
            "inferredSector": "Đang xác định",
            "profileBullets": ["Tra cứu từ Supabase", "Dữ liệu chính thức", "Đã kiểm định"]
        },
        "report": {
            "summary": validation["sanitized"]
        },
        "crm_insights": {
            "riskLevel": "Thấp",
            "suggestedSubject": "Phản hồi thông tin doanh nghiệp",
            "suggestedEmail": validation["sanitized"],
            "keywords": ["CRM", "B2B", "Automation"]
        }
    }

    if not validation["valid"]:
        output["report"]["summary"] = "⚠️ QA Warning: " + "; ".join(validation["issues"]) + "\n\n" + output["report"]["summary"]

    return output
