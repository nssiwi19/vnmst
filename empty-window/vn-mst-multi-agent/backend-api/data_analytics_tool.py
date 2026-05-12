import streamlit as st
import pandas as pd
import io
from typing import Dict, List

try:
    from database import supabase
except ImportError:
    supabase = None

SHARED_TABLE_NAME = "company"


def _normalize_uploaded_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa tên cột upload về schema của bảng 'company' trên Supabase."""
    if df.empty:
        return df

    # Map từ tên cột linh hoạt sang schema của bảng 'company'
    column_map: Dict[str, str] = {
        "MST": "ma_so_thue",
        "Mã số thuế": "ma_so_thue",
        "ma_so_thue": "ma_so_thue",
        "Tên công ty": "ten_cong_ty",
        "ten_cong_ty": "ten_cong_ty",
        "SĐT": "so_dien_thoai",
        "Số điện thoại": "so_dien_thoai",
        "so_dien_thoai": "so_dien_thoai",
        "Email": "email",
        "email": "email",
        "Mã ngành": "ma_nganh",
        "ma_nganh": "ma_nganh",
        "Mã tỉnh": "ma_tinh",
        "ma_tinh": "ma_tinh",
        "Địa chỉ": "so_nha",
        "so_nha": "so_nha",
    }

    renamed = df.rename(columns={col: column_map.get(col, col) for col in df.columns})
    required_cols = [
        "ma_so_thue",
        "ten_cong_ty",
        "so_dien_thoai",
        "email",
        "ma_nganh",
        "ma_tinh",
        "so_nha"
    ]

    for col in required_cols:
        if col not in renamed.columns:
            renamed[col] = None

    normalized = renamed[required_cols].copy()
    normalized["ma_so_thue"] = normalized["ma_so_thue"].astype(str).str.strip()
    normalized = normalized[normalized["ma_so_thue"].notna() & (normalized["ma_so_thue"] != "")]
    normalized = normalized.drop_duplicates(subset=["ma_so_thue"], keep="last")
    return normalized


def upsert_uploaded_data_to_supabase(df: pd.DataFrame) -> int:
    """
    Upsert dữ liệu upload vào bảng 'company'.
    """
    if not supabase:
        raise ValueError("Supabase chưa được khởi tạo.")

    normalized = _normalize_uploaded_dataframe(df)
    if normalized.empty:
        return 0

    records = normalized.where(pd.notnull(normalized), None).to_dict("records")
    chunk_size = 500
    for i in range(0, len(records), chunk_size):
        chunk: List[dict] = records[i:i + chunk_size]
        supabase.table(SHARED_TABLE_NAME).upsert(chunk, on_conflict="ma_so_thue").execute()
    return len(records)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_all_enterprises_from_supabase():
    """Hàm tải dữ liệu từ Supabase và làm giàu thông tin từ bảng lookup."""
    if not supabase:
        return pd.DataFrame()
    
    all_data = []
    page_size = 1000
    start = 0
    
    while True:
        response = supabase.table(SHARED_TABLE_NAME).select("*").range(start, start + page_size - 1).execute()
        data = response.data
        if not data:
            break
        all_data.extend(data)
        if len(data) < page_size:
            break
        start += page_size
        if start >= 100000:
            break
            
    df = pd.DataFrame(all_data)
    if not df.empty:
        # Làm giàu dữ liệu (Lookup)
        # 1. Tỉnh thành
        try:
            tinh_resp = supabase.table("dia_chi").select("ma_tinh, ten_tinh").execute()
            if tinh_resp.data:
                tinh_dict = {row["ma_tinh"]: row["ten_tinh"] for row in tinh_resp.data}
                df["Thành phố"] = df["ma_tinh"].map(tinh_dict).fillna(df["ma_tinh"])
        except: pass

        # 2. Ngành nghề (Chỉ lấy các mã xuất hiện trong df để tối ưu nếu cần, nhưng ở đây lấy all samples)
        try:
            nganh_resp = supabase.table("nganh_nghe").select("ma_nganh, ten_nganh").execute()
            if nganh_resp.data:
                nganh_dict = {row["ma_nganh"]: row["ten_nganh"] for row in nganh_resp.data}
                df["Ngành nghề"] = df["ma_nganh"].map(nganh_dict).fillna(df["ma_nganh"])
        except: pass

        # Đổi tên cột cho UI
        df = df.rename(columns={
            "ma_so_thue": "MST",
            "ten_cong_ty": "Tên công ty",
            "so_dien_thoai": "SĐT",
            "email": "Email",
            "so_nha": "Địa chỉ",
        })

    return df


def get_mock_data():
    """Dữ liệu mẫu khớp với schema mới."""
    data = {
        "MST": ["0101248141", "0314456789", "0300588569", "0100109106", "0301444753", "0311813220", "0108342468"],
        "Tên công ty": ["Công ty TNHH Phần mềm FPT", "Công ty CP Bán lẻ Minh Tuấn", "Vinamilk", "Vingroup", "PNJ", "Thế Giới Di Động", "Shopee"],
        "Thành phố": ["Hà Nội", "TP. Hồ Chí Minh", "TP. Hồ Chí Minh", "Hà Nội", "TP. Hồ Chí Minh", "TP. Hồ Chí Minh", "Hà Nội"],
        "Ngành nghề": ["Công nghệ", "Bán lẻ", "Thực phẩm", "Bất động sản", "Trang sức", "Bán lẻ", "TMĐT"],
        "SĐT": ["024 7300 7300", "028 3823 4567", "028 5415 5555", "024 3974 9999", "028 3995 1703", "028 3622 0792", "1900 6907"],
    }
    return pd.DataFrame(data)

def render_analytics_dashboard():
    st.markdown("### 📊 Data Analytics Dashboard (Enterprise Records)")
    st.write("Phân tích danh sách doanh nghiệp kết nối trực tiếp với Supabase.")

    col_up1, col_up2 = st.columns([1, 1])
    with col_up1:
        uploaded_file = st.file_uploader("Tải lên danh sách (CSV/Excel)", type=["csv", "xlsx"])
    with col_up2:
        st.write("Đồng bộ trực tiếp từ Database")
        use_supabase = st.button("⬇️ Tải toàn bộ dữ liệu từ Supabase", type="primary", use_container_width=True)

    df = pd.DataFrame()
    if use_supabase:
        if not supabase:
            st.error("Chưa kết nối được Supabase.")
            df = get_mock_data()
        else:
            with st.spinner("Đang tải dữ liệu..."):
                df = fetch_all_enterprises_from_supabase()
            if not df.empty:
                st.success(f"✅ Đã tải {len(df):,} doanh nghiệp!")
            else:
                st.warning("Database đang trống.")
                df = get_mock_data()
    elif uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            if supabase:
                with st.spinner("Đang lưu vào Supabase..."):
                    upserted_count = upsert_uploaded_data_to_supabase(df)
                    fetch_all_enterprises_from_supabase.clear()
                st.success(f"✅ Đã lưu {upserted_count} bản ghi.")
                df = fetch_all_enterprises_from_supabase()
        except Exception as e:
            st.error(f"Lỗi: {e}")
            df = get_mock_data()
    else:
        df = get_mock_data()

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tổng số DN", f"{len(df):,}")
    if "Thành phố" in df.columns:
        col2.metric("Số Tỉnh/Thành", f"{df['Thành phố'].nunique()}")
    if "Ngành nghề" in df.columns:
        col3.metric("Số Ngành nghề", f"{df['Ngành nghề'].nunique()}")
    col4.metric("Dữ liệu thiếu", f"{df.isnull().sum().sum()}")

    st.divider()
    st.markdown("#### 📈 Trực quan hóa")
    c1, c2 = st.columns(2)
    with c1:
        if "Thành phố" in df.columns:
            st.write("**Phân bố theo Tỉnh/Thành**")
            st.bar_chart(df["Thành phố"].value_counts(), color="#FF6B6B")
    with c2:
        if "Ngành nghề" in df.columns:
            st.write("**Phân bố theo Ngành nghề**")
            st.bar_chart(df["Ngành nghề"].value_counts(), color="#4ECDC4")

    st.divider()
    st.markdown("#### 🔍 Tìm kiếm & Xuất bản")
    query = st.text_input("Tìm kiếm doanh nghiệp:", placeholder="VD: FPT, 0101248141...")
    
    filtered = df.copy()
    if query:
        mask = filtered.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)
        filtered = filtered[mask]
        st.success(f"🎯 Tìm thấy {len(filtered)} kết quả.")
    
    st.dataframe(filtered, use_container_width=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        filtered.to_excel(writer, index=False, sheet_name='Data')
    st.download_button("📥 Tải Excel", buffer.getvalue(), "B2B_Data.xlsx", type="primary")
