import { createClient } from '@supabase/supabase-js';

// Các biến này sẽ được lấy từ file .env của Frontend (Vite)
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Thiếu cấu hình Supabase trong file .env của Frontend!');
}

export const supabase = createClient(supabaseUrl || '', supabaseAnonKey || '');
