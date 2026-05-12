import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { Upload, FileSpreadsheet, Database, CheckCircle2, AlertCircle, Loader2, Database as DatabaseIcon, Download, BarChart3, PieChart } from 'lucide-react';

interface ChartData {
  name: string;
  value: number;
}

export function DataHub() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<{type: 'success' | 'error', msg: string} | null>(null);
  const [stats, setStats] = useState({ total: 0, sources: 1 });
  const [regionData, setRegionData] = useState<ChartData[]>([]);
  const [industryData, setIndustryData] = useState<ChartData[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const [mainStats, regions, industries] = await Promise.all([
        api.get('/companies?page_size=1'),
        api.get('/stats/by-region'),
        api.get('/stats/by-industry')
      ]);
      
      setStats({ total: mainStats.total || 0, sources: 1 });
      setRegionData(regions || []);
      setIndustryData(industries || []);
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    } finally {
      setLoadingStats(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatus(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setStatus(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post('/ingest-csv', formData);
      setStatus({ type: 'success', msg: `Nạp thành công dữ liệu từ ${file.name}` });
      setFile(null);
      fetchStats();
    } catch (err: any) {
      setStatus({ type: 'error', msg: err.message || "Lỗi khi nạp dữ liệu" });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="data-hub-view animate-fade-in" style={{padding: '1rem'}}>
      {/* Stats Header */}
      <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '2rem'}}>
        <div className="glass card-glow" style={{padding: '1.5rem', borderRadius: '1.5rem', textAlign: 'center', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)'}}>
          <DatabaseIcon size={24} style={{color: '#3b82f6', marginBottom: '0.5rem'}} />
          <h4 style={{fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px'}}>Tổng số doanh nghiệp</h4>
          <p style={{fontSize: '2rem', fontWeight: 800, background: 'linear-gradient(to right, #fff, #3b82f6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'}}>
            {stats.total.toLocaleString()}
          </p>
        </div>
        <div className="glass card-glow" style={{padding: '1.5rem', borderRadius: '1.5rem', textAlign: 'center', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)'}}>
          <FileSpreadsheet size={24} style={{color: '#10b981', marginBottom: '0.5rem'}} />
          <h4 style={{fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px'}}>Nguồn dữ liệu CSV</h4>
          <p style={{fontSize: '2rem', fontWeight: 800, background: 'linear-gradient(to right, #fff, #10b981)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'}}>
            {stats.sources}
          </p>
        </div>
        <div className="glass card-glow" style={{padding: '1.5rem', borderRadius: '1.5rem', textAlign: 'center', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)'}}>
          <DatabaseIcon size={24} style={{color: '#8b5cf6', marginBottom: '0.5rem'}} />
          <h4 style={{fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px'}}>Supabase Sync</h4>
          <p style={{fontSize: '2rem', fontWeight: 800, background: 'linear-gradient(to right, #fff, #8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'}}>Active</p>
        </div>
      </div>

      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem'}}>
        {/* Region Chart */}
        <div className="card" style={{padding: '1.5rem'}}>
          <h3 style={{fontSize: '1rem', fontWeight: 700, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px', color: '#3b82f6'}}>
            <BarChart3 size={18} /> Phân bố theo Khu vực
          </h3>
          <div style={{height: '200px', display: 'flex', alignItems: 'flex-end', gap: '15px', padding: '0 10px'}}>
            {loadingStats ? (
               <div style={{width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center'}}><Loader2 className="animate-spin" /></div>
            ) : regionData.map((d, i) => (
              <div key={i} style={{flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px'}}>
                <div style={{
                  width: '100%', 
                  height: `${(d.value / Math.max(...regionData.map(v => v.value))) * 160}px`,
                  background: 'linear-gradient(to top, #3b82f6, #60a5fa)',
                  borderRadius: '6px 6px 2px 2px',
                  transition: 'height 1s ease-out'
                }}></div>
                <span style={{fontSize: '0.7rem', color: '#94a3b8', fontWeight: 600, textAlign: 'center'}}>{d.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Industry Chart */}
        <div className="card" style={{padding: '1.5rem'}}>
          <h3 style={{fontSize: '1rem', fontWeight: 700, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px', color: '#8b5cf6'}}>
            <PieChart size={18} /> Top Ngành nghề phổ biến
          </h3>
          <div style={{display: 'flex', flexDirection: 'column', gap: '12px'}}>
            {loadingStats ? (
               <div style={{width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center'}}><Loader2 className="animate-spin" /></div>
            ) : industryData.map((d, i) => (
              <div key={i}>
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px'}}>
                  <span style={{color: '#e2e8f0'}}>{d.name}</span>
                  <span style={{color: '#94a3b8', fontWeight: 700}}>{d.value}</span>
                </div>
                <div style={{width: '100%', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px'}}>
                  <div style={{
                    width: `${(d.value / Math.max(...industryData.map(v => v.value))) * 100}%`,
                    height: '100%',
                    background: 'var(--primary-purple)',
                    borderRadius: '3px',
                    boxShadow: '0 0 10px rgba(139, 92, 246, 0.3)'
                  }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '1.5rem'}}>
        {/* Upload Section */}
        <div className="card" style={{padding: '2rem', borderRadius: '2rem'}}>
          <h3 style={{fontSize: '1.25rem', fontWeight: 700, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px'}}>
            <Upload size={20} style={{color: '#3b82f6'}} /> Nạp dữ liệu mới
          </h3>
          
          <div 
            style={{
              border: '2px dashed rgba(255,255,255,0.1)',
              borderRadius: '1.5rem',
              padding: '3rem',
              textAlign: 'center',
              background: 'rgba(255,255,255,0.02)',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => document.getElementById('file-upload')?.click()}
          >
            <input type="file" id="file-upload" hidden accept=".csv" onChange={handleFileChange} />
            <div style={{background: 'rgba(59, 130, 246, 0.1)', width: '64px', height: '64px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyCenter: 'center', margin: '0 auto 1.5rem', color: '#3b82f6'}}>
               <FileSpreadsheet size={32} style={{margin: '0 auto'}} />
            </div>
            {file ? (
              <p style={{fontWeight: 600, color: '#fff'}}>{file.name}</p>
            ) : (
              <>
                <p style={{fontWeight: 600, marginBottom: '0.5rem'}}>Kéo thả file CSV vào đây</p>
                <p style={{fontSize: '0.8rem', color: '#94a3b8'}}>Dung lượng tối đa: 50MB</p>
              </>
            )}
          </div>

          {status && (
            <div style={{
              marginTop: '1.5rem',
              padding: '1rem',
              borderRadius: '12px',
              background: status.type === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              color: status.type === 'success' ? '#10b981' : '#ef4444',
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}>
              {status.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
              {status.msg}
            </div>
          )}

          <button 
            disabled={!file || uploading}
            onClick={handleUpload}
            style={{
              width: '100%',
              marginTop: '1.5rem',
              padding: '1rem',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              border: 'none',
              color: 'white',
              fontWeight: 700,
              cursor: file && !uploading ? 'pointer' : 'not-allowed',
              opacity: file && !uploading ? 1 : 0.5,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px'
            }}
          >
            {uploading ? <Loader2 className="animate-spin" size={20} /> : <Database size={20} />}
            {uploading ? 'Đang nạp dữ liệu...' : 'Bắt đầu nạp vào Database'}
          </button>
        </div>

        {/* Info Section */}
        <div className="card" style={{padding: '2rem', borderRadius: '2rem'}}>
          <h3 style={{fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.5rem'}}>Hướng dẫn định dạng</h3>
          <ul style={{listStyle: 'none', fontSize: '0.9rem', color: '#94a3b8'}}>
            <li style={{marginBottom: '1rem', display: 'flex', alignItems: 'start', gap: '10px'}}>
              <div style={{width: '6px', height: '6px', borderRadius: '50%', background: '#3b82f6', marginTop: '6px'}}></div>
              <span>File phải có định dạng <strong>.csv</strong> với mã hóa UTF-8.</span>
            </li>
            <li style={{marginBottom: '1rem', display: 'flex', alignItems: 'start', gap: '10px'}}>
              <div style={{width: '6px', height: '6px', borderRadius: '50%', background: '#3b82f6', marginTop: '6px'}}></div>
              <span>Các cột bắt buộc: <strong>ma_so_thue</strong>, <strong>ten_cong_ty</strong>.</span>
            </li>
            <li style={{marginBottom: '1rem', display: 'flex', alignItems: 'start', gap: '10px'}}>
              <div style={{width: '6px', height: '6px', borderRadius: '50%', background: '#3b82f6', marginTop: '6px'}}></div>
              <span>Hệ thống sẽ tự động loại bỏ các bản ghi trùng lặp MST.</span>
            </li>
          </ul>
          <div style={{marginTop: '2rem', padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)'}}>
            <p style={{fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem'}}>Tải file mẫu:</p>
            <button style={{background: 'none', border: 'none', color: '#3b82f6', fontSize: '0.875rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'}}>
              <Download size={14} /> sample_ingestion.csv
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
