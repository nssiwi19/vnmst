import React, { useState } from 'react';
import { supabase } from '../lib/supabase';

export function Login() {
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isSignUp) {
        const { error } = await supabase.auth.signUp({ 
            email, 
            password,
            options: {
                data: {
                    full_name: email.split('@')[0]
                }
            }
        });
        if (error) throw error;
        alert('Đăng ký thành công! Bạn có thể đăng nhập ngay.');
        setIsSignUp(false);
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }
    } catch (err: any) {
      setError(err.message || 'Có lỗi xảy ra');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="logo">
          <span className="logo-icon">🚀</span>
          <h1>Elite-DA</h1>
        </div>
        <p className="subtitle">{isSignUp ? 'Tạo tài khoản mới' : 'Hệ thống quản lý dữ liệu doanh nghiệp'}</p>
        
        <form onSubmit={handleAuth} className="login-form">
          <div className="form-group">
            <label>Email</label>
            <input 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              required 
              placeholder="name@company.com"
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label>Mật khẩu</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
              placeholder="••••••••"
              className="form-input"
            />
          </div>
          
          {error && <div className="error-message">{error}</div>}
          
          <button type="submit" className="login-button" disabled={loading}>
            {loading ? <span className="spinner"></span> : (isSignUp ? 'Đăng ký tài khoản' : 'Đăng nhập')}
          </button>
        </form>

        <div className="auth-footer">
          <span>{isSignUp ? 'Bạn đã có tài khoản?' : 'Bạn chưa có tài khoản?'}</span>
          <button onClick={() => setIsSignUp(!isSignUp)} className="toggle-auth">
            {isSignUp ? 'Đăng nhập' : 'Đăng ký ngay'}
          </button>
        </div>
      </div>

      <style>{`
        .login-container {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
          font-family: 'Inter', -apple-system, sans-serif;
        }
        .login-card {
          background: rgba(30, 41, 59, 0.7);
          backdrop-filter: blur(10px);
          padding: 3rem;
          border-radius: 1.5rem;
          width: 100%;
          max-width: 440px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        .logo {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          margin-bottom: 8px;
        }
        .logo-icon {
          font-size: 2rem;
        }
        .login-card h1 {
          color: white;
          margin: 0;
          font-size: 1.8rem;
          font-weight: 800;
          letter-spacing: -0.025em;
        }
        .subtitle {
          color: #94a3b8;
          font-size: 0.95rem;
          margin-bottom: 2rem;
        }
        .form-group {
          margin-bottom: 1.5rem;
        }
        .form-group label {
          display: block;
          color: #e2e8f0;
          font-size: 0.875rem;
          margin-bottom: 0.5rem;
          font-weight: 500;
        }
        .form-input {
          width: 100%;
          padding: 0.75rem 1rem;
          background: rgba(15, 23, 42, 0.6);
          border: 1px solid #334155;
          border-radius: 0.5rem;
          color: white;
          font-size: 1rem;
          transition: all 0.2s;
        }
        .form-input:focus {
          outline: none;
          border-color: #38bdf8;
          box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
        }
        .login-button {
          width: 100%;
          padding: 0.75rem;
          background: #38bdf8;
          color: #0f172a;
          border: none;
          border-radius: 0.5rem;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          margin-top: 0.5rem;
          display: flex;
          justify-content: center;
          align-items: center;
        }
        .login-button:hover {
          background: #7dd3fc;
          transform: translateY(-1px);
        }
        .login-button:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }
        .error-message {
          color: #f87171;
          font-size: 0.875rem;
          margin-bottom: 1rem;
          padding: 0.5rem;
          background: rgba(248, 113, 113, 0.1);
          border-radius: 0.375rem;
          border: 1px solid rgba(248, 113, 113, 0.2);
        }
        .auth-footer {
          margin-top: 2rem;
          color: #94a3b8;
          font-size: 0.875rem;
        }
        .toggle-auth {
          background: none;
          border: none;
          color: #38bdf8;
          font-weight: 600;
          cursor: pointer;
          margin-left: 0.5rem;
        }
        .toggle-auth:hover {
          text-decoration: underline;
        }
        .spinner {
          width: 20px;
          height: 20px;
          border: 3px solid rgba(15, 23, 42, 0.3);
          border-radius: 50%;
          border-top-color: #0f172a;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
