"""
market_research_agent.py — Pipeline nghiên cứu thị trường tự động.

Pipeline: Researcher → Verifier → Writer (3 agents, sequential)

LLM: Groq Llama-3.3-70b-versatile
  Lý do chọn: Thống nhất với crm_b2b_agent.py. Tốc độ inference nhanh,
  miễn phí qua Groq Cloud, chất lượng tiếng Việt tốt cho báo cáo phân tích.

Self-correction: max_iter, memory, max_retry_on_error, guardrail validation.
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

# 1. Cấu hình API Key
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError(
        "Thiếu GROQ_API_KEY. Hãy tạo file .env từ .env.example."
    )

from crm_b2b_agent import search_enterprise_database
from database import supabase

SHARED_TABLE_NAME = "company"

main_llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY
)

logger = setup_agent_logger("market_research")


# 2. Tools
@tool("internet_search_tool")
def search_tool(query: str) -> str:
    """Tìm kiếm thông tin trên Internet bằng DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results:
                return "Không tìm thấy kết quả nào."
            output = []
            for r in results:
                output.append(
                    f"Title: {r.get('title')}\n"
                    f"Snippet: {r.get('body')}\n"
                    f"Link: {r.get('href')}"
                )
            return "\n\n".join(output)
    except Exception as e:
        return f"Lỗi tìm kiếm: {str(e)}"


@tool("search_uploaded_dataset")
def search_uploaded_dataset(query: str) -> str:
    """Tra cứu dữ liệu đã upload vào Supabase bằng MST hoặc tên công ty."""
    if not supabase:
        return "Lỗi: Không kết nối được Supabase."
    q = (query or "").strip()
    if not q:
        return "Không có truy vấn hợp lệ."
    try:
        if any(ch.isdigit() for ch in q):
            response = (
                supabase.table(SHARED_TABLE_NAME)
                .select("ma_so_thue, ten_cong_ty, ma_tinh, ma_nganh, so_dien_thoai, email, so_nha")
                .eq("ma_so_thue", q).limit(3).execute()
            )
        else:
            response = (
                supabase.table(SHARED_TABLE_NAME)
                .select("ma_so_thue, ten_cong_ty, ma_tinh, ma_nganh, so_dien_thoai, email, so_nha")
                .ilike("ten_cong_ty", f"%{q}%").limit(5).execute()
            )
        if not response.data:
            return f"Không tìm thấy trong `{SHARED_TABLE_NAME}` cho: {q}"
        
        # Enrich data with lookup names
        results = []
        for record in response.data:
            # Lookup Tỉnh thành
            ma_tinh = record.get("ma_tinh")
            if ma_tinh:
                try:
                    tinh_resp = supabase.table("dia_chi").select("ten_tinh").eq("ma_tinh", ma_tinh).execute()
                    if tinh_resp.data:
                        record["ten_tinh_thanh"] = tinh_resp.data[0]["ten_tinh"]
                except: pass
            
            # Lookup Ngành nghề
            ma_nganh = record.get("ma_nganh")
            if ma_nganh:
                try:
                    nganh_resp = supabase.table("nganh_nghe").select("ten_nganh").eq("ma_nganh", ma_nganh).execute()
                    if nganh_resp.data:
                        record["ten_nganh_nghe"] = nganh_resp.data[0]["ten_nganh"]
                except: pass
            results.append(record)

        return str(results)
    except Exception as e:
        return f"Lỗi truy vấn `{SHARED_TABLE_NAME}`: {str(e)}"


