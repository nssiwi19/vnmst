"""
market_research_agent.py — Pipeline nghiên cứu thị trường tự động.
"""

import os
from crewai import Agent, Crew, Process, Task, LLM
from crewai.tools import tool
from dotenv import load_dotenv

from agent_utils import (
    retry_with_backoff,
    validate_markdown_report,
    setup_agent_logger,
)
from database import supabase

# 1. Cấu hình
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("Thiếu GROQ_API_KEY.")

# Khởi tạo các LLM với mục đích khác nhau
fast_llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=GROQ_API_KEY,
    temperature=0.0
)

premium_llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0.1
)

logger = setup_agent_logger("market_research")

# 2. Tools - Đổi tên thành CamelCase đơn giản để Groq dễ nhận diện
@tool("internetSearch")
def internetSearch(query: str) -> str:
    """Tìm kiếm thông tin trên Internet bằng DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results: return "Không tìm thấy kết quả."
            return "\n\n".join([f"Title: {r.get('title')}\nSnippet: {r.get('body')}" for r in results])
    except Exception as e:
        return f"Lỗi tìm kiếm: {str(e)}"

@tool("searchDatabase")
def searchDatabase(query: str) -> str:
    """Tra cứu dữ liệu doanh nghiệp trong database nội bộ bằng MST hoặc tên."""
    if not supabase: return "Lỗi kết nối Supabase."
    q = (query or "").strip()
    try:
        # Xử lý query để tránh lỗi Tool Calling của Groq (loại bỏ ngoặc nếu có)
        q = q.replace("(", "").replace(")", "").split("MST:")[0].strip()
        
        if q.isdigit():
            res = supabase.table("company").select("*").eq("ma_so_thue", q).limit(1).execute()
        else:
            res = supabase.table("company").select("*").ilike("ten_cong_ty", f"%{q}%").limit(3).execute()
            
        if not res.data: return f"Không tìm thấy dữ liệu cho: {q}"
        return str(res.data)
    except Exception as e:
        return f"Lỗi DB: {str(e)}"

# 3. Pipeline Function
@retry_with_backoff(max_retries=3, base_delay=2.0, logger=logger)
def run_market_research(topic: str) -> str:
    """Chạy Market Research pipeline."""
    
    researcher = Agent(
        role="Market Researcher",
        goal="Thu thập dữ liệu thực tế về {topic} bằng cách sử dụng các công cụ được cung cấp.",
        backstory="Bạn là chuyên gia phân tích dữ liệu tốc độ cao. Bạn LUÔN sử dụng các công cụ để lấy số liệu thực tế.",
        verbose=True,
        llm=fast_llm,
        tools=[internetSearch, searchDatabase],
        max_iter=3
    )

    verifier = Agent(
        role="Data Verifier",
        goal="Kiểm tra tính xác thực của dữ liệu từ Researcher.",
        backstory="Bạn là chuyên gia kiểm định. Bạn loại bỏ các thông tin không nhất quán.",
        verbose=True,
        llm=fast_llm,
        max_iter=3
    )

    writer = Agent(
        role="Report Writer",
        goal="Viết báo cáo Markdown chuyên nghiệp từ dữ liệu đã xác thực.",
        backstory="Bạn là chuyên gia viết báo cáo kinh doanh cho lãnh đạo cấp cao.",
        verbose=True,
        llm=premium_llm,
        max_iter=3
    )

    task1 = Task(
        description="Nghiên cứu về: {topic}. Sử dụng searchDatabase nếu là tên công ty/MST, nếu không dùng internetSearch.",
        expected_output="Bản tổng hợp dữ liệu thô.",
        agent=researcher
    )

    task2 = Task(
        description="Xác thực dữ liệu từ Task 1. Loại bỏ các giả định không có căn cứ.",
        expected_output="Dữ liệu đã xác thực.",
        agent=verifier,
        context=[task1]
    )

    task3 = Task(
        description="Viết báo cáo Markdown (không dùng in đậm **) từ dữ liệu Task 2.",
        expected_output="Báo cáo Markdown hoàn chỉnh.",
        agent=writer,
        context=[task2]
    )

    crew = Crew(
        agents=[researcher, verifier, writer],
        tasks=[task1, task2, task3],
        process=Process.sequential,
        verbose=True,
        memory=False # Quan trọng: Tắt để tránh lỗi search_memory trên Groq
    )

    result = crew.kickoff(inputs={"topic": topic})
    raw = str(result)

    validation = validate_markdown_report(raw)
    return validation["sanitized"]
