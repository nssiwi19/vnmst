export function ArchitectureFlow() {
  return (
    <svg
      className="flow-svg"
      viewBox="0 0 1040 420"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Luồng xử lý MST multi-agent"
    >
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="#64748b" />
        </marker>
      </defs>

      <rect x="12" y="178" width="120" height="56" rx="4" fill="#fff" stroke="#cbd5e1" />
      <text x="72" y="200" textAnchor="middle" fontSize="11" fill="#0f172a" fontWeight="600">
        Nhập MST
      </text>
      <text x="72" y="216" textAnchor="middle" fontSize="9" fill="#64748b">
        UI / CRM
      </text>

      <line x1="132" y1="206" x2="176" y2="206" stroke="#94a3b8" strokeWidth="1.5" markerEnd="url(#arrow)" />

      <rect x="176" y="170" width="130" height="72" rx="4" fill="#eff6ff" stroke="#1d4ed8" />
      <text x="241" y="196" textAnchor="middle" fontSize="11" fill="#1e3a8a" fontWeight="600">
        VietQR API
      </text>
      <text x="241" y="212" textAnchor="middle" fontSize="9" fill="#475569">
        GET /v2/business
      </text>
      <text x="241" y="226" textAnchor="middle" fontSize="8" fill="#64748b">
        api.vietqr.io
      </text>

      <line x1="306" y1="206" x2="346" y2="206" stroke="#94a3b8" strokeWidth="1.5" markerEnd="url(#arrow)" />

      <rect x="346" y="48" width="170" height="88" rx="4" fill="#fff" stroke="#cbd5e1" />
      <text x="431" y="72" textAnchor="middle" fontSize="11" fill="#0f172a" fontWeight="600">
        Agent Research
      </text>
      <text x="431" y="90" textAnchor="middle" fontSize="9" fill="#475569">
        Phân tích hồ sơ
      </text>
      <text x="431" y="106" textAnchor="middle" fontSize="8" fill="#64748b">
        Ngành, địa bàn, hình thức
      </text>
      <text x="431" y="122" textAnchor="middle" fontSize="8" fill="#64748b">
        Input: JSON VietQR
      </text>

      <rect x="346" y="164" width="170" height="88" rx="4" fill="#fff" stroke="#cbd5e1" />
      <text x="431" y="188" textAnchor="middle" fontSize="11" fill="#0f172a" fontWeight="600">
        Agent Report
      </text>
      <text x="431" y="206" textAnchor="middle" fontSize="9" fill="#475569">
        Báo cáo điều hành
      </text>
      <text x="431" y="222" textAnchor="middle" fontSize="8" fill="#64748b">
        Tóm tắt + khuyến nghị
      </text>
      <text x="431" y="238" textAnchor="middle" fontSize="8" fill="#64748b">
        Input: Research
      </text>

      <rect x="346" y="280" width="170" height="88" rx="4" fill="#fff" stroke="#cbd5e1" />
      <text x="431" y="304" textAnchor="middle" fontSize="11" fill="#0f172a" fontWeight="600">
        Agent Verification
      </text>
      <text x="431" y="322" textAnchor="middle" fontSize="9" fill="#475569">
        Rủi ro & tin cậy
      </text>
      <text x="431" y="338" textAnchor="middle" fontSize="8" fill="#64748b">
        Cờ rủi ro, trust score
      </text>
      <text x="431" y="354" textAnchor="middle" fontSize="8" fill="#64748b">
        Input: Research + raw
      </text>

      <path
        d="M 306 206 L 326 206 L 326 92 L 346 92"
        fill="none"
        stroke="#94a3b8"
        strokeWidth="1.5"
        markerEnd="url(#arrow)"
      />
      <path
        d="M 431 136 L 431 156"
        fill="none"
        stroke="#94a3b8"
        strokeWidth="1.5"
        markerEnd="url(#arrow)"
      />
      <path
        d="M 431 252 L 431 272"
        fill="none"
        stroke="#94a3b8"
        strokeWidth="1.5"
        markerEnd="url(#arrow)"
      />

      <line x1="516" y1="212" x2="556" y2="212" stroke="#94a3b8" strokeWidth="1.5" markerEnd="url(#arrow)" />

      <rect x="556" y="146" width="178" height="132" rx="4" fill="#f8fafc" stroke="#64748b" />
      <text x="645" y="174" textAnchor="middle" fontSize="11" fill="#0f172a" fontWeight="600">
        CRM Doanh nghiệp
      </text>
      <text x="645" y="194" textAnchor="middle" fontSize="9" fill="#475569">
        Lưu hồ sơ + segment
      </text>
      <text x="645" y="212" textAnchor="middle" fontSize="9" fill="#475569">
        KYC / Tín dụng / Kiểm toán
      </text>
      <text x="645" y="230" textAnchor="middle" fontSize="9" fill="#475569">
        Thẩm định hợp tác
      </text>
      <text x="645" y="252" textAnchor="middle" fontSize="8" fill="#64748b">
        Enterprise · SME · Startup · Risky · Inactive
      </text>

      <line x1="734" y1="212" x2="776" y2="212" stroke="#94a3b8" strokeWidth="1.5" markerEnd="url(#arrow)" />

      <rect x="776" y="150" width="248" height="124" rx="4" fill="#fff" stroke="#cbd5e1" />
      <text x="900" y="176" textAnchor="middle" fontSize="10" fill="#0f172a" fontWeight="600">
        Storage & Analytics
      </text>
      <text x="786" y="196" fontSize="8" fill="#475569">
        • Supabase/PostgreSQL (upsert theo MST)
      </text>
      <text x="786" y="212" fontSize="8" fill="#475569">
        • BigQuery (phân tích quy mô lớn 100k+)
      </text>
      <text x="786" y="228" fontSize="8" fill="#475569">
        • Chuẩn hóa SĐT/địa chỉ + de-dup MST
      </text>
      <text x="786" y="244" fontSize="8" fill="#475569">
        • Ưu tiên HN/TP.HCM theo bộ lọc địa bàn
      </text>

      <rect x="12" y="24" width="294" height="128" rx="4" fill="#fff" stroke="#cbd5e1" />
      <text x="159" y="48" textAnchor="middle" fontSize="10" fill="#0f172a" fontWeight="600">
        Nguồn dữ liệu tích hợp
      </text>
      <text x="24" y="68" fontSize="8" fill="#475569">
        • Tổng cục Thuế: tracuunnt.gdt.gov.vn / gdt.gov.vn
      </text>
      <text x="24" y="84" fontSize="8" fill="#475569">
        • Cổng ĐKKD quốc gia: dangkykinhdoanh.gov.vn
      </text>
      <text x="24" y="100" fontSize="8" fill="#475569">
        • Thuế HKD: web.gdt.gov.vn/.../hct2
      </text>
      <text x="24" y="116" fontSize="8" fill="#475569">
        • VietQR API (lookup theo MST thời gian thực)
      </text>
      <text x="24" y="132" fontSize="8" fill="#475569">
        • Nguồn mở rộng: MaSoThue theo tỉnh/thành (tuân thủ điều khoản)
      </text>

      <text x="12" y="404" fontSize="12" fill="#0f172a" fontWeight="650">
        Luồng tuần tự
      </text>
      <text x="12" y="418" fontSize="9" fill="#64748b">
        Proxy dev frontend: /vietqr-api → api.vietqr.io
      </text>
    </svg>
  );
}
