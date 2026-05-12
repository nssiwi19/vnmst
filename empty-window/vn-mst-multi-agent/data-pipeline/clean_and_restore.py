import pandas as pd
import os
from supabase import create_client
from dotenv import load_dotenv
import math

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Use Service Role Key for high-speed insert

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Missing SUPABASE_URL or SUPABASE_KEY in .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CSV_PATH = "data/listing.csv"

# Mapping đơn giản cho Tỉnh/Thành từ CSV sang mã số (ma_tinh)
PROVINCE_MAP = {
    "Ha Noi": "01",
    "Hồ Chí Minh": "79",
    "Ho Chi Minh": "79",
    "Da Nang": "48",
    "Binh Duong": "74",
    "Dong Nai": "75",
    "Long An": "80"
}

def clean_and_restore():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found.")
        return

    print(f"--- Đang đọc dữ liệu từ {CSV_PATH} ---")
    df = pd.read_csv(CSV_PATH)
    
    # 1. Loại bỏ bản ghi trùng MST
    df = df.drop_duplicates(subset=["ma_so_thue"])
    
    # 2. Xử lý Lookup Tables (Tỉnh Thành & Ngành Nghề)
    print("--- Đang chuẩn hóa bảng Lookup ---")
    
    # Đảm bảo bảng dia_chi có dữ liệu cơ bản
    provinces = []
    for name, code in PROVINCE_MAP.items():
        provinces.append({"ma_tinh": code, "ten_tinh": name})
    
    try:
        supabase.table("dia_chi").upsert(provinces).execute()
        print("Done: Cập nhật bảng dia_chi")
    except Exception as e:
        print(f"Warning: Không thể upsert dia_chi: {e}")

    # Thu thập ngành nghề duy nhất (nếu có)
    if "nganh_nghe" in df.columns:
        unique_nganh = df["nganh_nghe"].dropna().unique()
        nganh_data = []
        for n in unique_nganh:
            # Giả định ma_nganh là 5 ký tự đầu hoặc hash nếu không có mã
            n_str = str(n).strip()
            if n_str:
                nganh_data.append({"ma_nganh": n_str[:50], "ten_nganh": n_str})
        
        if nganh_data:
            try:
                # Chia nhỏ để upload nganh_nghe nếu quá nhiều
                for i in range(0, len(nganh_data), 100):
                    supabase.table("nganh_nghe").upsert(nganh_data[i:i+100]).execute()
                print("Done: Cập nhật bảng nganh_nghe")
            except Exception as e:
                print(f"Warning: Không thể upsert nganh_nghe: {e}")

    # 3. Chuẩn hóa dữ liệu Company
    print("--- Đang làm sạch dữ liệu Doanh nghiệp ---")
    
    companies = []
    for _, row in df.iterrows():
        # Map tỉnh thành
        tinh_raw = row.get("tinh_thanh", "")
        ma_tinh = PROVINCE_MAP.get(tinh_raw, None)
        
        # Làm sạch chuỗi
        ten = str(row.get("ten_cong_ty", "")).strip()
        mst = str(row.get("ma_so_thue", "")).strip()
        diachi = str(row.get("dia_chi", "")).strip()
        email = str(row.get("email", "")).strip() if pd.notna(row.get("email")) else None
        sdt = str(row.get("so_dien_thoai", "")).strip() if pd.notna(row.get("so_dien_thoai")) else None
        ma_nganh = str(row.get("nganh_nghe", ""))[:50] if pd.notna(row.get("nganh_nghe")) else None
        
        if not mst or len(mst) < 8: continue # Bỏ qua MST không hợp lệ

        companies.append({
            "ma_so_thue": mst,
            "ten_cong_ty": ten,
            "so_dien_thoai": sdt,
            "email": email,
            "ma_nganh": ma_nganh,
            "ma_tinh": ma_tinh,
            "so_nha": diachi, # Tạm thời để full địa chỉ vào so_nha nếu chưa tách được
            "nguon": "restore_from_csv"
        })

    # 4. Upload theo Batch
    batch_size = 500
    total = len(companies)
    print(f"--- Đang nạp {total} doanh nghiệp vào Supabase (Batch size: {batch_size}) ---")
    
    for i in range(0, total, batch_size):
        batch = companies[i : i + batch_size]
        try:
            supabase.table("company").upsert(batch).execute()
            print(f"Progress: {min(i + batch_size, total)}/{total}")
        except Exception as e:
            print(f"Error at batch {i}: {e}")

    print("--- HOÀN TẤT PHỤC HỒI DỮ LIỆU ---")

if __name__ == "__main__":
    clean_and_restore()
