import type {
  ReportOutput,
  ResearchOutput,
  VerificationOutput,
  VietQrBusiness,
  VietQrResponse,
} from "../types";

const DELAY_MS = 380;

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function inferLegalForm(name: string): string {
  const u = name.toUpperCase();
  if (u.includes("CÔNG TY CỔ PHẦN") || u.includes("CTCP")) return "Công ty cổ phần";
  if (u.includes("CÔNG TY TNHH MTV")) return "TNHH một thành viên";
  if (u.includes("CÔNG TY TNHH")) return "TNHH";
  if (u.includes("TỔNG CÔNG TY")) return "Tổng công ty";
  if (u.includes("NGÂN HÀNG")) return "Tổ chức tín dụng";
  if (u.includes("HỢP DANH")) return "Hợp danh";
  if (u.includes("DOANH NGHIỆP TƯ NHÂN") || u.includes("DNTN")) return "Doanh nghiệp tư nhân";
  return "Chưa phân loại rõ (cần tra Cổng thông tin quốc gia về đăng ký doanh nghiệp)";
}

function inferSector(name: string, intl: string): string {
  const blob = `${name} ${intl}`.toLowerCase();
  const rules: [RegExp, string][] = [
    [/ngân hàng|bank|tín dụng/, "Tài chính – ngân hàng"],
    [/viễn thông|telecom|viettel|mobifone|vinaphone/, "Viễn thông – CNTT"],
    [/sữa|dairy|milk|thực phẩm|food/, "Thực phẩm – FMCG"],
    [/bất động sản|real estate|vingroup|vinhomes/, "Bất động sản – hạ tầng"],
    [/ô tô|xe|automotive/, "Cơ khí – ô tô"],
    [/dược|pharma|y tế/, "Dược – y tế"],
  ];
  for (const [re, label] of rules) {
    if (re.test(blob)) return label;
  }
  return "Chung (cần bổ sung ngành từ nguồn đăng ký kinh doanh)";
}

function inferRegion(address: string): string {
  const u = address.toUpperCase();
  const cities = [
    "HÀ NỘI",
    "TP. HỒ CHÍ MINH",
    "HỒ CHÍ MINH",
    "ĐÀ NẴNG",
    "HẢI PHÒNG",
    "CẦN THƠ",
    "THỦ ĐỨC",
  ];
  for (const c of cities) {
    if (u.includes(c)) return c;
  }
  if (address.length > 10) return "Khu vực trong nước (chi tiết từ địa chỉ VietQR)";
  return "Chưa xác định";
}

export async function runResearchAgent(data: VietQrBusiness): Promise<ResearchOutput> {
  await sleep(DELAY_MS);
  const legalForm = inferLegalForm(data.name);
  const sector = inferSector(data.name, data.internationalName);
  const region = inferRegion(data.address);
  const profileBullets = [
    `Tên đăng ký: ${data.name}`,
    `Tên quốc tế: ${data.internationalName || "—"}`,
    `Tên ngắn: ${data.shortName || "—"}`,
    `Địa chỉ trụ sở (VietQR): ${data.address}`,
    `Hình thức pháp lý (suy luận từ tên): ${legalForm}`,
    `Nhóm ngành (heuristic): ${sector}`,
    `Địa bàn ưu tiên: ${region}`,
  ];
  return {
    legalForm,
    inferredSector: sector,
    region,
    profileBullets,
    dataSources: [
      "VietQR API — GET /v2/business/{taxCode} (tên, địa chỉ, tên quốc tế)",
      "Heuristic nội bộ — phân tích pattern tên DN (không thay thế tra cứu pháp lý đầy đủ)",
    ],
  };
}

