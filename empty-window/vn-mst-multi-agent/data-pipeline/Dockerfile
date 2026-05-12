# Sử dụng Python image
FROM python:3.12-slim

WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết cho Chrome/DrissionPage
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Lệnh mặc định là chạy crawler chính
CMD ["python", "crawler_v1.py"]
