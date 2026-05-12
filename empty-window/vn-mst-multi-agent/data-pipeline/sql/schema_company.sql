create table if not exists public.dim_company (
  mst text primary key,
  ten_cong_ty text,
  nam_thanh_lap int,
  sdt text,
  email text,
  dia_chi text,
  nganh_nghe_kinh_doanh text,
  nguon_url text,
  updated_at timestamptz not null default now()
);

create index if not exists idx_dim_company_city
  on public.dim_company using btree (dia_chi);

create index if not exists idx_dim_company_sector
  on public.dim_company using btree (nganh_nghe_kinh_doanh);

create index if not exists idx_dim_company_updated_at
  on public.dim_company using btree (updated_at desc);
