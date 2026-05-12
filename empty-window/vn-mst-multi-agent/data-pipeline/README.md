# Data Pipeline 100k MST (HN + TP.HCM)

## Mục tiêu
- Thu thập tối thiểu 100.000 hồ sơ doanh nghiệp theo MST.
- Ưu tiên địa bàn Hà Nội và TP.HCM.
- Chuẩn hóa và de-dup trước khi ghi vào kho dữ liệu.

## Trường dữ liệu chuẩn
- `mst`
- `ten_cong_ty`
- `nam_thanh_lap`
- `sdt`
- `email`
- `dia_chi`
- `nganh_nghe_kinh_doanh`
- `ten_quoc_te`
- `ten_ngan`
- `api_code`, `api_desc`, `updated_at`

## Cài đặt
```bash
cd data-pipeline
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy crawl async
```bash
python crawl_vn_enterprises.py mst_input.txt --workers 20 --output out/vn_enterprises.jsonl
```

Mặc định pipeline:
- Dùng async workers để tăng thông lượng.
- Retry + exponential backoff khi gặp 429.
- Lọc địa chỉ chỉ giữ HN/TP.HCM.
- De-dup theo MST trước khi ghi ra file.
- Fallback đa nguồn theo thứ tự ưu tiên.
- Tạo hàng chờ `manual_review_queue` cho mã thất bại.
- Ghi `quality_report` theo từng nguồn.

## Fallback đa nguồn + báo cáo chất lượng
```bash
python crawl_vn_enterprises.py mst_input.txt \
  --source-order vietqr,esgoo,thongtindoanhnghiep,xinvoice \
  --esgoo-url-template "https://esgoo.net/api-mst/{mst}.htm" \
  --ttdn-url-template "https://thongtindoanhnghiep.co/api/company/{mst}" \
  --xinvoice-url-template "https://api.xinvoice.vn/gdt-api/tax-payer-records/{mst}" \
  --xinvoice-client-id "YOUR_ID" \
  --xinvoice-api-key "YOUR_KEY" \
  --masothue-url-template "https://masothue.com/Search/?q={mst}" \
  --manual-review-file out/manual_review_queue.jsonl \
  --quality-report-file out/quality_report.json
```

Ghi chú:
- Nếu chưa có endpoint GDT/third-party hợp lệ, để trống template và hệ thống sẽ fallback nguồn còn lại.
- `quality_report.json` chứa: `attempt/success/fail` theo nguồn + số trùng bị loại + manual review count.

## Map 3 nguồn chính xác (official3)
Mục tiêu map:
- `Seed`: dữ liệu mở từ `data.gov.vn` (chuẩn bị file MST đầu vào).
- `Verify pháp lý`: `dkkd`.
- `Verify thuế`: `gdt` (qua template endpoint bạn có quyền truy cập).

Chạy profile đã map sẵn:
```bash
python crawl_vn_enterprises.py mst_input.txt \
  --source-profile official3 \
  --gdt-url-template "https://your-gdt-endpoint/{mst}" \
  --output out/vn_enterprises.official3.jsonl \
  --manual-review-file out/manual_review_queue.official3.jsonl \
  --quality-report-file out/quality_report.official3.json
```

Ghi chú:
- Nếu chưa có endpoint `gdt`, profile vẫn chạy nhưng sẽ fallback sang nguồn sau.
- Khi benchmark chất lượng, nên dùng danh sách MST unique để KPI không bị méo.
- Pipeline tự bỏ qua `gdt` nếu URL dạng placeholder (`your-...endpoint`) và tự bỏ qua `xinvoice` nếu thiếu `client-id/api-key`.
- Pipeline tự bỏ qua `dkkd` khi đang dùng default endpoint; dùng `--force-default-dkkd` nếu bạn muốn ép bật.
- Có thể dùng `--insecure-no-verify-ssl` để debug nhanh lỗi chứng thư SSL trong môi trường cục bộ.

## User-Agent / Proxy rotation (tùy chọn)
```bash
python crawl_vn_enterprises.py mst_input.txt \
  --user-agent-file user_agents.txt \
  --proxy-file proxies.txt
