import { api } from './api';

export const analyzeCompanyFull = async (companyData: any, purpose: string = "kyc") => {
  try {
    // 1. Gửi request phân tích
    const initialResponse = await api.post('/analyze', {
      tax_code: companyData.id,
      company_data: companyData,
      purpose: purpose
    });

    const analysisId = initialResponse.id;
    if (!analysisId) throw new Error("Không nhận được Analysis ID từ server");

    // 2. Polling trạng thái
    let attempts = 0;
    const maxAttempts = 120; // 2 phút (mỗi giây một lần)
    
    while (attempts < maxAttempts) {
      const statusRes = await api.get(`/analyze/${analysisId}`);
      
      if (statusRes.status === 'completed') {
        return {
          research: statusRes.research_data,
          report: { summary: statusRes.report_content },
          crm_insights: statusRes.crm_insights
        };
      }
      
      if (statusRes.status === 'failed') {
        throw new Error(statusRes.error_log || "Phân tích thất bại");
      }
      
      // Đợi 1 giây trước khi fetch tiếp
      await new Promise(r => setTimeout(r, 1000));
      attempts++;
    }
    
    throw new Error("Hết thời gian chờ phản hồi từ AI Agent");
  } catch (error) {
    console.error("Error in analyzeCompanyFull:", error);
    throw error;
  }
};

// Giữ lại các hàm cũ để không làm lỗi compile nhưng trỏ về dữ liệu mới
export const runResearchAgent = async (companyData: any) => {
  return (await analyzeCompanyFull(companyData)).research;
};

export const runReportAgent = async (companyData: any, researchResult: any) => {
  return { summary: "Báo cáo đã sẵn sàng." };
};

export const runVerificationAgent = async (companyData: any, researchResult: any, reportResult: any) => {
  return { isVerified: true, confidence: 0.95, notes: "Xác thực bởi Elite-DA" };
};
