create table if not exists public.vn_enterprises (
  mst text primary key,
  ten_cong_ty text,
  nam_thanh_lap int,
  sdt text,
  email text,
  dia_chi text,
  nganh_nghe_kinh_doanh text,
  ten_quoc_te text,
  ten_ngan text,
  nguon_chinh text not null default 'vietqr',
  api_code text,
  api_desc text,
  updated_at timestamptz not null default now()
);

create index if not exists idx_vn_enterprises_city_hint
  on public.vn_enterprises using btree (dia_chi);

create index if not exists idx_vn_enterprises_updated_at
  on public.vn_enterprises using btree (updated_at desc);