export async function runReportAgent(
  data: VietQrBusiness,
  research: ResearchOutput,
): Promise<ReportOutput> {
  await sleep(DELAY_MS);
  const executiveSummary = [
    `Doanh nghiệp ${data.shortName || data.name} (MST ${data.id}) được định vị trong nhóm ngành “${research.inferredSector}”, `,
    `hình thức pháp lý gợi ý: ${research.legalForm}. `,
    `Trụ sở ghi nhận tại ${research.region}. `,
    `Khuyến nghị đối chiếu thêm dữ liệu đăng ký kinh doanh và tình trạng hoạt động tại cơ quan thuế trước khi ra quyết định tín dụng hoặc hợp tác chiến lược.`,
  ].join("");

  const recommendations = [
    "Xác thực MST với hóa đơn điện tử / CQT khi dùng cho KYC thanh toán.",
    "Đối chiếu người đại diện pháp luật và vốn điều lệ từ nguồn đăng ký doanh nghiệp.",
    "Với mục đích tín dụng: yêu cầu BCTC hoặc xếp hạng nội bộ bổ sung.",
  ];

  const keyEntities = [
    { label: "MST", value: data.id },
    { label: "Tên hiển thị", value: data.name },
    { label: "Ngành (AI Research)", value: research.inferredSector },
    { label: "Địa bàn", value: research.region },
  ];

  return { executiveSummary, recommendations, keyEntities };
}

function nameConsistencyScore(vn: string, intl: string): { ok: boolean; note: string } {
  if (!intl || intl.length < 3) {
    return { ok: false, note: "Thiếu hoặc quá ngắn tên quốc tế — khó đối chiếu chéo." };
  }
  const a = vn
    .toUpperCase()
    .replace(/[^A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỰỲÝỶỸỴa-zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửựỳýỷỹỵ]/g, "");
  const short = intl.slice(0, 4).toUpperCase();
  if (a.includes(short) || intl.length > 12) {
    return { ok: true, note: "Tên quốc tế và tên trong nước có độ tương thích chấp nhận được." };
  }
  return { ok: false, note: "Độ khớp tên VI/EN thấp — nên kiểm tra thủ công." };
}

export async function runVerificationAgent(
  data: VietQrBusiness,
  research: ResearchOutput,
): Promise<VerificationOutput> {
  await sleep(DELAY_MS);
  const riskFlags: VerificationOutput["riskFlags"] = [];
  const nm = nameConsistencyScore(data.name, data.internationalName);
  if (!nm.ok) {
    riskFlags.push({ level: "medium", message: nm.note });
  }
  if (data.address.length < 25) {
    riskFlags.push({
      level: "low",
      message: "Địa chỉ ngắn — có thể là chi nhánh hoặc dữ liệu rút gọn.",
    });
  }
  const highRiskKw = /mua bán nợ|thanh lý|xuất khẩu lao động|tín dụng đen/i;
  if (highRiskKw.test(data.name)) {
    riskFlags.push({
      level: "high",
      message: "Từ khóa rủi ro trong tên — cần rà soát thêm (quy tắc nội bộ).",
    });
  }

  let trustScore = 72;
  if (nm.ok) trustScore += 10;
  if (data.address.length > 40) trustScore += 6;
  if (research.legalForm.includes("cổ phần") || research.legalForm.includes("Tổng công ty")) {
    trustScore += 4;
  }
  trustScore -= riskFlags.filter((f) => f.level === "high").length * 25;
  trustScore -= riskFlags.filter((f) => f.level === "medium").length * 12;
  trustScore -= riskFlags.filter((f) => f.level === "low").length * 4;
  trustScore = Math.max(18, Math.min(96, Math.round(trustScore)));

  const complianceNotes = [
    "Điểm tin cậy mang tính minh họa pipeline; không thay thế scoring tín dụng.",
    "Luồng này chỉ dùng dữ liệu VietQR + luật heuristic — bổ sung PEP/sanctions theo chính sách nội bộ.",
  ];

  return { trustScore, riskFlags, complianceNotes };
}

export async function runFullPipeline(response: VietQrResponse): Promise<{
  research: ResearchOutput;
  report: ReportOutput;
  verification: VerificationOutput;
}> {
  if (response.code !== "00" || !response.data) {
    throw new Error(response.desc || "Không có dữ liệu doanh nghiệp từ VietQR");
  }
  const data = response.data;
  const research = await runResearchAgent(data);
  const report = await runReportAgent(data, research);
  const verification = await runVerificationAgent(data, research);
  return { research, report, verification };
}