# 5. Hàm chạy pipeline (retry + validation)
@retry_with_backoff(max_retries=3, base_delay=2.0, logger=logger)
def run_market_research(topic: str) -> str:
    """
    Chạy Market Research pipeline với self-correction:
    - memory=True, max_retry_on_error=2 (CrewAI level)
    - retry_with_backoff (application level)
    - validate_markdown_report trước khi trả kết quả
    """
    # 3. Agents (Khởi tạo bên trong hàm để đảm bảo tính độc lập cho mỗi session/user)
    researcher_agent = Agent(
        role="Market Researcher",
        goal=(
            "Tìm kiếm trên Internet và thu thập dữ liệu mới nhất về thị trường. "
            "TUYỆT ĐỐI KHÔNG tự bịa số liệu. Luôn dùng tool tìm kiếm."
        ),
        backstory=(
            "Chuyên gia nghiên cứu thị trường. Luôn sử dụng công cụ tìm kiếm "
            "để lấy dữ liệu thật. Không bao giờ đưa ra số liệu tự đoán."
        ),
        verbose=True,
        allow_delegation=False,
        llm=main_llm,
        tools=[search_tool, search_uploaded_dataset, search_enterprise_database],
        max_iter=3
    )

    verifier_agent = Agent(
        role="Data Verifier",
        goal=(
            "Kiểm tra tính hợp lý và độ tin cậy của dữ liệu từ Researcher. "
            "Loại bỏ thông tin mâu thuẫn, sai lệch."
        ),
        backstory=(
            "Chuyên gia kiểm định dữ liệu (Data QA) khắt khe. "
            "Không chấp nhận thông tin thiếu căn cứ hoặc số liệu không nhất quán."
        ),
        verbose=True,
        allow_delegation=False,
        llm=main_llm,
        max_iter=3
    )

    writer_agent = Agent(
        role="Report Writer",
        goal=(
            "Tổng hợp dữ liệu đã kiểm duyệt thành báo cáo chuyên nghiệp "
            "có cấu trúc Markdown (Tóm tắt, Phân tích, Kết luận)."
        ),
        backstory=(
            "Chuyên viên phân tích kinh doanh kiêm copywriter. "
            "Biến số liệu khô khan thành câu chuyện hấp dẫn cho C-level."
        ),
        verbose=True,
        allow_delegation=False,
        llm=main_llm,
        max_iter=3
    )

    # 4. Tasks (Khởi tạo bên trong hàm để tránh ghi đè dữ liệu Task giữa các thread/request)
    task1 = Task(
        description=(
            'Nghiên cứu toàn diện về: "{topic}". '
            'Nếu hỏi về công ty/MST cụ thể, dùng search_uploaded_dataset trước, '
            'rồi search_enterprise_database, cuối cùng mới dùng internet_search_tool. '
            'BẮT BUỘC dùng tool để lấy số liệu thực.'
        ),
        expected_output=(
            "Bản tóm tắt dữ liệu thô toàn diện với số liệu thực tế, "
            "xu hướng và nhận định chuyên gia."
        ),
        agent=researcher_agent,
    )

    task2 = Task(
        description=(
            "Kiểm tra logic dữ liệu thô từ Task 1. Tìm điểm mâu thuẫn. "
            "Nếu không có dữ liệu, ghi nhận rõ 'KHÔNG CÓ DỮ LIỆU'. "
            "KHÔNG lấy dữ liệu ngành/khu vực khác để thay thế."
        ),
        expected_output=(
            "Danh sách thông tin đã xác thực. Nếu không có dữ liệu: "
            "'Thị trường chưa tồn tại hoặc không có số liệu'."
        ),
        agent=verifier_agent,
    )

    task3 = Task(
        description=(
            "Viết báo cáo Markdown hoàn chỉnh từ dữ liệu Task 2. "
            "Nếu Task 2 báo 'không có dữ liệu', kết luận ngắn gọn. "
            "KHÔNG suy diễn số liệu, KHÔNG lời khuyên đầu tư sáo rỗng."
        ),
        expected_output=(
            "Báo cáo Markdown phản ánh trung thực tình trạng dữ liệu."
        ),
        agent=writer_agent,
    )

    crew = Crew(
        agents=[researcher_agent, verifier_agent, writer_agent],
        tasks=[task1, task2, task3],
        process=Process.sequential,
        verbose=True,
        memory=True,
        max_retry_on_error=2,
    )

    logger.info("Bắt đầu Market Research cho: %s", topic[:80])
    result = crew.kickoff(inputs={"topic": topic})
    raw = result.raw if hasattr(result, 'raw') else str(result)

    validation = validate_markdown_report(raw)
    if not validation["valid"]:
        logger.warning("Validation: %s", "; ".join(validation["issues"]))
        warning = "⚠️ QA: " + "; ".join(validation["issues"]) + "\n\n---\n\n"
        return warning + validation["sanitized"]

    logger.info("Market Research hoàn tất OK")
    return validation["sanitized"]


if __name__ == "__main__":
    test_topic = "Thị trường AI tại Việt Nam năm 2024"
    print(f"Khởi động Market Research: {test_topic}...\n")
    report = run_market_research(test_topic)
    print("\n" + "=" * 50)
    print(" BÁO CÁO HOÀN THÀNH:")
    print("=" * 50)
    print(report)
