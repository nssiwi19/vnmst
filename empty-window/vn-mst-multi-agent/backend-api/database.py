import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase_client() -> Client:
    """
    Khởi tạo và trả về đối tượng Supabase Client.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables.")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Khởi tạo client dùng chung
try:
    supabase: Client = get_supabase_client()
except Exception as e:
    print(f"Warning: Không thể khởi tạo Supabase client. Chi tiết lỗi: {e}")
    supabase = None
