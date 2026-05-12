import type { CrmInsight, CrmPurpose, CrmSegment, VerificationOutput, VietQrBusiness } from "../types";

function baseSegment(data: VietQrBusiness, verification: VerificationOutput | null): CrmSegment {
  if (verification && verification.trustScore < 35) return "Risky";
  const n = `${data.name} ${data.shortName}`.toUpperCase();
  const enterpriseHints =
    /TẬP ĐOÀN|TỔNG CÔNG TY|NGÂN HÀNG|VIETTEL|VINGROUP|VINAMILK|VIETCOMBANK|CTCP.*(SỮA|HÀNG KHÔNG)/;
  if (enterpriseHints.test(n)) return "Enterprise";
  if (/CÔNG TY TNHH MTV|CHI NHÁNH|TNHH/.test(n) && !/HỢP TÁC XÃ/.test(n)) return "SME";
  if (/KHỞI NGHIỆP|STARTUP|INNOVATION|LAB/.test(n)) return "Startup";
  if (verification && verification.riskFlags.some((f) => f.level === "high")) return "Risky";
  return "SME";
}

function purposeNarrative(
  purpose: CrmPurpose,
  segment: CrmSegment,
): { rationale: string[]; adjustments: string[]; steps: string[] } {
  const map: Record<
    CrmPurpose,
    { rationale: string[]; adjustments: string[]; steps: string[] }
  > = {
    kyc: {
      rationale: [
        "KYC: ưu tiên khớp MST – tên – địa chỉ với giấy tờ và hóa đơn mẫu.",
        `Phân khúc ${segment} ảnh hưởng mức độ giấy tờ bổ sung (ĐKKD, UBO).`,
      ],
      adjustments:
        segment === "Enterprise"
          ? ["Yêu cầu xác minh pháp nhân qua kênh chính thức hoặc ngân hàng đối tác."]
          : segment === "Startup"
            ? ["Chấp nhận địa chỉ đăng ký khác địa chỉ giao dịch nếu có hợp đồng thuê."]
            : ["Chuẩn hóa địa chỉ theo VietQR và đối chiếu mã bưu chính."],
      steps: ["Thu thập MST + scan ĐKKD", "Đối chiếu VietQR", "Lưu artifact vào CRM"],
    },
    credit: {
      rationale: [
        "Tín dụng: MST chỉ là tầng dữ liệu mở — cần BCTC và lịch sử nợ.",
        `Nhóm ${segment} quyết định hạn mức khởi điểm đề xuất.`,
      ],
      adjustments:
        segment === "Risky"
          ? ["Hạn chế tự động duyệt; chuyển thẩm định thủ công."]
          : ["Cho phép scoring tự động sơ bộ nếu trust score đủ cao."],
      steps: ["Import VietQR", "Gắn cờ rủi ro", "Gửi sang hệ thống scoring"],
    },
    audit: {
      rationale: [
        "Kiểm toán: dùng MST để khóa đối tượng và đối chiếu chuỗi giao dịch.",
        "Segment giúp chọn mẫu kiểm tra và ngưỡng vật liệu chứng minh.",
      ],
      adjustments:
        segment === "Enterprise"
          ? ["Mở rộng phạm vi kiểm tra các công ty con liên quan."]
          : ["Tập trung kiểm tra dòng tiền và hóa đơn đầu vào."],
      steps: ["Snapshot hồ sơ VietQR", "Lưu hash thời điểm tra cứu", "Đính kèm working paper"],
    },
    partnership: {
      rationale: [
        "Thẩm định hợp tác: cần uy tín thương hiệu và tình trạng hoạt động.",
        "AI phân loại segment để định tần suất review định kỳ.",
      ],
      adjustments:
        segment === "Inactive"
          ? ["Tạm dừng đàm phán cho đến khi xác minh hoạt động."]
          : ["Tiến hành NDA và due diligence theo checklist ngành."],
      steps: ["Chạy pipeline 3 agent", "Lưu báo cáo điều hành", "Phân công owner đối tác"],
    },
  };
  return map[purpose];
}

export function buildCrmInsight(
  data: VietQrBusiness | null,
  verification: VerificationOutput | null,
  purpose: CrmPurpose,
  apiInactive: boolean,
): CrmInsight {
  if (apiInactive || !data) {
    const pn = purposeNarrative(purpose, "Inactive");
    return {
      segment: "Inactive",
      rationale: [
        "Không lấy được hồ sơ hợp lệ từ VietQR (MST sai, gián đoạn API hoặc DN không tồn tại trong nguồn).",
        ...pn.rationale,
      ],
      purposeAdjustments: [
        "Không sử dụng kết quả AI cho quyết định cho đến khi có MST hợp lệ.",
        ...pn.adjustments,
      ],
      suggestedNextSteps: ["Kiểm tra lại MST", "Tra cổng đăng ký doanh nghiệp", ...pn.steps],
    };
  }

  let segment = baseSegment(data, verification);
  const n = data.name.toUpperCase();
  if (/GIẢI THỂ|PHÁ SẢN|TẠM NGỪNG/.test(n)) {
    segment = "Inactive";
  }

  const pn = purposeNarrative(purpose, segment);
  return {
    segment,
    rationale: [
      `Phân khúc gợi ý: ${segment} (dựa trên tên DN, trust score và cờ rủi ro).`,
      ...pn.rationale,
    ],
    purposeAdjustments: pn.adjustments,
    suggestedNextSteps: pn.steps,
  };
}
