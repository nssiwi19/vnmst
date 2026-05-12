import type { SampleCompany } from "../types";

/** Mẫu MST công khai thường dùng tra cứu; có thể thay đổi theo dữ liệu VietQR. */
export const SAMPLE_COMPANIES: SampleCompany[] = [
  {
    id: "viettel",
    label: "Tập đoàn Công nghiệp Viễn thông Quân đội (Viettel)",
    mst: "0100109106",
    note: "Doanh nghiệp nhà nước / tập đoàn",
  },
  {
    id: "vietcombank",
    label: "Ngân hàng TMCP Ngoại thương Việt Nam (Vietcombank)",
    mst: "0102126770",
    note: "Ngân hàng niêm yết",
  },
  {
    id: "vingroup",
    label: "Tập đoàn Vingroup",
    mst: "0101241596",
    note: "Holding đa ngành",
  },
  {
    id: "vinamilk",
    label: "Công ty CP Sữa Việt Nam (Vinamilk)",
    mst: "0300588569",
    note: "DN CP lớn",
  },
];
