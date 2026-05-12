-- File: migrations/003_auth_columns.sql
-- 1. Thêm cột user_id để quản lý Chat Logs theo từng User
ALTER TABLE public.chat_logs 
  ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

-- 2. Bật RLS và tạo Policy bảo mật
ALTER TABLE public.chat_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "chat_logs: user owns their logs" ON public.chat_logs;
CREATE POLICY "chat_logs: user owns their logs"
  ON public.chat_logs FOR ALL
  USING (auth.uid() = user_id);
