"""
seed_demo_data.py — Thêm dữ liệu demo vào bảng company trên Supabase.

Bảng company hiện đang trống. Script này sẽ insert 7 doanh nghiệp mẫu
để demo CRM B2B Agent có thể tra cứu và phản hồi email.

Schema: company(ma_so_thue PK, ten_cong_ty, so_dien_thoai, email, ma_nganh, ma_tinh, xa_phuong_id, so_nha)
"""

from database import supabase

DEMO_COMPANIES = [
    {
        "ma_so_thue": "0101248141",
        "ten_cong_ty": "Công ty TNHH Phần mềm Công nghệ FPT",
        "so_dien_thoai": "024 7300 7300",
        "email": "contact@fpt.com.vn",
        "ma_nganh": "6201",  # Lập trình máy vi tính
        "ma_tinh": "HN",
        "xa_phuong_id": None,
        "so_nha": "Lô B2, Phường Dịch Vọng Hậu, Quận Cầu Giấy",
    },
    {
        "ma_so_thue": "0314456789",
        "ten_cong_ty": "Công ty Cổ phần Bán lẻ Minh Tuấn",
        "so_dien_thoai": "028 3823 4567",
        "email": "info@minhtuan.vn",
        "ma_nganh": "4719",  # Bán lẻ khác trong cửa hàng
        "ma_tinh": "HCM",
        "xa_phuong_id": None,
        "so_nha": "123 Nguyễn Huệ, Quận 1",
    },
    {
        "ma_so_thue": "0300588569",
        "ten_cong_ty": "Công ty Cổ phần Sữa Việt Nam (Vinamilk)",
        "so_dien_thoai": "028 5415 5555",
        "email": "vinamilk@vinamilk.com.vn",
        "ma_nganh": "1050",  # Chế biến sữa
        "ma_tinh": "HCM",
        "xa_phuong_id": None,
        "so_nha": "10 Tân Trào, Quận 7",
    },
    {
        "ma_so_thue": "0100109106",
        "ten_cong_ty": "Tập đoàn Vingroup",
        "so_dien_thoai": "024 3974 9999",
        "email": "info@vingroup.net",
        "ma_nganh": "6810",  # Kinh doanh bất động sản
        "ma_tinh": "HN",
        "xa_phuong_id": None,
        "so_nha": "Số 7, Đường Bằng Lăng 1, Vinhomes Riverside",
    },
    {
        "ma_so_thue": "0301444753",
        "ten_cong_ty": "Công ty Vàng bạc đá quý Phú Nhuận PNJ",
        "so_dien_thoai": "028 3995 1703",
        "email": "cskh@pnj.com.vn",
        "ma_nganh": "4773",  # Bán lẻ hàng mới khác
        "ma_tinh": "HCM",
        "xa_phuong_id": None,
        "so_nha": "170E Phan Đăng Lưu, Quận Phú Nhuận",
    },
    {
        "ma_so_thue": "0311813220",
        "ten_cong_ty": "Công ty Cổ phần Thế Giới Di Động",
        "so_dien_thoai": "028 3622 0792",
        "email": "info@thegioididong.com",
        "ma_nganh": "4741",  # Bán lẻ máy vi tính, thiết bị ngoại vi
        "ma_tinh": "HCM",
        "xa_phuong_id": None,
        "so_nha": "128 Trần Quang Khải, Quận 1",
    },
    {
        "ma_so_thue": "0108342468",
        "ten_cong_ty": "Công ty TNHH Shopee",
        "so_dien_thoai": "1900 6907",
        "email": "support@shopee.vn",
        "ma_nganh": "4791",  # Bán lẻ theo đơn đặt hàng qua internet
        "ma_tinh": "HN",
        "xa_phuong_id": None,
        "so_nha": "Tầng 18, Capital Place, 29 Liễu Giai, Ba Đình",
    },
]


def seed_companies():
    if not supabase:
        print("❌ Supabase chưa kết nối. Kiểm tra .env")
        return

    print("=" * 60)
    print("🌱 SEEDING DỮ LIỆU DEMO VÀO BẢNG 'company'")
    print("=" * 60)

    # Kiểm tra bảng đã có dữ liệu chưa
    existing = supabase.table("company").select("ma_so_thue").limit(1).execute()
    if existing.data and len(existing.data) > 0:
        print(f"⚠️  Bảng 'company' đã có dữ liệu ({len(existing.data)}+ records).")
        confirm = input("Bạn có muốn upsert thêm dữ liệu demo? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Đã hủy.")
            return

    try:
        # Upsert: nếu MST đã tồn tại → update, nếu chưa → insert
        response = supabase.table("company").upsert(
            DEMO_COMPANIES,
            on_conflict="ma_so_thue"
        ).execute()

        print(f"\n✅ Đã upsert {len(DEMO_COMPANIES)} doanh nghiệp demo:")
        for c in DEMO_COMPANIES:
            print(f"   MST: {c['ma_so_thue']} — {c['ten_cong_ty']}")

        print(f"\n🔍 Xác nhận: Đọc lại từ database...")
        verify = supabase.table("company").select("ma_so_thue, ten_cong_ty").execute()
        print(f"   Tổng số bản ghi trong 'company': {len(verify.data)}")

    except Exception as e:
        print(f"❌ Lỗi khi seed: {e}")


if __name__ == "__main__":
    seed_companies()
