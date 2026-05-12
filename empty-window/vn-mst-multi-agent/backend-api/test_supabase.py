"""
test_supabase.py — Kiểm tra kết nối Supabase và schema thực tế.

Schema thực tế:
  - company (PK: ma_so_thue): ten_cong_ty, so_dien_thoai, email, ma_nganh, ma_tinh, xa_phuong_id, so_nha
  - dia_chi (PK: ma_tinh): ten_tinh
  - nganh_nghe (PK: ma_nganh): ten_nganh  (334 records)
  - xa_phuong (PK: id): ten_xa_phuong, ma_tinh  (215 records)
  - v_company: View tổng hợp
  - chat_logs: Lịch sử chat
"""

import os
from database import supabase
from crm_b2b_agent import search_enterprise_database


def test_supabase_integration():
    print("=" * 60)
    print("🚀 BẮT ĐẦU TEST KẾT NỐI SUPABASE")
    print("=" * 60)

    # 1. Kiểm tra Client
    if not supabase:
        print("❌ LỖI: Supabase client chưa được khởi tạo.")
        return

    print("✅ 1. Khởi tạo Supabase client thành công.")

    # 2. Kiểm tra các bảng tồn tại
    tables_to_check = {
        "company": "ma_so_thue, ten_cong_ty, so_dien_thoai, email, ma_nganh, ma_tinh",
        "dia_chi": "ma_tinh, ten_tinh",
        "nganh_nghe": "ma_nganh, ten_nganh",
        "xa_phuong": "id, ten_xa_phuong, ma_tinh",
        "chat_logs": "*",
    }

    print(f"\n🔍 2. Kiểm tra {len(tables_to_check)} bảng trong schema public:")
    print("-" * 50)

    for table, cols in tables_to_check.items():
        try:
            response = supabase.table(table).select(cols).limit(2).execute()
            count = len(response.data) if response.data else 0
            print(f"  ✅ {table:<20} — {count} bản ghi mẫu", end="")

            if count > 0:
                keys = list(response.data[0].keys())
                print(f"  | Cột: {keys}")
            else:
                print("  (trống)")
        except Exception as e:
            print(f"  ❌ {table:<20} — Lỗi: {e}")

    # 3. Kiểm tra bảng company có dữ liệu chưa
    print(f"\n🏢 3. Kiểm tra dữ liệu bảng 'company':")
    print("-" * 50)
    try:
        resp = supabase.table("company").select("ma_so_thue, ten_cong_ty").limit(5).execute()
        if resp.data and len(resp.data) > 0:
            print(f"  ✅ Tìm thấy {len(resp.data)} doanh nghiệp:")
            for row in resp.data:
                print(f"     MST: {row.get('ma_so_thue')} — {row.get('ten_cong_ty')}")

            # 4. Test tool của Agent
            test_mst = resp.data[0].get("ma_so_thue")
            print(f"\n🤖 4. Test Tool 'search_enterprise_database' với MST: {test_mst}")
            print("-" * 50)

            if hasattr(search_enterprise_database, '_run'):
                agent_result = search_enterprise_database._run(test_mst)
            else:
                agent_result = search_enterprise_database.run({"mst_or_name": test_mst})

            print("  Kết quả:")
            print(f"  {agent_result}")
        else:
            print("  ⚠️ Bảng 'company' đang TRỐNG (0 bản ghi).")
            print("  👉 Chạy lệnh: python seed_demo_data.py để thêm dữ liệu demo.")
            print("  👉 Hoặc upload file CSV qua Data Analytics Tool trong Streamlit UI.")
    except Exception as e:
        print(f"  ❌ Lỗi: {e}")

    # 5. Kiểm tra lookup tables
    print(f"\n📋 5. Kiểm tra bảng lookup:")
    print("-" * 50)
    try:
        nganh_resp = supabase.table("nganh_nghe").select("ma_nganh, ten_nganh").limit(3).execute()
        print(f"  nganh_nghe: {len(nganh_resp.data)} mẫu")
        for row in nganh_resp.data:
            print(f"    {row['ma_nganh']}: {row['ten_nganh']}")
    except Exception as e:
        print(f"  ❌ nganh_nghe: {e}")

    try:
        dc_resp = supabase.table("dia_chi").select("*").execute()
        print(f"  dia_chi: {len(dc_resp.data)} records")
        for row in dc_resp.data:
            print(f"    {row['ma_tinh']}: {row['ten_tinh']}")
    except Exception as e:
        print(f"  ❌ dia_chi: {e}")

    try:
        xp_resp = supabase.table("xa_phuong").select("id, ten_xa_phuong, ma_tinh").limit(3).execute()
        print(f"  xa_phuong: {len(xp_resp.data)} mẫu")
        for row in xp_resp.data:
            print(f"    #{row['id']}: {row['ten_xa_phuong']} ({row['ma_tinh']})")
    except Exception as e:
        print(f"  ❌ xa_phuong: {e}")

    print("\n" + "=" * 60)
    print("✅ TEST HOÀN TẤT")
    print("=" * 60)


if __name__ == "__main__":
    test_supabase_integration()
