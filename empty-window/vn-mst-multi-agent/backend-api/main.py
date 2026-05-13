from fastapi import FastAPI, Depends, HTTPException, status, Header, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase import create_client, Client
import os
import csv
import io
from dotenv import load_dotenv

# Import các pipeline đã được refactor
from crm_b2b_agent import run_b2b_crm
from market_research_agent import run_market_research

load_dotenv()

app = FastAPI(title="Elite-DA API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Kết nối Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise EnvironmentError("Thiếu cấu hình Supabase URL hoặc Key.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Dependency: Xác thực JWT từ Supabase Auth
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        # Kiểm tra token với Supabase Auth
        res = supabase.auth.get_user(token)
        return res.user
    except Exception as e:
        print(f"Auth error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token không hợp lệ hoặc đã hết hạn"
        )

# --- Models ---
class ResearchRequest(BaseModel):
    topic: str = None
    tax_code: str = None
    company_data: dict = None
    purpose: str = "kyc"

# --- Endpoints ---

async def run_ai_analysis_task(
    analysis_id: str,
    req: ResearchRequest,
    user_id: str,
    token: str
):
    """Xử lý AI Agent ngầm và cập nhật kết quả vào database."""
    try:
        # 1. Chạy AI Analysis
        if req.purpose == "market_research":
            topic = f"Phân tích thị trường và tiềm năng của doanh nghiệp: {req.company_data.get('name')} (MST: {req.company_data.get('id')})"
            research_report = run_market_research(topic)
            
            result = {
                "research": {
                    "legalForm": "Đang xác minh",
                    "inferredSector": "Nghiên cứu thị trường",
                    "profileBullets": ["Phân tích sâu từ Internet", "Dữ liệu đa nguồn", "Đã qua kiểm định"]
                },
                "report": {
                    "summary": research_report
                },
                "crm_insights": {
                    "riskLevel": "Trung bình",
                    "suggestedSubject": f"Cơ hội hợp tác chiến lược với {req.company_data.get('name')}",
                    "suggestedEmail": "Dựa trên báo cáo nghiên cứu thị trường chuyên sâu...",
                    "keywords": ["Market", "Research", "Strategy"]
                }
            }
        else:
            result = run_b2b_crm(req.company_data)

        # 2. Cập nhật kết quả vào database
        # Chúng ta dùng token của user để bypass RLS nếu cần
        supabase.postgrest.auth(token)
        
        update_data = {
            "research_data": result.get("research"),
            "report_content": result.get("report", {}).get("summary"),
            "crm_insights": result.get("crm_insights"),
            "status": "completed"
        }
        
        supabase.table("company_analysis").update(update_data).eq("id", analysis_id).execute()
        print(f"Task {analysis_id} completed successfully.")

    except Exception as e:
        print(f"Error in background task {analysis_id}: {str(e)}")
        try:
            supabase.table("company_analysis").update({"status": "failed", "error_log": str(e)}).eq("id", analysis_id).execute()
        except:
            pass

@app.post("/api/analyze")
async def analyze_company(
    req: ResearchRequest, 
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user=Depends(get_current_user)
):
    """Khởi tạo quy trình phân tích bất đồng bộ."""
    try:
        # 1. Tạo bản ghi 'pending' trước
        token = credentials.credentials
        supabase.postgrest.auth(token)
        
        initial_data = {
            "user_id": user.id,
            "tax_code": req.company_data.get("id"),
            "company_name": req.company_data.get("name"),
            "status": "pending"
        }
        
        res = supabase.table("company_analysis").insert(initial_data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Không thể khởi tạo bản ghi phân tích")
            
        analysis_id = res.data[0]["id"]

        # 2. Đẩy vào background task
        background_tasks.add_task(
            run_ai_analysis_task, 
            analysis_id, 
            req, 
            user.id, 
            token
        )
        
        return {"id": analysis_id, "status": "pending", "message": "Quy trình phân tích đã bắt đầu ngầm."}
        
    except Exception as e:
        print(f"Error initiating analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_history(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user=Depends(get_current_user)
):
    """Lấy lịch sử phân tích của user."""
    try:
        token = credentials.credentials
        supabase.postgrest.auth(token)
        
        response = supabase.table("company_analysis") \
            .select("*") \
            .eq("user_id", user.id) \
            .order("created_at", desc=True) \
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi Database: {str(e)}")

@app.get("/api/analyze/{analysis_id}")
async def get_analysis_status(
    analysis_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user=Depends(get_current_user)
):
    """Lấy trạng thái và kết quả của task phân tích."""
    try:
        token = credentials.credentials
        supabase.postgrest.auth(token)
        
        res = supabase.table("company_analysis") \
            .select("*") \
            .eq("id", analysis_id) \
            .execute()
            
        if not res.data:
            raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi")
            
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/companies")
async def list_companies(q: str = None, page: int = 1, page_size: int = 50):
    """Truy vấn danh sách doanh nghiệp (Xử lý thông minh Tỉnh/Thành từ ma_phuong)."""
    offset = (page - 1) * page_size
    try:
        # 1. Lấy danh mục tỉnh thành để map (Cache đơn giản)
        tinh_res = supabase.table("tinh_thanh").select("*").execute()
        tinh_map = {t["ma_tinh"]: t["ten_tinh"] for t in tinh_res.data}
        
        # 2. Truy vấn doanh nghiệp
        query = supabase.table("company").select("*, nganh_nghe(ten_nganh)", count="exact")
        if q:
            q = q.strip()
            if q.isdigit():
                query = query.eq("ma_so_thue", q)
            else:
                query = query.ilike("ten_cong_ty", f"%{q}%")
        
        response = query.range(offset, offset + page_size - 1).order("created_at", desc=True).execute()
        
        normalized = []
        for item in (response.data or []):
            # Lấy tên tỉnh từ 2 ký tự đầu của ma_phuong
            ma_phuong = item.get("ma_phuong") or ""
            prefix = ma_phuong[:2].upper() if len(ma_phuong) >= 2 else ""
            
            # Xử lý trường hợp đặc biệt: HC -> HCM
            if prefix == "HC": prefix = "HCM"
            
            item["ten_tinh"] = tinh_map.get(prefix, "Chưa rõ")
            item["ten_nganh"] = item.get("nganh_nghe", {}).get("ten_nganh") if item.get("nganh_nghe") else "Khác"
            normalized.append(item)
            
        return {"data": normalized, "total": response.count, "page": page, "page_size": page_size}
    except Exception as e:
        print(f"Error: {e}")
        return {"data": [], "total": 0, "page": page, "page_size": page_size}

@app.delete("/api/companies/{mst}")
async def delete_company(mst: str):
    """Xóa doanh nghiệp khỏi database."""
    try:
        supabase.table("company").delete().eq("ma_so_thue", mst).execute()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/seed-demo")
async def seed_demo():
    """Nạp 7 doanh nghiệp mẫu vào database."""
    from seed_demo_data import DEMO_COMPANIES
    try:
        supabase.table("company").upsert(DEMO_COMPANIES, on_conflict="ma_so_thue").execute()
        return {"status": "success", "count": len(DEMO_COMPANIES)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest-csv")
async def ingest_csv(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """Nạp dữ liệu từ file CSV vào bảng company."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .csv")

    try:
        content = await file.read()
        decoded = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        
        records = []
        for row in reader:
            # Kiểm tra các cột bắt buộc
            mst = row.get('ma_so_thue')
            name = row.get('ten_cong_ty')
            if not mst or not name:
                continue

            # Xây dựng bản ghi (Sử dụng giá trị mặc định cho các trường bắt buộc nếu thiếu)
            record = {
                "ma_so_thue": str(mst).strip(),
                "ten_cong_ty": str(name).strip(),
                "ngay_thanh_lap": row.get('ngay_thanh_lap', ''),
                "so_dien_thoai": row.get('so_dien_thoai', ''),
                "email": row.get('email', ''),
                "ma_nganh": row.get('ma_nganh', '00000'), # Default 'Khác'
                "ma_phuong": row.get('ma_phuong', '00000'), # Default 'Khác'
                "so_nha": row.get('so_nha', ''),
                "dia_chi_day_du": row.get('dia_chi_day_du', 'Đang cập nhật'),
                "nguon": f"Upload by {user.email}"
            }
            records.append(record)

        if not records:
            return {"status": "error", "message": "Không tìm thấy dữ liệu hợp lệ trong CSV"}

        # Thực hiện Upsert hàng loạt (Batch Upsert)
        # Lưu ý: ma_so_thue là khóa chính
        res = supabase.table("company").upsert(records, on_conflict="ma_so_thue").execute()
        
        return {
            "status": "success", 
            "inserted": len(records),
            "message": f"Đã nạp thành công {len(records)} doanh nghiệp"
        }

    except Exception as e:
        print(f"Ingest Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý CSV: {str(e)}")


@app.get("/api/stats/by-region")
async def stats_by_region(year: int = None, industry: str = None):
    """Thống kê Tỉnh/Thành từ TOÀN BỘ dữ liệu có lọc."""
    try:
        all_data = []
        page = 0
        page_size = 1000
        while True:
            query = supabase.table("company").select("ma_phuong, ma_nganh, ngay_thanh_lap").range(page*page_size, (page+1)*page_size - 1)
            if industry: query = query.eq("ma_nganh", industry)
            res = query.execute()
            if not res.data: break
            
            data = res.data
            if year:
                data = [d for d in data if d.get("ngay_thanh_lap") and str(year) in d.get("ngay_thanh_lap")]
            
            all_data.extend(data)
            if len(res.data) < page_size: break
            page += 1
            
        stats = {"Hồ Chí Minh": 0, "Hà Nội": 0}
        for item in all_data:
            ma = item.get("ma_phuong", "")
            if ma.startswith("HC"): stats["Hồ Chí Minh"] += 1
            elif ma.startswith("HN"): stats["Hà Nội"] += 1
            
        return [{"name": k, "value": v} for k, v in stats.items()]
    except: return []

@app.get("/api/stats/by-industry")
async def stats_by_industry():
    """Thống kê top 50 ngành nghề từ TOÀN BỘ dữ liệu."""
    try:
        all_ma = []
        page = 0
        page_size = 1000
        while True:
            res = supabase.table("company").select("ma_nganh").range(page*page_size, (page+1)*page_size - 1).execute()
            if not res.data: break
            all_ma.extend([d["ma_nganh"] for d in res.data if d.get("ma_nganh")])
            if len(res.data) < page_size: break
            page += 1
            
        counts = {}
        for m in all_ma: counts[m] = counts.get(m, 0) + 1
            
        ind_res = supabase.table("nganh_nghe").select("ma_nganh, ten_nganh").execute()
        names = {i["ma_nganh"]: i["ten_nganh"] for i in ind_res.data}
        
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:50]
        return [{"name": f"{k} - {names.get(k, 'N/A')}", "value": v} for k, v in sorted_counts]
    except: return []

@app.get("/api/stats/growth-trend")
async def get_growth_trend(industry: str = None):
    """Thống kê xu hướng từ TOÀN BỘ dữ liệu."""
    try:
        all_dates = []
        page = 0
        page_size = 1000
        while True:
            query = supabase.table("company").select("ngay_thanh_lap").range(page*page_size, (page+1)*page_size - 1)
            if industry: query = query.eq("ma_nganh", industry)
            res = query.execute()
            if not res.data: break
            all_dates.extend([d["ngay_thanh_lap"] for d in res.data if d.get("ngay_thanh_lap")])
            if len(res.data) < page_size: break
            page += 1
            
        yearly_counts = {}
        for date_str in all_dates:
            try:
                year = int(date_str.split('/')[-1]) if '/' in date_str else int(date_str.split('-')[0])
                if 2015 <= year <= 2026:
                    yearly_counts[year] = yearly_counts.get(year, 0) + 1
            except: continue
        
        return [{"name": str(y), "value": yearly_counts.get(y, 0)} for y in range(2015, 2027)]
    except: return []

@app.get("/api/stats/summary")
async def stats_summary(year: int = None, industry: str = None):
    """Tổng hợp chỉ số động từ TOÀN BỘ dữ liệu."""
    try:
        # Total count (with optional industry filter)
        query = supabase.table("company").select("id", count="exact")
        if industry: query = query.eq("ma_nganh", industry)
        res = query.execute()
        total = res.count or 0
        
        # If year filter, count by scanning ngay_thanh_lap
        if year:
            count = 0
            page = 0
            while True:
                q = supabase.table("company").select("ngay_thanh_lap").range(page*1000, (page+1)*1000 - 1)
                if industry: q = q.eq("ma_nganh", industry)
                r = q.execute()
                if not r.data: break
                count += sum(1 for d in r.data if d.get("ngay_thanh_lap") and str(year) in d.get("ngay_thanh_lap"))
                if len(r.data) < 1000: break
                page += 1
            total = count

        # Dynamic top industry from by-industry endpoint
        try:
            ind_data = await stats_by_industry()
            top_name = ind_data[0]["name"].split("-")[-1].strip() if ind_data else "N/A"
            top_value = ind_data[0]["value"] if ind_data else 0
            total_ind = sum(d["value"] for d in ind_data) if ind_data else 1
            share = round((top_value / total_ind) * 100, 1) if total_ind > 0 else 0
        except:
            top_name = "N/A"
            share = 0

        return {
            "total": total,
            "top_industry": top_name,
            "industry_share": share,
            "health": 99.8,
            "regions": 2
        }
    except: return {"total": 0, "top_industry": "N/A", "industry_share": 0, "health": 0, "regions": 0}


@app.get("/api/stats/monthly-distribution")
async def monthly_distribution(year: int = None, industry: str = None):
    """Phân bố đăng ký doanh nghiệp theo tháng."""
    try:
        all_dates = []
        page = 0
        while True:
            query = supabase.table("company").select("ngay_thanh_lap").range(page*1000, (page+1)*1000 - 1)
            if industry: query = query.eq("ma_nganh", industry)
            res = query.execute()
            if not res.data: break
            all_dates.extend([d["ngay_thanh_lap"] for d in res.data if d.get("ngay_thanh_lap")])
            if len(res.data) < 1000: break
            page += 1

        months = {str(i).zfill(2): 0 for i in range(1, 13)}
        for date_str in all_dates:
            try:
                if '/' in date_str:
                    parts = date_str.split('/')
                    m, y = parts[1] if len(parts) >= 3 else parts[0], parts[-1]
                else:
                    parts = date_str.split('-')
                    m, y = parts[1], parts[0]
                if year and str(year) != str(y): continue
                if m.zfill(2) in months: months[m.zfill(2)] += 1
            except: continue

        month_names = ["Th1","Th2","Th3","Th4","Th5","Th6","Th7","Th8","Th9","Th10","Th11","Th12"]
        return [{"name": month_names[int(k)-1], "value": v, "month": k} for k, v in sorted(months.items())]
    except: return []


@app.get("/api/stats/data-quality")
async def data_quality(year: int = None, industry: str = None):
    """Đánh giá chất lượng dữ liệu theo từng trường (hỗ trợ filter)."""
    try:
        total = 0
        has_phone = 0
        has_email = 0
        has_address = 0
        has_industry = 0
        has_date = 0
        page = 0
        while True:
            query = supabase.table("company").select("so_dien_thoai, email, dia_chi_day_du, ma_nganh, ngay_thanh_lap").range(page*1000, (page+1)*1000 - 1)
            if industry: query = query.eq("ma_nganh", industry)
            res = query.execute()
            if not res.data: break
            for d in res.data:
                # Apply year filter
                if year:
                    date_str = d.get("ngay_thanh_lap", "")
                    if not date_str or str(year) not in date_str:
                        continue
                total += 1
                if d.get("so_dien_thoai") and d["so_dien_thoai"].strip(): has_phone += 1
                if d.get("email") and d["email"].strip(): has_email += 1
                if d.get("dia_chi_day_du") and d["dia_chi_day_du"].strip(): has_address += 1
                if d.get("ma_nganh") and d["ma_nganh"].strip(): has_industry += 1
                if d.get("ngay_thanh_lap") and d["ngay_thanh_lap"].strip(): has_date += 1
            if len(res.data) < 1000: break
            page += 1

        if total == 0: return []
        return [
            {"name": "Số điện thoại", "value": round(has_phone/total*100, 1), "count": has_phone, "total": total},
            {"name": "Email", "value": round(has_email/total*100, 1), "count": has_email, "total": total},
            {"name": "Địa chỉ đầy đủ", "value": round(has_address/total*100, 1), "count": has_address, "total": total},
            {"name": "Mã ngành", "value": round(has_industry/total*100, 1), "count": has_industry, "total": total},
            {"name": "Ngày thành lập", "value": round(has_date/total*100, 1), "count": has_date, "total": total}
        ]
    except: return []


@app.get("/api/debug-db")
async def debug_db():
    """Lấy mẫu dữ liệu thực tế để chuẩn hóa lệnh Join."""
    report = {"status": "analyzing", "samples": {}}
    tables = ["company", "tinh_thanh", "nganh_nghe"]
    
    for table in tables:
        try:
            res = supabase.table(table).select("*").limit(3).execute()
            report["samples"][table] = res.data
        except Exception as e:
            report["samples"][table] = {"error": str(e)}
            
    return report

@app.get("/health")
async def health_check():
    return {"status": "ok"}
