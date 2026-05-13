# Sử dụng Python image nhẹ
FROM python:3.12-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết (nếu có) cho việc build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements và cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ source code vào container
COPY . .

# Mở port mặc định của FastAPI
EXPOSE 8000

# Lệnh kiểm tra sức khỏe
HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

# Chạy ứng dụng FastAPI
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
