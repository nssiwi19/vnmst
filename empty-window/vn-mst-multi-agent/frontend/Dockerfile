# Sử dụng Node image
FROM node:20-slim

WORKDIR /app

# Cài đặt dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source code
COPY . .

# Mở port Vite mặc định
EXPOSE 5173

# Chạy ở chế độ dev (theo yêu cầu)
CMD ["npm", "run", "dev", "--", "--host"]
