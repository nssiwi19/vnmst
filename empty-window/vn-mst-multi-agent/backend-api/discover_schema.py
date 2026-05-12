"""Khám phá schema thực tế trên Supabase."""
from database import supabase

# Các bảng có thể tồn tại (dự đoán từ hint + code)
candidate_tables = [
    "nganh_nghe",
    "market_research_dataset",
    "chat_logs",
    "doanh_nghiep",
    "companies",
    "enterprises",
    "tinh_thanh",
    "users",
]

print("=" * 60)
print("🔍 KHÁM PHÁ SCHEMA SUPABASE")
print("=" * 60)

for table in candidate_tables:
    try:
        resp = supabase.table(table).select("*").limit(2).execute()
        count = len(resp.data) if resp.data else 0
        print(f"\n✅ Bảng '{table}' TỒN TẠI — {count} bản ghi mẫu:")
        if resp.data:
            # In tên các cột
            cols = list(resp.data[0].keys())
            print(f"   Cột: {cols}")
            for row in resp.data:
                print(f"   → {row}")
        else:
            print("   (bảng trống)")
    except Exception as e:
        err_msg = str(e)
        if "PGRST205" in err_msg or "Could not find" in err_msg:
            print(f"❌ Bảng '{table}' KHÔNG TỒN TẠI")
        else:
            print(f"⚠️ Bảng '{table}' — lỗi khác: {e}")
