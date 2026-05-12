import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { Upload, FileSpreadsheet, Database, CheckCircle2, AlertCircle, Loader2, Database as DatabaseIcon, Download, BarChart3, PieChart, Search, Filter } from 'lucide-react';

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
  const [companies, setCompanies] = useState<any[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingTable, setLoadingTable] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [seeding, setSeeding] = useState(false);
  const [growthData, setGrowthData] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>({});
  const [selectedIndustry, setSelectedIndustry] = useState<string>("");
  const [selectedYear, setSelectedYear] = useState<string>("");
  const [monthlyData, setMonthlyData] = useState<any[]>([]);
  const [qualityData, setQualityData] = useState<any[]>([]);

  useEffect(() => {
    fetchStats();
    fetchCompanies();
  }, [page, searchTerm]);

  const fetchCompanies = async () => {
    setLoadingTable(true);
    try {
      const data = await api.get(`/companies?q=${searchTerm}&page=${page}&page_size=10`);
      setCompanies(data.data || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error("Failed to fetch companies:", err);
    } finally {
      setLoadingTable(false);
    }
  };

  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const yearParam = selectedYear ? `?year=${selectedYear}` : '';
      const industryParam = selectedIndustry ? `${selectedYear ? '&' : '?'}industry=${selectedIndustry}` : '';
      const commonParams = `${yearParam}${industryParam}`;

      const [regionRes, industryRes, summaryRes, growthRes, monthlyRes, qualityRes] = await Promise.all([
        api.get(`/stats/by-region${commonParams}`),
        api.get(`/stats/by-industry`),
        api.get(`/stats/summary${commonParams}`),
        api.get(`/stats/growth-trend${selectedIndustry ? `?industry=${selectedIndustry}` : ''}`),
        api.get(`/stats/monthly-distribution${commonParams}`),
        api.get(`/stats/data-quality${commonParams}`)
      ]);
      
      setRegionData(regionRes || []);
      setIndustryData(industryRes || []);
      setSummary(summaryRes || {});
      setStats({ total: summaryRes.total || 0, sources: 2 });
      setGrowthData(growthRes || []);
      setMonthlyData(monthlyRes || []);
      setQualityData(qualityRes || []);
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [selectedIndustry, selectedYear]);

  const handleSeed = async () => {
    if (!confirm("Bạn có muốn nạp 7 doanh nghiệp mẫu để chạy thử không?")) return;
    setSeeding(true);
    try {
      await api.post('/seed-demo', {});
      fetchStats();
      fetchCompanies();
      alert("Đã nạp dữ liệu mẫu thành công!");
    } catch (err) {
      alert("Lỗi khi nạp dữ liệu mẫu.");
    } finally {
      setSeeding(false);
    }
  };

  const handleDelete = async (mst: string) => {
    if (!confirm(`Bạn có chắc chắn muốn xóa doanh nghiệp MST ${mst}?`)) return;
    try {
      await api.delete(`/companies/${mst}`);
      fetchCompanies();
      fetchStats();
    } catch (err) {
      alert("Lỗi khi xóa.");
    }
  };

  const handleExport = () => {
    if (companies.length === 0) return;
    const headers = ["MST", "Tên Công ty", "SĐT", "Email", "Địa chỉ"];
    const rows = companies.map(c => [c.ma_so_thue, c.ten_cong_ty, c.so_dien_thoai, c.email, c.dia_chi_day_du]);
    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers, ...rows].map(e => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "danh_ba_doanh_nghiep.csv");
    document.body.appendChild(link);
    link.click();
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
    <div className="data-hub-view animate-fade-in" style={{padding: '2rem', minHeight: '100vh', background: '#0a0a0c'}}>
      
      {/* Global Advanced Filter Bar */}
      <div className="glass" style={{
        padding: '1.2rem 2rem', 
        borderRadius: '1.5rem', 
        marginBottom: '1.5rem', 
        display: 'flex', 
        alignItems: 'center', 
        gap: '2rem',
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.1)',
        backdropFilter: 'blur(20px)'
      }}>
        <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
          <Filter size={18} style={{color: '#3b82f6'}} />
          <span style={{fontSize: '0.9rem', fontWeight: 700, color: '#94a3b8'}}>BỘ LỌC TOÀN CỤC:</span>
        </div>

        <div style={{display: 'flex', gap: '1rem', flex: 1}}>
          <select 
            value={selectedYear}
            onChange={(e) => setSelectedYear(e.target.value)}
            style={{
              padding: '10px 20px',
              borderRadius: '12px',
              background: '#16161a',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#fff',
              fontSize: '0.9rem',
              fontWeight: 600,
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="">Tất cả các năm</option>
            {Array.from({length: 12}, (_, i) => 2015 + i).reverse().map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>

          <select 
            value={selectedIndustry}
            onChange={(e) => setSelectedIndustry(e.target.value)}
            style={{
              padding: '10px 20px',
              borderRadius: '12px',
              background: '#16161a',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#fff',
              fontSize: '0.9rem',
              fontWeight: 600,
              outline: 'none',
              cursor: 'pointer',
              flex: 1,
              maxWidth: '400px'
            }}
          >
            <option value="">Tất cả ngành nghề (Top 50)</option>
            {industryData.map((ind, idx) => (
              <option key={idx} value={ind.name.split('-')[0].trim()}>{ind.name}</option>
            ))}
          </select>
        </div>

        <div style={{color: '#64748b', fontSize: '0.85rem', fontWeight: 500}}>
          {loadingStats ? 'Đang cập nhật dữ liệu...' : `Tìm thấy ${stats.total?.toLocaleString()} kết quả`}
        </div>
      </div>
      {/* Summary Metrics */}
      <div style={{display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.2rem', marginBottom: '1.5rem'}}>
        {[
          { label: 'Tổng doanh nghiệp', val: stats.total?.toLocaleString(), icon: <DatabaseIcon />, color: '#3b82f6', trend: '+12%' },
          { label: 'Ngành chủ lực', val: summary.top_industry || 'N/A', icon: <BarChart3 />, color: '#8b5cf6', trend: `${summary.industry_share || 0}% market` },
          { label: 'Độ sạch dữ liệu', val: summary.data_health || '99.8%', icon: <CheckCircle2 />, color: '#10b981', trend: 'Verified' },
          { label: 'Tỉnh thành', val: regionData.length, icon: <PieChart />, color: '#f59e0b', trend: 'Active' }
        ].map((m, i) => (
          <div key={i} className="glass card-glow" style={{padding: '1.2rem', borderRadius: '1.2rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', position: 'relative', overflow: 'hidden'}}>
            <div style={{position: 'absolute', right: '-10px', top: '-10px', opacity: 0.05, transform: 'scale(3)'}}>{m.icon}</div>
            <div style={{display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '0.8rem'}}>
              <div style={{padding: '8px', borderRadius: '10px', background: `${m.color}20`, color: m.color}}>{m.icon}</div>
              <span style={{fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase'}}>{m.label}</span>
            </div>
            <div style={{fontSize: '1.5rem', fontWeight: 800, color: '#fff', marginBottom: '0.2rem'}}>{m.val}</div>
            <div style={{fontSize: '0.7rem', color: m.color, fontWeight: 700}}>{m.trend}</div>
          </div>
        ))}
      </div>

      {/* Row 1: Growth Chart + Industry Top 10 */}
      <div style={{display: 'grid', gridTemplateColumns: '1.4fr 0.6fr', gap: '1.5rem', marginBottom: '1.5rem', alignItems: 'stretch'}}>
        <div className="glass card-glow" style={{padding: '2rem', borderRadius: '1.8rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', display: 'flex', flexDirection: 'column'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem'}}>
            <div>
              <h3 style={{fontSize: '1.2rem', fontWeight: 800, color: '#fff', marginBottom: '0.3rem'}}>Phân tích Tăng trưởng Chiến lược</h3>
              <p style={{fontSize: '0.85rem', color: '#64748b'}}>Chu kỳ thành lập {selectedYear || '2015-2026'}</p>
            </div>
            <div style={{display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: '#3b82f6', fontWeight: 600}}>
              <div style={{width: '10px', height: '10px', borderRadius: '50%', background: '#3b82f6', boxShadow: '0 0 10px #3b82f6'}} />
              Quy mô thành lập
            </div>
          </div>
          <div style={{flex: 1, minHeight: '240px'}}>
            {growthData.length > 0 ? (
              <svg width="100%" height="100%" viewBox="0 0 800 260" preserveAspectRatio="none" style={{overflow: 'visible'}}>
                <defs>
                  <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.5" />
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                  </linearGradient>
                  <filter id="glow"><feGaussianBlur stdDeviation="5" result="b" /><feComposite in="SourceGraphic" in2="b" operator="over" /></filter>
                </defs>
                {[0,0.25,0.5,0.75,1].map((v,i) => <line key={i} x1="0" y1={v*200} x2="800" y2={v*200} stroke="rgba(255,255,255,0.03)" strokeWidth="1" strokeDasharray="4 4" />)}
                {(() => {
                  const max = Math.max(...growthData.map(v => v.value)) || 1;
                  const pts = growthData.map((d,i) => ({ x: (i/(growthData.length-1))*800, y: 200-(d.value/max*180) }));
                  let p = `M ${pts[0].x} ${pts[0].y}`;
                  for(let i=0;i<pts.length-1;i++){const c=pts[i],n=pts[i+1]; p+=` C ${c.x+(n.x-c.x)*0.4} ${c.y}, ${c.x+(n.x-c.x)*0.6} ${n.y}, ${n.x} ${n.y}`;}
                  return (<><path d={`${p} L 800 260 L 0 260 Z`} fill="url(#areaGrad)" /><path d={p} fill="none" stroke="#3b82f6" strokeWidth="4" strokeLinecap="round" filter="url(#glow)" /></>);
                })()}
                {growthData.map((d,i) => {
                  const max = Math.max(...growthData.map(v => v.value)) || 1;
                  const x = (i/(growthData.length-1))*800, y = 200-(d.value/max*180);
                  return (<g key={i}><circle cx={x} cy={y} r="4" fill="#fff" filter="url(#glow)" /><text x={x} y="245" textAnchor="middle" fill="#94a3b8" style={{fontSize:'11px',fontWeight:700}}>{d.name}</text></g>);
                })}
              </svg>
            ) : <div style={{textAlign:'center',paddingTop:'100px',color:'#64748b'}}>Đang chuẩn bị dữ liệu...</div>}
          </div>
        </div>

        <div className="glass card-glow" style={{padding: '2rem', borderRadius: '1.8rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', display: 'flex', flexDirection: 'column'}}>
          <h3 style={{fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '10px'}}>
            <PieChart size={20} style={{color: '#a855f7'}} /> Trọng số Ngành (Top 10)
          </h3>
          <div style={{display: 'flex', flexDirection: 'column', gap: '0.9rem', flex: 1, justifyContent: 'center'}}>
            {industryData.slice(0, 10).map((d, i) => (
              <div key={i}>
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px'}}>
                  <span style={{color: '#cbd5e1', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '70%'}} title={d.name}>{d.name.split('-').pop()?.trim()}</span>
                  <span style={{fontWeight: 800, color: '#fff'}}>{d.value.toLocaleString()}</span>
                </div>
                <div style={{height: '6px', background: 'rgba(255,255,255,0.03)', borderRadius: '3px', overflow: 'hidden'}}>
                  <div style={{width: `${(d.value/(industryData[0]?.value||1))*100}%`, height: '100%', background: `linear-gradient(to right, ${['#6366f1','#8b5cf6','#a855f7','#d946ef','#ec4899'][i%5]}, ${['#8b5cf6','#a855f7','#d946ef','#ec4899','#f43f5e'][i%5]})`, borderRadius: '3px', transition: 'width 1s ease'}} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Row 2: Region Chart + AI Engine — same grid ratio */}
      <div style={{display: 'grid', gridTemplateColumns: '1.4fr 0.6fr', gap: '1.5rem', marginBottom: '1.5rem', alignItems: 'stretch'}}>
        <div className="glass card-glow" style={{padding: '2rem', borderRadius: '1.8rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', display: 'flex', flexDirection: 'column'}}>
          <h3 style={{fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px'}}>
            <DatabaseIcon size={20} style={{color: '#10b981'}} /> Đối soát Quy mô Khu vực
          </h3>
          <div style={{display: 'flex', alignItems: 'flex-end', justifyContent: 'center', flex: 1, minHeight: '220px', padding: '20px 0', gap: '80px', position: 'relative'}}>
            <div style={{position: 'absolute', width: '100%', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', zIndex: 0}}>
              {[0,1,2,3].map(i => <div key={i} style={{borderTop: '1px solid rgba(255,255,255,0.03)', width: '100%'}} />)}
            </div>
            {regionData.map((d, i) => {
              const totalReg = regionData.reduce((a,b) => a+b.value, 0) || 1;
              const maxVal = Math.max(...regionData.map(v => v.value)) || 1;
              return (
                <div key={i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', width: '120px', gap: '14px', zIndex: 1}}>
                  <div style={{fontSize: '0.9rem', fontWeight: 800, color: '#fff', padding: '5px 12px', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)'}}>{d.value.toLocaleString()}</div>
                  <div style={{width: '44px', height: `${(d.value/maxVal)*140}px`, background: i===0 ? 'linear-gradient(180deg, #10b981, #059669)' : 'linear-gradient(180deg, #3b82f6, #2563eb)', borderRadius: '22px', boxShadow: `0 8px 32px ${i===0 ? 'rgba(16,185,129,0.2)' : 'rgba(59,130,246,0.2)'}`, transition: 'height 1s cubic-bezier(0.34,1.56,0.64,1)', position: 'relative'}}>
                    <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent)', borderRadius: '22px'}} />
                  </div>
                  <div style={{fontSize: '0.9rem', color: '#fff', fontWeight: 700}}>{d.name}</div>
                  <div style={{fontSize: '0.75rem', color: '#64748b', fontWeight: 600}}>{((d.value/totalReg)*100).toFixed(1)}% market</div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="glass card-glow" style={{padding: '2rem', borderRadius: '1.8rem', background: 'linear-gradient(135deg, rgba(30,64,175,0.05), rgba(88,28,135,0.05))', border: '1px solid rgba(59,130,246,0.2)', display: 'flex', flexDirection: 'column'}}>
          <h3 style={{display: 'flex', alignItems: 'center', gap: '0.8rem', fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.2rem', color: '#60a5fa'}}>
            <BarChart3 size={22} /> Elite-DA Intelligence
          </h3>
          <div style={{display: 'flex', flexDirection: 'column', gap: '0.8rem', flex: 1, justifyContent: 'center'}}>
            {[
              { label: 'Ngành Bùng nổ', desc: `${summary.top_industry || 'N/A'} dẫn đầu thị trường`, status: 'Hot', color: '#ef4444' },
              { label: 'Thị phần', desc: `Chiếm ${summary.industry_share || 0}% tổng DN`, status: 'High', color: '#8b5cf6' },
              { label: 'Tăng trưởng', desc: `Trung bình ${growthData[growthData.length-1]?.change || 0}%/năm`, status: '+', color: '#10b981' },
              { label: 'Độ tin cậy', desc: 'Supabase realtime sync', status: '✓', color: '#3b82f6' }
            ].map((ins, idx) => (
              <div key={idx} style={{padding: '0.8rem', borderRadius: '0.8rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.03)', display: 'flex', alignItems: 'center', gap: '12px'}}>
                <div style={{width: '4px', height: '36px', background: ins.color, borderRadius: '2px'}} />
                <div style={{flex: 1}}>
                  <div style={{display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px'}}>
                    <span style={{fontSize: '0.85rem', fontWeight: 700, color: '#fff'}}>{ins.label}</span>
                    <span style={{fontSize: '0.6rem', padding: '1px 5px', borderRadius: '4px', background: `${ins.color}20`, color: ins.color, fontWeight: 800}}>{ins.status}</span>
                  </div>
                  <p style={{fontSize: '0.75rem', color: '#94a3b8', margin: 0}}>{ins.desc}</p>
                </div>
              </div>
            ))}
          </div>
          <button style={{marginTop: '1rem', width: '100%', padding: '0.7rem', borderRadius: '0.8rem', background: '#3b82f6', color: '#fff', border: 'none', fontWeight: 600, cursor: 'pointer'}} className="btn-glow">Tạo báo cáo chi tiết</button>
        </div>
      </div>

      {/* Row 3: Monthly Heatmap — full width */}
      <div className="glass card-glow" style={{padding: '2rem', borderRadius: '1.8rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem'}}>
        <h3 style={{fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px'}}>
          <BarChart3 size={20} style={{color: '#f59e0b'}} /> Phân bố Đăng ký theo Tháng {selectedYear ? `(${selectedYear})` : '(Tất cả)'}
        </h3>
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '8px', alignItems: 'flex-end', height: '200px'}}>
          {monthlyData.map((d: any, i: number) => {
            const max = Math.max(...monthlyData.map((v: any) => v.value)) || 1;
            const pct = (d.value / max) * 100;
            return (
              <div key={i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end', gap: '6px'}}>
                <span style={{fontSize: '0.75rem', fontWeight: 800, color: '#fff'}}>{d.value.toLocaleString()}</span>
                <div style={{
                  width: '100%', height: `${Math.max(pct, 4)}%`,
                  background: `linear-gradient(180deg, rgba(245,158,11,${0.3 + (d.value/max)*0.7}), rgba(234,88,12,${0.2 + (d.value/max)*0.6}))`,
                  borderRadius: '8px 8px 4px 4px', transition: 'height 0.8s ease',
                  boxShadow: d.value === max ? '0 0 20px rgba(245,158,11,0.4)' : 'none',
                  border: d.value === max ? '1px solid rgba(245,158,11,0.5)' : '1px solid rgba(255,255,255,0.05)'
                }} />
                <span style={{fontSize: '0.7rem', color: '#94a3b8', fontWeight: 700}}>{d.name}</span>
              </div>
            );
          })}
        </div>
        {monthlyData.length > 0 && (() => {
          const max = monthlyData.reduce((a: any, b: any) => a.value > b.value ? a : b, {value: 0, name: ''});
          const nonZero = monthlyData.filter((d: any) => d.value > 0);
          const min = nonZero.length > 0 ? nonZero.reduce((a: any, b: any) => a.value < b.value ? a : b) : {value: 0, name: 'N/A'};
          const total = monthlyData.reduce((a: number, b: any) => a + b.value, 0);
          return (
            <div style={{display: 'flex', gap: '2rem', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.05)'}}>
              <span style={{fontSize: '0.8rem', color: '#94a3b8'}}>Cao nhất: <strong style={{color: '#f59e0b'}}>{max.name} ({max.value.toLocaleString()})</strong></span>
              <span style={{fontSize: '0.8rem', color: '#94a3b8'}}>Thấp nhất: <strong style={{color: '#64748b'}}>{min.name} ({min.value?.toLocaleString()})</strong></span>
              <span style={{fontSize: '0.8rem', color: '#94a3b8'}}>TB: <strong style={{color: '#fff'}}>{Math.round(total / 12).toLocaleString()}/tháng</strong></span>
            </div>
          );
        })()}
      </div>

      {/* Row 4: YoY Growth Rate + Industry Donut */}
      <div style={{display: 'grid', gridTemplateColumns: '1.4fr 0.6fr', gap: '1.5rem', marginBottom: '1.5rem', alignItems: 'stretch'}}>
        <div className="glass card-glow" style={{padding: '2rem', borderRadius: '1.8rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', display: 'flex', flexDirection: 'column'}}>
          <h3 style={{fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '10px'}}>
            <BarChart3 size={20} style={{color: '#10b981'}} /> Tốc độ Tăng trưởng YoY (%)
          </h3>
          <div style={{display: 'flex', flexDirection: 'column', gap: '6px', flex: 1, justifyContent: 'center'}}>
            {growthData.slice(1).map((d: any, i: number) => {
              const prev = growthData[i]?.value || 1;
              const rate = prev > 0 ? ((d.value - prev) / prev * 100) : 0;
              const maxRate = Math.max(...growthData.slice(1).map((g: any, j: number) => { const p = growthData[j]?.value || 1; return p > 0 ? Math.abs((g.value - p) / p * 100) : 0; })) || 1;
              const barW = Math.min(Math.abs(rate) / maxRate * 100, 100);
              return (
                <div key={i} style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                  <span style={{width: '38px', fontSize: '0.72rem', color: '#94a3b8', fontWeight: 700, textAlign: 'right'}}>{d.name}</span>
                  <div style={{flex: 1, height: '16px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', overflow: 'hidden'}}>
                    <div style={{width: `${barW}%`, height: '100%', background: rate >= 0 ? 'linear-gradient(90deg, #10b981, #34d399)' : 'linear-gradient(90deg, #ef4444, #f87171)', borderRadius: '8px', transition: 'width 1s ease'}} />
                  </div>
                  <span style={{width: '60px', fontSize: '0.72rem', fontWeight: 800, color: rate >= 0 ? '#10b981' : '#ef4444', textAlign: 'right'}}>{rate >= 0 ? '+' : ''}{rate.toFixed(1)}%</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="glass card-glow" style={{padding: '2rem', borderRadius: '1.8rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', display: 'flex', flexDirection: 'column'}}>
          <h3 style={{fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '10px'}}>
            <PieChart size={20} style={{color: '#6366f1'}} /> Tỷ trọng Ngành nghề (Top 5)
          </h3>
          <div style={{display: 'flex', alignItems: 'center', gap: '2rem', flex: 1, justifyContent: 'center'}}>
            <svg width="150" height="150" viewBox="0 0 160 160">
              {(() => {
                const top5 = industryData.slice(0, 5);
                const total = top5.reduce((a: number, b: any) => a + b.value, 0) || 1;
                const colors = ['#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899'];
                let cumAngle = -90;
                return top5.map((d: any, i: number) => {
                  const angle = (d.value / total) * 360;
                  const sa = cumAngle; cumAngle += angle;
                  const r = 70, cx = 80, cy = 80;
                  const x1 = cx + r * Math.cos(sa * Math.PI / 180), y1 = cy + r * Math.sin(sa * Math.PI / 180);
                  const x2 = cx + r * Math.cos((sa + angle) * Math.PI / 180), y2 = cy + r * Math.sin((sa + angle) * Math.PI / 180);
                  return <path key={i} d={`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${angle > 180 ? 1 : 0} 1 ${x2} ${y2} Z`} fill={colors[i]} opacity="0.85" stroke="#0a0a0c" strokeWidth="2" />;
                });
              })()}
              <circle cx="80" cy="80" r="38" fill="#0a0a0c" />
              <text x="80" y="76" textAnchor="middle" fill="#fff" style={{fontSize: '13px', fontWeight: 800}}>{industryData.slice(0, 5).reduce((a: number, b: any) => a + b.value, 0).toLocaleString()}</text>
              <text x="80" y="90" textAnchor="middle" fill="#94a3b8" style={{fontSize: '8px', fontWeight: 600}}>TỔNG TOP 5</text>
            </svg>
            <div style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
              {industryData.slice(0, 5).map((d: any, i: number) => {
                const total = industryData.slice(0, 5).reduce((a: number, b: any) => a + b.value, 0) || 1;
                const colors = ['#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899'];
                return (
                  <div key={i} style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                    <div style={{width: '10px', height: '10px', borderRadius: '3px', background: colors[i], flexShrink: 0}} />
                    <span style={{fontSize: '0.72rem', color: '#cbd5e1', maxWidth: '130px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}} title={d.name}>{d.name.split('-').pop()?.trim()}</span>
                    <span style={{fontSize: '0.7rem', color: '#fff', fontWeight: 800, marginLeft: 'auto'}}>{((d.value / total) * 100).toFixed(1)}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Row 5: Data Quality Gauges */}
      <div className="glass card-glow" style={{padding: '2rem', borderRadius: '1.8rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem'}}>
        <h3 style={{fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px'}}>
          <CheckCircle2 size={20} style={{color: '#10b981'}} /> Kiểm toán Chất lượng Dữ liệu ({stats.total.toLocaleString()} bản ghi)
        </h3>
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1.5rem'}}>
          {qualityData.map((d: any, i: number) => {
            const color = d.value >= 90 ? '#10b981' : d.value >= 70 ? '#f59e0b' : '#ef4444';
            const circ = 2 * Math.PI * 36;
            const off = circ - (d.value / 100) * circ;
            return (
              <div key={i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px'}}>
                <svg width="90" height="90" viewBox="0 0 90 90">
                  <circle cx="45" cy="45" r="36" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="6" />
                  <circle cx="45" cy="45" r="36" fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
                    strokeDasharray={circ} strokeDashoffset={off} transform="rotate(-90 45 45)" style={{transition: 'stroke-dashoffset 1.5s ease'}} />
                  <text x="45" y="42" textAnchor="middle" fill="#fff" style={{fontSize: '15px', fontWeight: 800}}>{d.value}%</text>
                  <text x="45" y="56" textAnchor="middle" fill="#94a3b8" style={{fontSize: '8px', fontWeight: 600}}>{d.count?.toLocaleString()}</text>
                </svg>
                <span style={{fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600, textAlign: 'center'}}>{d.name}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{display: 'grid', gridTemplateColumns: '1.4fr 0.6fr', gap: '1.5rem'}}>
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

      {/* Companies Table Section */}
      <div className="card" style={{padding: '2rem', marginTop: '1.5rem'}}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
          <h3 style={{fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px'}}>
            <DatabaseIcon size={20} style={{color: '#3b82f6'}} /> Danh bạ Doanh nghiệp nội bộ
          </h3>
          <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
            <button 
              onClick={handleSeed}
              disabled={seeding}
              className="btn-secondary" 
              style={{display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', fontSize: '0.85rem'}}
            >
              {seeding ? <Loader2 size={14} className="animate-spin" /> : <Database size={14} />}
              Nạp mẫu
            </button>
            <button 
              onClick={handleExport}
              className="btn-secondary" 
              style={{display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', fontSize: '0.85rem'}}
            >
              <Download size={14} /> Xuất CSV
            </button>
            <div className="search-box" style={{position: 'relative', width: '250px'}}>
              <Search size={16} style={{position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8'}} />
              <input 
                type="text" 
                placeholder="Tìm MST hoặc tên..." 
                value={searchTerm}
                onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
                style={{width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', padding: '8px 8px 8px 36px', borderRadius: '10px', color: '#fff', fontSize: '0.85rem'}}
              />
            </div>
          </div>
        </div>

        <div style={{overflowX: 'auto'}}>
          <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', textAlign: 'left'}}>
            <thead>
              <tr style={{borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#94a3b8'}}>
                <th style={{padding: '12px', fontWeight: 600}}>MST</th>
                <th style={{padding: '12px', fontWeight: 600}}>Tên Doanh nghiệp</th>
                <th style={{padding: '12px', fontWeight: 600}}>Tỉnh / Thành</th>
                <th style={{padding: '12px', fontWeight: 600}}>Số điện thoại</th>
                <th style={{padding: '12px', fontWeight: 600}}>Email</th>
                <th style={{padding: '12px', fontWeight: 600}}>Địa chỉ</th>
                <th style={{padding: '12px', fontWeight: 600, textAlign: 'right'}}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {loadingTable ? (
                <tr><td colSpan={7} style={{padding: '2rem', textAlign: 'center'}}><Loader2 className="animate-spin" /></td></tr>
              ) : companies.length > 0 ? (
                companies.map((c, i) => (
                  <tr key={i} style={{borderBottom: '1px solid rgba(255,255,255,0.02)', transition: 'background 0.2s'}} className="table-row-hover">
                    <td style={{padding: '12px'}}><span style={{background: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700}}>{c.ma_so_thue}</span></td>
                    <td style={{padding: '12px', fontWeight: 600, color: '#fff'}}>{c.ten_cong_ty}</td>
                    <td style={{padding: '12px'}}><span style={{color: '#94a3b8', fontSize: '0.85rem'}}>{c.ten_tinh || '-'}</span></td>
                    <td style={{padding: '12px', color: '#fff', fontSize: '0.85rem'}}>{c.so_dien_thoai || '-'}</td>
                    <td style={{padding: '12px', color: '#3b82f6', fontSize: '0.85rem', textDecoration: 'underline'}}>{c.email || '-'}</td>
                    <td style={{padding: '12px', fontSize: '0.8rem', color: '#94a3b8'}}>{c.dia_chi_day_du || c.so_nha || '-'}</td>
                    <td style={{padding: '12px', textAlign: 'right'}}>
                      <div style={{display: 'flex', gap: '8px', justifyContent: 'flex-end'}}>
                        <button 
                          title="Phân tích"
                          onClick={() => {
                            // Chuyển sang tab Pipeline và điền MST
                            window.dispatchEvent(new CustomEvent('switch-tab', { detail: { tab: 'pipeline', mst: c.ma_so_thue }}));
                          }}
                          style={{padding: '6px', borderRadius: '6px', background: 'rgba(59, 130, 246, 0.1)', border: 'none', color: '#3b82f6', cursor: 'pointer'}}
                        >
                          <BarChart3 size={16} />
                        </button>
                        <button 
                          title="Xóa"
                          onClick={() => handleDelete(c.ma_so_thue)}
                          style={{padding: '6px', borderRadius: '6px', background: 'rgba(239, 68, 68, 0.1)', border: 'none', color: '#ef4444', cursor: 'pointer'}}
                        >
                          <AlertCircle size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={7} style={{padding: '2rem', textAlign: 'center', color: '#64748b'}}>Không tìm thấy dữ liệu doanh nghiệp nào.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > 10 && (
          <div style={{display: 'flex', justifyContent: 'center', gap: '10px', marginTop: '1.5rem'}}>
            <button 
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
              style={{padding: '6px 12px', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', cursor: page === 1 ? 'not-allowed' : 'pointer'}}
            >Trước</button>
            <span style={{color: '#94a3b8', display: 'flex', alignItems: 'center', fontSize: '0.9rem'}}>Trang {page} / {Math.ceil(total / 10)}</span>
            <button 
              disabled={page >= Math.ceil(total / 10)}
              onClick={() => setPage(p => p + 1)}
              style={{padding: '6px 12px', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', cursor: page >= Math.ceil(total / 10) ? 'not-allowed' : 'pointer'}}
            >Sau</button>
          </div>
        )}
      </div>
    </div>
  );
}
