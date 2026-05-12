-- Tạo bảng lưu trữ kết quả phân tích
CREATE TABLE IF NOT EXISTS public.company_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id),
    tax_code TEXT NOT NULL,
    company_name TEXT,
    research_data JSONB,
    report_content TEXT,
    crm_insights JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Bật RLS
ALTER TABLE public.company_analysis ENABLE ROW LEVEL SECURITY;

-- Chính sách bảo mật: Người dùng chỉ thấy dữ liệu của chính mình
CREATE POLICY "Users can only see their own analysis" 
ON public.company_analysis FOR SELECT 
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own analysis" 
ON public.company_analysis FOR INSERT 
WITH CHECK (auth.uid() = user_id);