```

## Đẩy trực tiếp lên Supabase (PostgreSQL)
1. Chạy schema:
```sql
-- data-pipeline/schema_supabase.sql
```
2. Set env:
```bash
set SUPABASE_DB_URL=postgresql://user:pass@host:5432/postgres
```
3. Chạy:
```bash
python crawl_vn_enterprises.py mst_input.txt --storage supabase --supabase-batch-size 1000
```

## Đẩy trực tiếp lên BigQuery
1. Cấu hình credentials chuẩn GCP (`GOOGLE_APPLICATION_CREDENTIALS`).
2. Chạy:
```bash
python crawl_vn_enterprises.py mst_input.txt \
  --storage bigquery \
  --bigquery-table your-project.your_dataset.vn_enterprises
```

## Ghi chú pháp lý
- Chỉ dùng nguồn dữ liệu và API theo quyền truy cập hợp pháp.
- Không triển khai crawl vượt rào cản hoặc trái điều khoản dịch vụ.

## Crawler compliant (BeautifulSoup + lxml)
File: `crawl_trangvang_compliant.py`

### Ý tưởng 3 tầng
- Tầng danh mục: đọc danh sách URL danh mục từ file txt.
- Tầng phân trang: tự thêm `?page=N` hoặc dùng URL mẫu có `{page}`.
- Tầng chi tiết: vào từng trang doanh nghiệp, bóc trường dữ liệu bằng CSS selectors.

### Chuẩn bị file danh mục
Tạo `category_urls.txt`, ví dụ:
```txt
https://example.com/ha-noi/nganh-van-tai?page={page}
https://example.com/tp-ho-chi-minh/nganh-xay-dung?page={page}
```

### Chạy crawler
```bash
python crawl_trangvang_compliant.py \
  --base-url https://example.com \
  --category-urls category_urls.txt \
  --output out/trangvang_companies.jsonl \
  --checkpoint out/checkpoints/trangvang_checkpoint.json \
  --concurrency 15 \
  --request-delay-ms 120
```

### Ghi thẳng PostgreSQL (dim_company)
1. Chạy schema:
```sql
-- data-pipeline/sql/schema_company.sql
```
2. Chạy crawler + DSN:
```bash
python crawl_trangvang_compliant.py \
  --base-url https://example.com \
  --category-urls category_urls.txt \
  --pg-dsn postgresql://user:pass@host:5432/dbname
```

### Tuỳ biến selectors (khi cấu trúc HTML thay đổi)
```bash
python crawl_trangvang_compliant.py \
  --base-url https://example.com \
  --category-urls category_urls.txt \
  --detail-link-selectors '["a.company_name","a[href*=\"cong-ty\"]"]' \
  --field-selectors-json '{"ten_cong_ty":["h2.company_name"],"dia_chi":[".info_contact .address"]}'
```

### Chạy nhiều batch
```bash
python run_batches.py \
  --base-url https://example.com \
  --batch-dir batches \
  --batch-glob "category_batch_*.txt" \
  --output-dir out/batches \
  --checkpoint-dir out/checkpoints \
  --concurrency 15 \
  --delay-ms 120
```

## Chạy 10 batch MST + tổng hợp KPI cuối
```bash
python run_10_batches.py \
  --batch-dir . \
  --batch-glob "mst_batch_*.txt" \
  --output-dir out/batches \
  --workers 15 \
  --pause-ms 150 \
  --source-retries 1 \
  --source-retry-backoff-ms 120 \
  --rescue-rounds 1 \
  --source-profile official3 \
  --source-order vietqr,esgoo,thongtindoanhnghiep,xinvoice \
  --esgoo-url-template "https://esgoo.net/api-mst/{mst}.htm" \
  --ttdn-url-template "https://thongtindoanhnghiep.co/api/company/{mst}" \
  --xinvoice-url-template "https://api.xinvoice.vn/gdt-api/tax-payer-records/{mst}" \
  --masothue-url-template "https://masothue.com/Search/?q={mst}"
```

Output tong hop:
- `out/batches/final_quality_summary.json`
