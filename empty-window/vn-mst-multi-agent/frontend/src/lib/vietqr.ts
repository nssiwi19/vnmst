// frontend/src/lib/vietqr.ts

export const normalizeMst = (mst: string) => mst.replace(/\D/g, '');

export const fetchBusinessByTaxCode = async (mst: string) => {
  const cleanMst = normalizeMst(mst);
  
  try {
    // Thử gọi API VietQR
    const response = await fetch(`https://api.vietqr.io/v2/business/${cleanMst}`);
    
    if (response.status === 429) {
      console.warn("VietQR API rate limited. Using fallback.");
      return {
        code: "429",
        desc: "API VietQR đang quá tải. Hệ thống sẽ sử dụng dữ liệu dự phòng.",
        data: {
          name: "Doanh nghiệp (Dữ liệu dự phòng)",
          id: cleanMst,
          address: "Địa chỉ đang cập nhật..."
        }
      };
    }

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error("VietQR Fetch Error:", error);
    // Trả về dữ liệu tối thiểu để không làm dừng pipeline AI
    return {
      code: "00", // Giả lập thành công để đi tiếp
      desc: "Sử dụng dữ liệu tối thiểu do lỗi kết nối API",
      data: {
        name: "Doanh nghiệp (MST: " + cleanMst + ")",
        id: cleanMst,
        address: "Không thể lấy địa chỉ tự động"
      }
    };
  }
};
