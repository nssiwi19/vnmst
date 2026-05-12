-- File: migrations/002_rls_policies.sql
-- Row Level Security (RLS) Policies

-- 1. Bật RLS cho tất cả bảng
ALTER TABLE public.company ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tinh_thanh ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nganh_nghe ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.xa_phuong ENABLE ROW LEVEL SECURITY;

-- 2. Policy cho bảng lookup (đọc công khai, chỉ service role mới ghi)
DROP POLICY IF EXISTS "tinh_thanh: public read" ON public.tinh_thanh;
CREATE POLICY "tinh_thanh: public read" ON public.tinh_thanh FOR SELECT USING (true);

DROP POLICY IF EXISTS "nganh_nghe: public read" ON public.nganh_nghe;
CREATE POLICY "nganh_nghe: public read" ON public.nganh_nghe FOR SELECT USING (true);

DROP POLICY IF EXISTS "xa_phuong: public read" ON public.xa_phuong;
CREATE POLICY "xa_phuong: public read" ON public.xa_phuong FOR SELECT USING (true);

-- 3. Policy cho company (service role full access, anon chỉ đọc)
DROP POLICY IF EXISTS "company: service role full access" ON public.company;
CREATE POLICY "company: service role full access" ON public.company FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "company: anon read" ON public.company;
CREATE POLICY "company: anon read" ON public.company FOR SELECT USING (true);
