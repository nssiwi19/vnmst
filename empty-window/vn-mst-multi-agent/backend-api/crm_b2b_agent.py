"""
crm_b2b_agent.py — Pipeline xử lý email B2B tự động.
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

# 1. Cấu hình
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("Thiếu GROQ_API_KEY.")

# Khởi tạo các LLM với mục đích khác nhau
# 8B cho tốc độ và tiết kiệm Rate Limit
fast_llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=GROQ_API_KEY,
    temperature=0.0
)

# 70B cho chất lượng viết lách
premium_llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0.1
)

logger = setup_agent_logger("crm_b2b")

# 2. Tools - Đổi tên thành CamelCase để ổn định trên Groq
@tool("searchCrmDatabase")
def searchCrmDatabase(query: str) -> str:
    """Truy vấn CSDL doanh nghiệp nội bộ để lấy thông tin chi tiết."""
    if not supabase: return "Lỗi kết nối Supabase."
    q = (query or "").strip()
    # Làm sạch query
    q = q.replace("(", "").replace(")", "").split("MST:")[0].strip()
    
    try:
        if q.isdigit():
            res = supabase.table("company").select("*").eq("ma_so_thue", q).limit(1).execute()
        else:
            res = supabase.table("company").select("*").ilike("ten_cong_ty", f"%{q}%").limit(3).execute()
            
        if not res.data: return f"Không tìm thấy doanh nghiệp: {q}"
        return str(res.data)
    except Exception as e:
        return f"Lỗi DB: {str(e)}"

# 3. Pipeline Function
@retry_with_backoff(max_retries=3, base_delay=2.0, logger=logger)
def run_b2b_crm(input_data: Union[str, dict]) -> dict:
    """Chạy CRM B2B pipeline."""
    text_content = f"Dữ liệu: {input_data}" if isinstance(input_data, dict) else str(input_data)

    classifier = Agent(
        role="Intent Classifier",
        goal="Xác định ý định khách hàng và MST/Tên DN.",
        backstory="Bạn là chuyên gia phân tích intent tốc độ cao. Bạn trích xuất MST hoặc Tên DN cực kỳ chính xác.",
        verbose=True,
        llm=fast_llm, # Dùng 8B cho nhanh
        max_iter=3
    )

    analyst = Agent(
        role="CRM Data Analyst",
        goal="Tra cứu thông tin DN bằng công cụ searchCrmDatabase.",
        backstory="Bạn sử dụng công cụ searchCrmDatabase để lấy profile chính xác từ database.",
        verbose=True,
        llm=fast_llm, # Dùng 8B để tiết kiệm Token
        tools=[searchCrmDatabase],
        max_iter=3
    )

    writer = Agent(
        role="B2B Response Writer",
        goal="Soạn email phản hồi chuyên nghiệp dựa trên dữ liệu CRM.",
        backstory="Bạn soạn email B2B lịch sự, chuyên nghiệp và có chữ ký Esgoo.",
        verbose=True,
        llm=premium_llm, # Chỉ dùng 70B cho bước viết lách cuối cùng
        max_iter=3
    )

    task1 = Task(
        description=f"Phân tích intent và MST/Tên DN từ nội dung: {text_content}",
        expected_output="JSON chứa intent và entity.",
        agent=classifier
    )

    task2 = Task(
        description="Dùng kết quả Task 1, gọi searchCrmDatabase để lấy profile.",
        expected_output="Dữ liệu doanh nghiệp chi tiết.",
        agent=analyst,
        context=[task1]
    )

    task3 = Task(
        description="Dựa trên dữ liệu Task 2, soạn email phản hồi (không in đậm **).",
        expected_output="Email Markdown hoàn chỉnh.",
        agent=writer,
        context=[task2]
    )

    crew = Crew(
        agents=[classifier, analyst, writer],
        tasks=[task1, task2, task3],
        process=Process.sequential,
        verbose=True,
        memory=False
    )

    result = crew.kickoff()
    validation = validate_crm_output(str(result))
    
    return {
        "research": {"legalForm": "Công ty", "inferredSector": "Đang xác định", "profileBullets": ["Tra cứu từ Supabase"]},
        "report": {"summary": validation["sanitized"]},
        "crm_insights": {
            "riskLevel": "Thấp",
            "suggestedSubject": "Phản hồi thông tin doanh nghiệp",
            "suggestedEmail": validation["sanitized"],
            "keywords": ["CRM", "Automation"]
        }
    }
