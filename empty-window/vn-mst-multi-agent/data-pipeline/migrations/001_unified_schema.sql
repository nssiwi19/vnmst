-- File: migrations/001_unified_schema.sql
-- Unified Schema for Elite-DA Project (Đã đồng bộ thực tế)

-- 0. Dọn dẹp
DROP VIEW IF EXISTS public.v_company CASCADE;
DROP TABLE IF EXISTS public.company CASCADE;
DROP TABLE IF EXISTS public.xa_phuong CASCADE;
DROP TABLE IF EXISTS public.nganh_nghe CASCADE;
DROP TABLE IF EXISTS public.tinh_thanh CASCADE;

-- 1. Bảng lookup: tinh_thanh
CREATE TABLE public.tinh_thanh (
  ma_tinh TEXT PRIMARY KEY,
  ten_tinh TEXT NOT NULL
);

-- 2. Bảng lookup: nganh_nghe
CREATE TABLE public.nganh_nghe (
  ma_nganh TEXT PRIMARY KEY,
  ten_nganh TEXT NOT NULL
);

-- 3. Bảng lookup: xa_phuong
CREATE TABLE public.xa_phuong (
  ma_phuong TEXT PRIMARY KEY,
  ten_xa_phuong TEXT NOT NULL,
  ma_tinh TEXT REFERENCES public.tinh_thanh(ma_tinh)
);

-- Bảng company (Canonical)
CREATE TABLE public.company (
  ma_so_thue      TEXT PRIMARY KEY,
  ten_cong_ty     TEXT NOT NULL,
  ngay_thanh_lap  TEXT,
  so_dien_thoai   TEXT,
  email           TEXT,
  ma_nganh        TEXT NOT NULL REFERENCES public.nganh_nghe(ma_nganh),
  ma_phuong       TEXT NOT NULL REFERENCES public.xa_phuong(ma_phuong),
  so_nha          TEXT,
  dia_chi_day_du  TEXT NOT NULL,
  nguon           TEXT,
  created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_company_fts ON public.company USING gin(to_tsvector('simple', ten_cong_ty));
CREATE INDEX IF NOT EXISTS idx_company_mst ON public.company(ma_so_thue);

-- Trigger tự động cập nhật updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER company_updated_at
  BEFORE UPDATE ON public.company
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Tạo View v_company (Dùng cho Backend)
CREATE VIEW public.v_company AS
SELECT
  c.ma_so_thue,
  c.ten_cong_ty,
  c.ngay_thanh_lap,
  c.so_dien_thoai,
  c.email,
  c.ma_nganh,
  n.ten_nganh,
  c.ma_phuong,
  x.ten_xa_phuong,
  x.ma_tinh,
  t.ten_tinh,
  c.so_nha,
  c.dia_chi_day_du,
  c.nguon,
  c.created_at,
  c.updated_at
FROM public.company c
LEFT JOIN public.nganh_nghe n ON c.ma_nganh = n.ma_nganh
LEFT JOIN public.xa_phuong x ON c.ma_phuong = x.ma_phuong
LEFT JOIN public.tinh_thanh t ON x.ma_tinh = t.ma_tinh;
