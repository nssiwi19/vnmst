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

# Mở port mặc định của Hugging Face
EXPOSE 7860

# Lệnh kiểm tra sức khỏe của Streamlit container
HEALTHCHECK CMD curl --fail http://localhost:7860/_stcore/health

# Chạy ứng dụng
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
