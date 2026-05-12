// frontend/src/lib/crm.ts

export const buildCrmInsight = (companyData: any, research: any, report: any, purpose: string) => {
  try {
    // Nếu research hoặc report chưa sẵn sàng, trả về null
    if (!research || !report) return null;

    // Ưu tiên sử dụng insights từ backend nếu có
    if (research.crm_insights) {
       return research.crm_insights;
    }

    // Fallback logic nếu backend không trả về insights sẵn
    const isSales = purpose === 'sales';
    
    return {
      riskLevel: "Thấp",
      suggestedSubject: isSales 
        ? `Đề xuất hợp tác cùng ${companyData.name}` 
        : `Báo cáo thẩm định: ${companyData.name}`,
      suggestedEmail: `Kính gửi Ban lãnh đạo ${companyData.name},\n\nDựa trên phân tích về quy mô và lĩnh vực hoạt động của quý công ty, chúng tôi xin đề xuất các giải pháp tối ưu...`,
      keywords: ["Phân tích", "Chuyên sâu", "Đối tác"]
    };
  } catch (error) {
    console.error("Error in buildCrmInsight:", error);
    return {
      riskLevel: "Không xác định",
      suggestedSubject: "Lỗi xử lý gợi ý",
      suggestedEmail: "Không thể tạo nội dung email lúc này.",
      keywords: ["Error"]
    };
  }
};
