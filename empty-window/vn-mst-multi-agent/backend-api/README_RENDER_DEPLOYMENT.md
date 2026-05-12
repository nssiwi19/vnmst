# Hướng dẫn Deploy lên Render.com (Bằng Docker)

Lựa chọn Render.com kết hợp với `Dockerfile` đã có sẵn là phương án tối ưu nhất cho hệ thống CrewAI của bạn. Quá trình này hoàn toàn tự động và miễn phí/chi phí rất thấp.

## Bước 1: Đưa Code Lên GitHub
Render cần lấy mã nguồn của bạn từ GitHub.
1. Tạo một repository mới trên [GitHub](https://github.com/).
2. Mở terminal tại thư mục dự án trên máy tính (`c:\Users\Admin\.cursor\projects\empty-window\CRM`).
3. Chạy các lệnh sau:
   ```bash
   git init
   git add .
   git commit -m "First commit for deployment"
   git branch -M main
   git remote add origin https://github.com/<tên-user-của-bạn>/<tên-repo>.git
   git push -u origin main
   ```
*(Lưu ý: Git đã bỏ qua file `.env` nhờ file `.gitignore`, hãy chắc chắn file `.env` chứa API Key của bạn không bị đẩy lên mạng).*

## Bước 2: Khởi tạo Web Service trên Render
1. Truy cập [Render.com](https://render.com/) và tạo tài khoản (có thể đăng nhập thẳng bằng GitHub).
2. Click vào nút **New +** ở góc phải trên cùng và chọn **Web Service**.
3. Chọn tùy chọn **Build and deploy from a Git repository**.
4. Chọn Repository bạn vừa tạo ở Bước 1. (Bạn có thể cần cấp quyền cho Render truy cập repo của bạn).

## Bước 3: Cấu hình Môi trường Deployment
Tại màn hình cấu hình Web Service của Render, thiết lập như sau:
- **Name**: Nhập tên tùy ý (vd: `crm-b2b-agent`).
- **Region**: Chọn vùng máy chủ gần Việt Nam nhất (thường là `Singapore`).
- **Branch**: `main`
- **Environment**: Render sẽ tự động nhận diện `Docker` nhờ file `Dockerfile` của bạn. Đảm bảo mục này là `Docker`.
- **Instance Type**: Nếu muốn test, bạn có thể chọn gói **Free** (Miễn phí). Tuy nhiên, vì CrewAI khá ngốn RAM, nếu ứng dụng chạy bị sập, bạn nên cân nhắc nâng lên gói Starter (7$/tháng).

## Bước 4: Thêm Biến Môi Trường (API Keys)
Kéo xuống mục **Environment Variables** (hoặc **Advanced** -> **Add Environment Variable**):
- Cột Key: Nhập `GROQ_API_KEY`
- Cột Value: Nhập chuỗi API Key thật của bạn (bắt đầu bằng `gsk_...`)

## Bước 5: Deploy
1. Bấm nút **Create Web Service** ở dưới cùng.
2. Render sẽ bắt đầu đọc file `Dockerfile`, tải các thư viện trong `requirements.txt` và khởi động Streamlit. Quá trình này mất khoảng 2-5 phút.
3. Khi bạn thấy dòng chữ `Your service is live 🎉` trên màn hình log, nghĩa là app đã chạy thành công!
4. Truy cập ứng dụng qua đường link Render cung cấp ở góc trên bên trái (vd: `https://crm-b2b-agent.onrender.com`).

---
**💡 Mẹo cho quá trình vận hành sau này:**
Mỗi khi bạn sửa code trên máy tính của mình (ví dụ cập nhật code cho Giai đoạn 2), bạn chỉ cần gõ lệnh `git push`. Render sẽ tự động nhận biết có code mới và tự động build lại hệ thống cho bạn mà không cần phải vào trang web của Render thao tác lại!
